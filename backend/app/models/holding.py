"""holdings 持仓表：一只标的一条；数量/成本由 lots 实时聚合（docs/02 §2）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Holding(SQLModel, table=True):
    __tablename__ = "holdings"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    market: str   # a_share / us_stock / hk_stock / fund / bond
    code: str
    name: str
    currency: str = Field(default="CNY")   # CNY / USD / HKD
    account: Optional[str] = None
    freq: str = Field(default="unknown")   # monthly/quarterly/semi_annual/annual/irregular/unknown
    note: Optional[str] = None
    current_price: Optional[float] = None  # 手填现价（可选，用于现价股息率），docs/04 §6.6
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)

    class Config:
        json_encoders = {}
