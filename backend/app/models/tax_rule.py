"""tax_rules 税率规则表（docs/02 §8，含种子数据口径）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class TaxRule(SQLModel, table=True):
    __tablename__ = "tax_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    market: str                    # 适用市场：a_share / us_stock / hk_stock / fund / bond
    condition: str                 # 人类可读条件，如「持股 > 1 年」
    rate: float                    # 税率：0 / 0.05 / 0.10 / 0.20
    hold_min_days: Optional[int] = None  # 持股天数下限（A股分档用：NULL/0/31/366）
    hold_max_days: Optional[int] = None  # 持股天数上限（NULL=不限）
    description: Optional[str] = None    # 规则说明（计税口径/代扣方）
    enabled: int = 1               # 是否启用：1 启用 / 0 停用
    updated_at: str = Field(default_factory=now_str)  # 更新时间
