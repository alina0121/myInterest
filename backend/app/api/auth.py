"""认证接口：注册/登录/刷新/当前用户/退出（docs/04 §一）。"""
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, or_, select

from ..database import get_session
from ..models import User, UserSetting
from ..schemas import LoginIn, RefreshIn, RegisterIn
from ..utils.errors import AppError, Codes, ok
from ..utils.security import (create_refresh_token, decode_token, hash_password,
                              token_pair, verify_password)
from ..utils.timeutil import now_str
from .deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 简单内存限流：每 IP 每 60 秒 10 次（docs/01 §5）
_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    with _lock:
        q, now = _hits[ip], time.time()
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= 10:
            raise AppError(Codes.SERVER_ERROR, "请求过于频繁，请稍后再试", status=429)
        q.append(now)


def _user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "email": u.email,
            "nickname": u.nickname, "avatar": u.avatar, "role": u.role,
            "base_currency": u.base_currency, "has_wx": bool(u.wx_openid),
            "created_at": u.created_at}


@router.post("/register")
def register(body: RegisterIn, request: Request,
             session: Session = Depends(get_session)):
    _rate_limit(request)
    exists = session.exec(select(User).where(User.username == body.username)).first()
    if exists:
        raise AppError(Codes.USER_EXISTS, "用户名已存在", status=409)
    if body.email:
        email_exists = session.exec(select(User).where(User.email == body.email)).first()
        if email_exists:
            raise AppError(Codes.USER_EXISTS, "邮箱已被使用", status=409)
    user = User(username=body.username, email=body.email,
                password_hash=hash_password(body.password),
                nickname=body.nickname or body.username)
    session.add(user)
    session.flush()
    session.add(UserSetting(user_id=user.id))
    session.commit()
    session.refresh(user)
    return ok({"user": _user_out(user), **token_pair(user.id)})


@router.post("/login")
def login(body: LoginIn, request: Request, session: Session = Depends(get_session)):
    _rate_limit(request)
    user = session.exec(select(User).where(
        or_(User.username == body.account, User.email == body.account))).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError(Codes.BAD_CREDENTIALS, "用户名或密码错误", status=401)
    if user.status == "banned":
        raise AppError(Codes.FORBIDDEN, "账号已封禁，请联系管理员", status=403)
    user.last_login_at = now_str()
    session.add(user)
    session.commit()
    return ok({"user": _user_out(user), **token_pair(user.id)})


@router.post("/refresh")
def refresh(body: RefreshIn, request: Request, session: Session = Depends(get_session)):
    _rate_limit(request)
    user_id = decode_token(body.refresh_token, "refresh")
    user = session.get(User, user_id)
    if user is None or user.status == "banned":
        raise AppError(Codes.TOKEN_INVALID, "token 无效", status=401)
    return ok({"access_token": token_pair(user.id)["access_token"],
               "refresh_token": create_refresh_token(user.id)})


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok(_user_out(user))


@router.post("/logout")
def logout():
    """V1 前端清 token 即可（refresh 黑名单 V2）。"""
    return ok({})
