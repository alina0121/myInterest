"""feedback 用户反馈表（docs/02 §11）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Feedback(SQLModel, table=True):
    __tablename__ = "feedback"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)  # 反馈用户
    content: str      # 反馈内容
    contact: Optional[str] = None        # 联系方式（选填）
    status: str = Field(default="pending", index=True)
    # 状态：pending 待处理 / adopted 已采纳 / planned 排期中 / done 已上线 / rejected 已驳回
    reply: Optional[str] = None          # 管理员回复
    handled_by: Optional[int] = Field(default=None, foreign_key="users.id")  # 处理管理员
    created_at: str = Field(default_factory=now_str)  # 创建时间
