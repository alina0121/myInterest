"""密码哈希（bcrypt）与 JWT 签发/校验。

双 token 机制：
- access_token：短期（ACCESS_TOKEN_MINUTES），接口鉴权用，过期前端用 refresh 换新
- refresh_token：长期（REFRESH_TOKEN_DAYS），仅用于刷新 access，不用于业务接口
- payload 里带 type 字段，刷新接口只认 refresh、业务接口只认 access，防止混用
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import SECRET_KEY
from ..services import config_service
from .errors import AppError, Codes

_ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # hash 格式非法（如历史脏数据/微信随机密码缺失）时按校验失败处理，不抛 500
        return False


def _create_token(user_id: int, token_type: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=_ALGO)


def create_access_token(user_id: int) -> str:
    # 有效期取系统配置（DB→环境变量→默认 120 分钟），只影响新签发的令牌
    return _create_token(user_id, "access", config_service.get_int("access_token_minutes"))


def create_refresh_token(user_id: int) -> str:
    days = config_service.get_int("refresh_token_days")
    return _create_token(user_id, "refresh", days * 24 * 60)


def token_pair(user_id: int) -> dict:
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


def decode_token(token: str, expected_type: str) -> int:
    """校验并解析 token，返回 user_id；失败抛 1003。"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[_ALGO])
    except jwt.PyJWTError:
        raise AppError(Codes.TOKEN_INVALID, "登录已过期，请重新登录", status=401)
    if payload.get("type") != expected_type:
        raise AppError(Codes.TOKEN_INVALID, "token 类型无效", status=401)
    try:
        return int(payload["sub"])
    except (KeyError, ValueError):
        raise AppError(Codes.TOKEN_INVALID, "token 无效", status=401)
