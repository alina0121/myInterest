"""dividend_schedules 分红预案表（全局公共，后台维护，docs/02 §6）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class DividendSchedule(SQLModel, table=True):
    __tablename__ = "dividend_schedules"

    id: Optional[int] = Field(default=None, primary_key=True)
    market: str                  # a_share / us_stock / hk_stock / fund / bond
    code: str = Field(index=True)
    name: str
    ex_date: Optional[str] = None        # 除权除息日（未公告可空）
    record_date: Optional[str] = None    # 股权登记日
    pay_date: Optional[str] = None       # 派息日
    dps: Optional[float] = None          # 每股分红（预案币种，税前）
    currency: str = Field(default="CNY")
    div_type: str = Field(default="cash")             # cash / bonus_share
    source: str = Field(default="manual")             # crawler / manual / user_submit
    confidence: float = 1.0                # 0~1 置信度（爬虫评分）
    status: str = Field(default="pending", index=True)  # pending / published / rejected
    submitted_by: Optional[int] = Field(default=None, foreign_key="users.id")
    reviewed_by: Optional[int] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[str] = None
    reject_reason: Optional[str] = None
    raw_title: Optional[str] = None        # 公告原文标题（爬虫留痕）
    created_at: str = Field(default_factory=now_str)
