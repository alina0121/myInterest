"""user_settings 用户设置表（docs/02 §9）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class UserSetting(SQLModel, table=True):
    __tablename__ = "user_settings"

    user_id: int = Field(primary_key=True, foreign_key="users.id")
    remind_before_days: int = 3
    remind_on_payday: int = 1
    auto_match_schedule: int = 1
    push_enabled: int = 1
    wx_subscribe: int = 0
    updated_at: str = Field(default_factory=now_str)
