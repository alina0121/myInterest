"""密码哈希（bcrypt）与 JWT 签发/校验。"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS, SECRET_KEY
from .errors import AppError, Codes

_ALGO = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
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
    return _create_token(user_id, "access", ACCESS_TOKEN_MINUTES)


def create_refresh_token(user_id: int) -> str:
    return _create_token(user_id, "refresh", REFRESH_TOKEN_DAYS * 24 * 60)


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
