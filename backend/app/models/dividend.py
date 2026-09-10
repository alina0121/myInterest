"""dividends 分红记录表（docs/02 §4）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Dividend(SQLModel, table=True):
    __tablename__ = "dividends"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)        # 所属用户（多用户数据隔离）
    holding_id: int = Field(foreign_key="holdings.id", index=True)  # 所属持仓
    schedule_id: Optional[int] = Field(default=None, index=True)  # 来源预案（自动匹配生成时关联）
    ex_date: str            # 除权除息日
    record_date: str        # 股权登记日（A股=除权日前一交易日；美股=ex_date）
    pay_date: str           # 派息/到账日
    dps: float              # 每股/每份分红（税前，原币种，4 位小数）
    eligible_shares: float = 0   # 除权日参与分红的净持仓（归属计算结果）
    gross_amount: float = 0      # 税前金额 = eligible_shares × dps
    tax: float = 0               # 税费（自动估算，允许手工改）
    net_amount: float = 0        # 税后到账 = gross_amount - tax
    currency: str = Field(default="CNY")  # 原币种
    div_type: str = Field(default="cash")     # 类型：cash 现金 / bonus_share 送股
    source: str = Field(default="manual")     # 来源：manual 手录 / imported 导入 / auto_schedule 预案生成
    status: str = Field(default="confirmed", index=True)  # 状态：pending 预告待到账 / confirmed 已到账
    tax_overridden: int = 0   # 税费被手工改过（1=是，自动重算时跳过税费）
    note: Optional[str] = None  # 备注
    created_at: str = Field(default_factory=now_str)  # 创建时间
    updated_at: str = Field(default_factory=now_str)  # 更新时间
