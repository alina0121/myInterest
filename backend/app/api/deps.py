"""API 依赖：当前用户鉴权（JWT Bearer）。"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from ..database import get_session
from ..models import User
from ..utils.errors import AppError, Codes
from ..utils.security import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise AppError(Codes.UNAUTHORIZED, "未登录或缺少 token", status=401)
    user_id = decode_token(credentials.credentials, "access")
    user = session.get(User, user_id)
    if user is None:
        raise AppError(Codes.TOKEN_INVALID, "账号不存在", status=401)
    if user.status == "banned":
        raise AppError(Codes.FORBIDDEN, "账号已封禁，请联系管理员", status=403)
    return user
