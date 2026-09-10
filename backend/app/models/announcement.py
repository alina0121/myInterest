"""announcements 系统公告表（全局公共，后台维护，docs/02 §10）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Announcement(SQLModel, table=True):
    __tablename__ = "announcements"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str        # 公告标题
    content: str      # 公告正文
    published_at: Optional[str] = None   # 发布时间（NULL=草稿）
    status: str = Field(default="draft", index=True)  # 状态：draft 草稿 / published 已发布 / offline 已下线
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")  # 创建管理员
    created_at: str = Field(default_factory=now_str)  # 创建时间
