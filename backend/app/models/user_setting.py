"""user_settings 用户设置表（docs/02 §9）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class UserSetting(SQLModel, table=True):
    __tablename__ = "user_settings"

    user_id: int = Field(primary_key=True, foreign_key="users.id")  # 用户ID（与 users 1:1，兼主键）
    remind_before_days: int = 3    # 派息日前 N 天提醒
    remind_on_payday: int = 1      # 派息当天提醒（1=开 / 0=关）
    auto_match_schedule: int = 1   # 预案发布后自动生成分红(待到账)（1=开）
    push_enabled: int = 1          # App 推送开关（1=开 / 0=关）
    wx_subscribe: int = 0          # 小程序订阅消息是否已授权（1=是）
    updated_at: str = Field(default_factory=now_str)  # 更新时间
