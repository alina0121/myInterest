"""users 用户表（docs/02 §1）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: Optional[str] = Field(default=None, unique=True, index=True)
    phone: Optional[str] = None
    password_hash: str
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    wx_openid: Optional[str] = Field(default=None, unique=True)
    wx_unionid: Optional[str] = None
    role: str = Field(default="user")      # user / admin / super_admin
    status: str = Field(default="active")  # active / banned
    base_currency: str = Field(default="CNY")
    created_at: str = Field(default_factory=now_str)
    last_login_at: Optional[str] = None
