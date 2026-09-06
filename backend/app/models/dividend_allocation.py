"""dividend_allocations 分红批次归属明细（docs/02 §5）。

每笔分红按批次拆分：哪个批次分了多少、税费按该批次持有天数分档。
批次删除后保留快照（lot_id 置空）。
"""
from typing import Optional

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, SQLModel


class DividendAllocation(SQLModel, table=True):
    __tablename__ = "dividend_allocations"

    id: Optional[int] = Field(default=None, primary_key=True)
    dividend_id: int = Field(
        sa_column=Column(ForeignKey("dividends.id", ondelete="CASCADE"), index=True)
    )
    lot_id: Optional[int] = Field(
        default=None, sa_column=Column(ForeignKey("lots.id", ondelete="SET NULL"))
    )
    lot_date: str          # 批次买入日快照
    shares: float          # 该批次参与分红的股数
    gross: float
    tax: float = 0
    net: float
    note: Optional[str] = None
