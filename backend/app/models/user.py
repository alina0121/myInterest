"""users 用户表（docs/02 §1）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)   # 登录名（邮箱/自定义），唯一
    email: Optional[str] = Field(default=None, unique=True, index=True)  # 邮箱（可空，微信用户可后绑）
    phone: Optional[str] = None      # 手机号（小程序快捷登录）
    password_hash: str               # bcrypt 密码哈希；微信用户初始随机密码
    nickname: Optional[str] = None   # 昵称
    avatar: Optional[str] = None     # 头像 URL
    wx_openid: Optional[str] = Field(default=None, unique=True)  # 微信 openid（小程序登录）
    wx_unionid: Optional[str] = None  # 微信 unionid（多端打通）
    role: str = Field(default="user")      # 角色：user / admin / super_admin
    status: str = Field(default="active")  # 状态：active 正常 / banned 封禁
    base_currency: str = Field(default="CNY")  # 统计折算本位币：CNY / USD / HKD
    created_at: str = Field(default_factory=now_str)    # 创建时间
    last_login_at: Optional[str] = None   # 最近登录时间
