"""API 依赖：当前用户鉴权（JWT Bearer）。

用法：在路由参数里写 user: User = Depends(get_current_user)，
FastAPI 会自动完成「取 token → 校验 → 查用户 → 查封禁」，不通过直接抛错，
路由函数里拿到的 user 一定是合法登录用户，无需再判空。
三级依赖层层嵌套：get_current_user → get_admin_user → require_super_admin。
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from ..database import get_session
from ..models import User
from ..utils.errors import AppError, Codes
from ..utils.security import decode_token

# auto_error=False：缺 token 时不返回 FastAPI 默认 403，
# 交给下面统一抛业务错误码（前端按 code 统一处理）
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> User:
    """普通登录用户依赖：所有业务接口的第一道门。"""
    if credentials is None:
        raise AppError(Codes.UNAUTHORIZED, "未登录或缺少 token", status=401)
    user_id = decode_token(credentials.credentials, "access")  # 只认 access token
    user = session.get(User, user_id)
    if user is None:
        raise AppError(Codes.TOKEN_INVALID, "账号不存在", status=401)
    if user.status == "banned":
        raise AppError(Codes.FORBIDDEN, "账号已封禁，请联系管理员", status=403)
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """管理员依赖：role ∈ {admin, super_admin}（docs/04 §0.1）。"""
    if user.role not in ("admin", "super_admin"):
        raise AppError(Codes.FORBIDDEN, "无管理员权限", status=403)
    return user


def require_super_admin(user: User = Depends(get_admin_user)) -> User:
    """超级管理员依赖：封禁/解封、汇率税率维护等敏感操作。"""
    if user.role != "super_admin":
        raise AppError(Codes.FORBIDDEN, "该操作仅超级管理员可执行", status=403)
    return user
