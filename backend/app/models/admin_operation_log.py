"""admin_operation_logs 后台操作留痕表（docs/02 §12）。所有后台写操作必须落此表。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class AdminOperationLog(SQLModel, table=True):
    __tablename__ = "admin_operation_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    admin_id: int = Field(foreign_key="users.id", index=True)  # 操作管理员
    action: str            # 操作类型：schedule.approve / user.ban / rate.update / ...
    target_type: str       # 操作对象类型：schedule / user / rate / tax_rule / announcement / feedback
    target_id: Optional[int] = None    # 操作对象 ID
    detail: Optional[str] = None   # 详情 JSON：前后值摘要
    ip: Optional[str] = None       # 操作 IP
    created_at: str = Field(default_factory=now_str, index=True)  # 操作时间
