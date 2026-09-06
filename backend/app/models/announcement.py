"""announcements 系统公告表（全局公共，后台维护，docs/02 §10）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Announcement(SQLModel, table=True):
    __tablename__ = "announcements"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str
    published_at: Optional[str] = None   # NULL=草稿
    status: str = Field(default="draft", index=True)  # draft / published / offline
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: str = Field(default_factory=now_str)
