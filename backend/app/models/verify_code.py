"""verify_codes 验证码表：邮箱/短信验证码登录、注册、找回密码、绑定。

存储方式：bcrypt 哈希后的 6 位数字（不存明文），10 分钟过期，
单次有效（consumed_at 一旦填充即不可再用）。每次校验查最新未消费记录。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class VerifyCode(SQLModel, table=True):
    __tablename__ = "verify_codes"

    id: Optional[int] = Field(default=None, primary_key=True)
    channel: str = Field(index=True)             # "email" / "sms"
    target: str = Field(index=True)              # 邮箱地址或手机号
    code_hash: str                              # bcrypt 哈希后的 6 位数字
    purpose: str = Field(index=True)             # "login" / "register" / "reset" / "bind"
    expires_at: str                             # ISO 时间字符串，默认 10 分钟后过期
    consumed_at: Optional[str] = None           # 使用后填，单次有效
    created_at: str = Field(default_factory=now_str)
