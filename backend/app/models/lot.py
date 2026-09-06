"""lots 买入批次表：同一标的每次交易一条（docs/02 §3，多批次核心）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Lot(SQLModel, table=True):
    __tablename__ = "lots"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    holding_id: int = Field(foreign_key="holdings.id", index=True)
    trade_date: str            # YYYY-MM-DD，分红归属判定关键字段
    direction: str             # buy / sell / bonus_share
    shares: float              # > 0
    price: float = 0           # 成交单价；送股为 0
    fee: float = 0
    note: Optional[str] = None
    created_at: str = Field(default_factory=now_str)
