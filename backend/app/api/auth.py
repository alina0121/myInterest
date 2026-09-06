"""认证接口：注册/登录/刷新/当前用户/退出/微信登录（docs/04 §一）。"""
import secrets
import threading
import time
from collections import defaultdict, deque

import httpx
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, or_, select

from ..config import WX_APPID, WX_MOCK, WX_SECRET
from ..database import get_session
from ..models import User, UserSetting
from ..schemas import LoginIn, RefreshIn, RegisterIn, WxLoginIn
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


@router.post("/wx-login")
def wx_login(body: WxLoginIn, request: Request,
             session: Session = Depends(get_session)):
    """微信小程序登录（docs/04 §1.5）。

    code → 微信 code2session 换 openid → 已绑定则登录；未绑定则创建用户。
    未配置 AppID/Secret 或 XI_WX_MOCK=1 时进入 mock 模式（用 code 当 openid）。
    """
    _rate_limit(request)
    openid = _wx_code2openid(body.code)
    if not openid:
        raise AppError(Codes.VALIDATION, "微信登录失败，请重试", status=400)

    user = session.exec(select(User).where(User.wx_openid == openid)).first()
    is_new = False
    if user is None:
        # 未绑定 → 创建用户（随机密码，username=wx_{openid前8位}）
        username = "wx_" + openid[:8]
        while session.exec(select(User).where(User.username == username)).first():
            username = "wx_" + openid[:6] + secrets.token_hex(2)
        user = User(
            username=username, wx_openid=openid,
            password_hash=hash_password(secrets.token_urlsafe(16)),
            nickname=body.nickname or f"微信用户{openid[-4:]}",
            avatar=body.avatar,
        )
        session.add(user)
        session.flush()
        session.add(UserSetting(user_id=user.id))
        is_new = True
    else:
        # 已绑定 → 更新昵称/头像（若有传）
        if body.nickname:
            user.nickname = body.nickname
        if body.avatar:
            user.avatar = body.avatar

    if user.status == "banned":
        raise AppError(Codes.FORBIDDEN, "账号已封禁，请联系管理员", status=403)
    user.last_login_at = now_str()
    session.add(user)
    session.commit()
    session.refresh(user)
    return ok({"user": _user_out(user), **token_pair(user.id), "is_new_user": is_new})


def _wx_code2openid(code: str) -> str | None:
    """调用微信 code2session 接口换取 openid；mock 模式直接返回 code。"""
    if WX_MOCK:
        return code
    try:
        resp = httpx.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={"appid": WX_APPID, "secret": WX_SECRET,
                    "js_code": code, "grant_type": "authorization_code"},
            timeout=8.0,
        )
        data = resp.json()
        if data.get("openid"):
            return data["openid"]
        # errcode: 40029=code无效, 40163=code已被使用, 45011=频率限制
        return None
    except Exception:
        return None


@router.post("/logout")
def logout():
    """V1 前端清 token 即可（refresh 黑名单 V2）。"""
    return ok({})
