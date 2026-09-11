"""dividend_schedules 分红预案表（全局公共，后台维护，docs/02 §6）。

股票级属性（name/currency/freq/latest_price）已迁移到 securities 表，
本表仅保留分红事件级字段；market/code 作为与 holdings 关联的自然键保留。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class DividendSchedule(SQLModel, table=True):
    __tablename__ = "dividend_schedules"

    id: Optional[int] = Field(default=None, primary_key=True)
    security_id: Optional[int] = Field(default=None, foreign_key="securities.id", index=True)
    market: str                  # 市场：a_share / us_stock / hk_stock / fund / bond
    code: str = Field(index=True)   # 证券代码（与 securities.market+code 对应，保留便于关联持仓）
    ex_date: Optional[str] = None        # 除权除息日（未公告可空）
    record_date: Optional[str] = None    # 股权登记日
    pay_date: Optional[str] = None       # 派息日
    dps: Optional[float] = None          # 每股分红（预案币种，税前）
    div_type: str = Field(default="cash")             # 类型：cash / bonus_share
    source: str = Field(default="manual")             # 来源：crawler 爬虫 / manual 后台 / user_submit 用户提交 / forecast 推算
    confidence: float = 1.0                # 0~1 置信度（爬虫评分）
    status: str = Field(default="pending", index=True)  # 状态：pending 待审核 / published 已发布 / rejected 已驳回
    submitted_by: Optional[int] = Field(default=None, foreign_key="users.id")  # user_submit 时的提交用户
    reviewed_by: Optional[int] = Field(default=None, foreign_key="users.id")   # 审核管理员
    reviewed_at: Optional[str] = None       # 审核时间
    reject_reason: Optional[str] = None     # 驳回原因
    raw_title: Optional[str] = None        # 公告原文标题（爬虫留痕）
    created_at: str = Field(default_factory=now_str)  # 创建时间
