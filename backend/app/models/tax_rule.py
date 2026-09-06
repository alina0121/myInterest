"""tax_rules 税率规则表（docs/02 §8，含种子数据口径）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class TaxRule(SQLModel, table=True):
    __tablename__ = "tax_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    market: str
    condition: str                 # 人类可读条件，如「持股 > 1 年」
    rate: float                    # 0 / 0.05 / 0.10 / 0.20
    hold_min_days: Optional[int] = None
    hold_max_days: Optional[int] = None
    description: Optional[str] = None
    enabled: int = 1
    updated_at: str = Field(default_factory=now_str)
