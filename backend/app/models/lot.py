"""lots 买入批次表：同一标的每次交易一条（docs/02 §3，多批次核心）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Lot(SQLModel, table=True):
    __tablename__ = "lots"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)        # 所属用户（多用户数据隔离）
    holding_id: int = Field(foreign_key="holdings.id", index=True)  # 所属持仓（1:N）
    trade_date: str            # 成交日期 YYYY-MM-DD，分红归属判定关键字段
    direction: str             # 方向：buy 买入 / sell 卖出 / bonus_share 送股转增（0 成本）
    shares: float              # 数量（股/份），> 0；卖出在净持仓聚合中按负号处理
    price: float = 0           # 成交单价；送股为 0
    fee: float = 0             # 交易费用（佣金/印花税等）
    note: Optional[str] = None  # 备注：首次建仓 / 回调加仓
    created_at: str = Field(default_factory=now_str)  # 创建时间
