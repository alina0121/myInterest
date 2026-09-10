"""exchange_rates 汇率表（docs/02 §7）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class ExchangeRate(SQLModel, table=True):
    __tablename__ = "exchange_rates"

    id: Optional[int] = Field(default=None, primary_key=True)
    base: str              # 基准币：USD / HKD
    quote: str = "CNY"     # 报价币（固定 CNY）
    rate: float            # 汇率：1 base = rate CNY
    rate_date: str         # 汇率日期（历史分红按派息日汇率折算）
    source: str = "pbc"    # 来源：pbc 央行中间价 / frankfurter / manual 手录
    created_at: str = Field(default_factory=now_str)  # 创建时间
