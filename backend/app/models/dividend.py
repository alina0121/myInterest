"""dividends 分红记录表（docs/02 §4）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Dividend(SQLModel, table=True):
    __tablename__ = "dividends"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    holding_id: int = Field(foreign_key="holdings.id", index=True)
    schedule_id: Optional[int] = Field(default=None, index=True)  # P1 关联预案
    ex_date: str            # 除权除息日
    record_date: str        # 股权登记日（归属判定日）
    pay_date: str           # 派息日
    dps: float              # 每股分红（税前，原币种）
    eligible_shares: float = 0   # 归属计算结果
    gross_amount: float = 0      # 税前 = eligible_shares × dps
    tax: float = 0
    net_amount: float = 0        # 税后到账
    currency: str = Field(default="CNY")
    div_type: str = Field(default="cash")     # cash / bonus_share
    source: str = Field(default="manual")     # manual / imported / auto_schedule
    status: str = Field(default="confirmed", index=True)  # pending / confirmed
    tax_overridden: int = 0   # 税费被手工改过（1=是，重算时跳过税费）
    note: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
