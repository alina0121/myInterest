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
    dividend_id: int = Field(  # 所属分红，外键 dividends.id（分红删除时级联）
        sa_column=Column(ForeignKey("dividends.id", ondelete="CASCADE"), index=True)
    )
    lot_id: Optional[int] = Field(  # 对应买入批次，外键 lots.id（批次删除置空，保留快照）
        default=None, sa_column=Column(ForeignKey("lots.id", ondelete="SET NULL"))
    )
    lot_date: str          # 批次买入日快照（防批次后续改动）
    shares: float          # 该批次参与分红的股数
    gross: float           # 该批次分摊的税前金额
    tax: float = 0         # 该批次税费（A股按持股期限分档，见 03 文档）
    net: float             # 该批次税后金额 = gross - tax
    note: Optional[str] = None  # 快照说明
