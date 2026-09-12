"""认证接口：注册/登录/刷新/当前用户/退出/微信登录/邮箱验证码（docs/04 §一）。"""
import secrets
import threading
import time
from collections import defaultdict, deque

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlmodel import Session, or_, select

from ..database import get_session
from ..models import Dividend, Holding, Lot, User, UserSetting
from ..schemas import (BindEmailIn, EmailLoginIn, EmailRegisterIn, LoginIn,
                       RefreshIn, RegisterIn, ResetPasswordIn, SendCodeIn,
                       WxLoginIn)
from ..services import config_service, mail_service, sms_service, verify_code_service
from ..utils.errors import AppError, Codes, ok
from ..utils.security import (create_refresh_token, decode_token, hash_password,
                              token_pair, verify_password)
from ..utils.timeutil import now_str
from .deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 简单内存限流：每 IP 每 60 秒 N 次（阈值后台可配 login_rate_limit_per_min）
# 滑动窗口：deque 存该 IP 最近的请求时间戳，每次请求先清掉 60 秒外的，
# 剩下的 >=阈值 就拒绝。单机够用；多进程部署需换 Redis（V2）
_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limit(request: Request) -> None:
    limit = config_service.get_int("login_rate_limit_per_min")
    ip = request.client.host if request.client else "unknown"
    with _lock:  # 多线程下保护 deque
        q, now = _hits[ip], time.time()
        while q and now - q[0] > 60:
            q.popleft()  # 丢掉窗口外的旧记录
        if len(q) >= limit:
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
    session.flush()  # 先 flush 拿到 user.id，才能建 1:1 的设置行
    session.add(UserSetting(user_id=user.id))  # 每个新用户配一份默认设置（提醒/自动匹配开关）
    session.commit()
    session.refresh(user)
    return ok({"user": _user_out(user), **token_pair(user.id)})  # 注册即登录，直接发双 token


@router.post("/login")
def login(body: LoginIn, request: Request, session: Session = Depends(get_session)):
    _rate_limit(request)
    # account 字段用户名/邮箱都能登录，所以用 or_ 两个条件一起查
    user = session.exec(select(User).where(
        or_(User.username == body.account, User.email == body.account))).first()
    if user is None or not verify_password(body.password, user.password_hash):
        # 用户不存在和密码错误返回同一句话，防止被枚举出哪些用户名已注册
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
    """调用微信 code2session 接口换取 openid；mock 模式直接返回 code。

    mock 条件：环境变量 XI_WX_MOCK=1（测试/开发强制），
    或后台未配置 wx_appid / wx_secret。
    """
    import os
    if os.getenv("XI_WX_MOCK", "") == "1":
        return code
    appid = config_service.get_text("wx_appid").strip()
    secret = config_service.get_text("wx_secret").strip()
    if not appid or not secret:
        return code  # 未配置微信凭证 → mock 模式（code 直接当 openid）
    try:
        resp = httpx.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={"appid": appid, "secret": secret,
                    "js_code": code,
                    "grant_type": "authorization_code"},
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


# ────────────────────────────────────────────────────────────────
# 邮箱验证码相关：发送验证码 / 邮箱登录 / 邮箱注册 / 找回密码 / 绑定邮箱
# ────────────────────────────────────────────────────────────────
@router.post("/send-code")
def send_code(body: SendCodeIn, request: Request,
              bg: BackgroundTasks,
              session: Session = Depends(get_session)):
    """发送验证码：邮箱或短信。通过 BackgroundTasks 异步发，失败仅记日志不阻塞响应。

    channel=email 时需要先在后台开启 mail_enabled 和配置 SMTP；
    channel=sms 时需要开启 sms_enabled（V2 短信 SDK 接入前抛 501）。
    """
    _rate_limit(request)
    # 目标格式校验
    if body.channel == "email":
        if "@" not in body.target or "." not in body.target.split("@")[-1]:
            raise AppError(Codes.VALIDATION, "邮箱格式不正确", status=422)
        if not config_service.get_bool("mail_enabled"):
            raise AppError(Codes.VALIDATION, "邮件服务未开启，请联系管理员",
                           status=503)
    else:  # sms
        if not body.target.isdigit() or len(body.target) < 6:
            raise AppError(Codes.VALIDATION, "手机号格式不正确", status=422)
        if not config_service.get_bool("sms_enabled"):
            raise AppError(Codes.VALIDATION, "短信服务未开启，请联系管理员",
                           status=503)

    # 业务前置检查：register 时若邮箱已注册则不发码（避免发骚扰信）
    if body.purpose == "register":
        if session.exec(select(User).where(User.email == body.target)).first():
            raise AppError(Codes.USER_EXISTS, "该邮箱已注册", status=409)
    elif body.purpose in ("login", "reset"):
        if not session.exec(select(User).where(User.email == body.target)).first():
            # 出于隐私不暴露存在性，但也不发码（避免被探测）
            raise AppError(Codes.NOT_FOUND, "该邮箱未注册", status=404)

    # 生成并存表（含频率限制：同目标 code_send_interval_sec 秒内不可重发）
    code = verify_code_service.generate_and_store(body.channel, body.target, body.purpose)

    # 异步发送：失败仅日志
    if body.channel == "email":
        bg.add_task(mail_service.send_code, body.target, code, body.purpose)
    else:
        bg.add_task(sms_service.send_code, body.target, code, body.purpose)
    return ok({"sent": True})


@router.post("/email-login")
def email_login(body: EmailLoginIn, request: Request,
                session: Session = Depends(get_session)):
    """邮箱验证码登录：校验 → 查 email → 返回 token pair；邮箱未注册返回 404。"""
    _rate_limit(request)
    verify_code_service.verify("email", body.email, body.code, "login")
    user = session.exec(select(User).where(User.email == body.email)).first()
    if user is None:
        raise AppError(Codes.NOT_FOUND, "该邮箱未注册，请先注册", status=404)
    if user.status == "banned":
        raise AppError(Codes.FORBIDDEN, "账号已封禁，请联系管理员", status=403)
    user.last_login_at = now_str()
    session.add(user)
    session.commit()
    return ok({"user": _user_out(user), **token_pair(user.id)})


@router.post("/email-register")
def email_register(body: EmailRegisterIn, request: Request,
                   session: Session = Depends(get_session)):
    """邮箱验证码注册（PC 网页端主要入口）：校验 → 建 User（username=email）。

    password 可选：传则后续可用密码登录；不传则只能通过邮箱验证码登录。
    """
    _rate_limit(request)
    verify_code_service.verify("email", body.email, body.code, "register")
    # 邮箱已注册则报错
    if session.exec(select(User).where(User.email == body.email)).first():
        raise AppError(Codes.USER_EXISTS, "该邮箱已注册", status=409)
    # 用户名默认用邮箱前缀（@ 前部分），冲突则加随机后缀
    base = body.email.split("@")[0]
    username = base
    while session.exec(select(User).where(User.username == username)).first():
        username = base + "_" + secrets.token_hex(2)
    # 密码：传了用，没传则随机（用户后续只能邮箱验证码登录）
    password_hash = hash_password(body.password) if body.password else \
        hash_password(secrets.token_urlsafe(16))
    user = User(
        username=username, email=body.email,
        password_hash=password_hash,
        nickname=body.nickname or base,
    )
    session.add(user)
    session.flush()
    session.add(UserSetting(user_id=user.id))
    session.commit()
    session.refresh(user)
    return ok({"user": _user_out(user), **token_pair(user.id)})


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, request: Request,
                   session: Session = Depends(get_session)):
    """找回密码：邮箱 + 验证码 + 新密码 → 改 password_hash。"""
    _rate_limit(request)
    verify_code_service.verify("email", body.email, body.code, "reset")
    user = session.exec(select(User).where(User.email == body.email)).first()
    if user is None:
        raise AppError(Codes.NOT_FOUND, "该邮箱未注册", status=404)
    user.password_hash = hash_password(body.new_password)
    session.add(user)
    session.commit()
    return ok({"reset": True})


@router.post("/bind-email")
def bind_email(body: BindEmailIn, request: Request,
               user: User = Depends(get_current_user),
               session: Session = Depends(get_session)):
    """绑定邮箱（需登录）。

    场景：微信账号 A 绑定邮箱 E。若 E 已被账号 B 使用，触发合并流程：
    把 A 的所有业务数据（holdings/lots/dividends）迁到 B，删除 A，把 A 的
    wx_openid/wx_unionid 绑到 B，返回 B 的新 token pair。前端 clearAuth+setAuth 切到 B。
    若 E 未被使用，则直接 UPDATE users SET email=E WHERE id=A.id。
    """
    _rate_limit(request)
    verify_code_service.verify("email", body.email, body.code, "bind")

    # B：用 E 已注册的账号（若有）
    user_b = session.exec(select(User).where(User.email == body.email)).first()
    if user_b is None:
        # E 未被使用 → 直接绑给当前用户 A
        if user.email:
            raise AppError(Codes.VALIDATION, "当前账号已绑定邮箱，请先解绑",
                           status=400)
        user.email = body.email
        session.add(user)
        session.commit()
        session.refresh(user)
        return ok({"merged": False, "user": _user_out(user),
                   **token_pair(user.id)})

    # E 已被 B 使用 → 合并 A 到 B
    # 防御：A 不能等于 B（理论上不会发生，user.email 为空才会到这里）
    if user_b.id == user.id:
        raise AppError(Codes.VALIDATION, "无需合并到自身", status=400)

    # 1. 处理同 (market, code) 持仓冲突：A 和 B 都有同标的持仓时，把 A 的 lots 和
    #    dividends 迁到 B 的对应持仓下，再删 A 的持仓；否则直接迁持仓到 B
    a_holdings = session.exec(select(Holding).where(Holding.user_id == user.id)).all()
    for h_a in a_holdings:
        h_b = session.exec(select(Holding).where(
            Holding.user_id == user_b.id,
            Holding.market == h_a.market,
            Holding.code == h_a.code)).first()
        if h_b:
            # 同标的两边都有：A 的 lots/dividends 迁到 B 的持仓下
            for lot in session.exec(select(Lot).where(Lot.holding_id == h_a.id)).all():
                lot.holding_id = h_b.id
                lot.user_id = user_b.id
                session.add(lot)
            for div in session.exec(select(Dividend).where(Dividend.holding_id == h_a.id)).all():
                div.holding_id = h_b.id
                div.user_id = user_b.id
                session.add(div)
            session.commit()
            session.delete(h_a)
        else:
            # 无冲突：直接改 user_id
            h_a.user_id = user_b.id
            session.add(h_a)
    session.commit()

    # 2. 迁 A 的剩余 lots 和 dividends（同持仓冲突的部分已迁，这里处理已切换 holding_id 之外的）
    #    实际上 lots 通过 holding_id 关联，已在上面处理；dividends 同。
    #    为防漏，对仍指向 A 的 lots/dividends 兜底改 user_id
    for lot in session.exec(select(Lot).where(Lot.user_id == user.id)).all():
        lot.user_id = user_b.id
        session.add(lot)
    for div in session.exec(select(Dividend).where(Dividend.user_id == user.id)).all():
        div.user_id = user_b.id
        session.add(div)
    session.commit()

    # 3. 把 A 的 wx_openid/wx_unionid 绑到 B
    #    wx_openid 有唯一约束，必须先置 A 的为 NULL 再设 B
    a_openid = user.wx_openid
    a_unionid = user.wx_unionid
    user.wx_openid = None
    session.add(user)
    session.commit()
    if a_openid:
        user_b.wx_openid = a_openid
    if a_unionid and not user_b.wx_unionid:
        user_b.wx_unionid = a_unionid
    user_b.last_login_at = now_str()
    session.add(user_b)
    session.commit()

    # 4. 删 A 的设置和账号本身
    a_setting = session.get(UserSetting, user.id)
    if a_setting:
        session.delete(a_setting)
    session.commit()
    session.delete(user)
    session.commit()

    session.refresh(user_b)
    return ok({"merged": True, "user": _user_out(user_b),
               **token_pair(user_b.id)})
