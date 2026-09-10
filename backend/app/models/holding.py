"""holdings 持仓表：一只标的一条；数量/成本由 lots 实时聚合（docs/02 §2）。"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Holding(SQLModel, table=True):
    __tablename__ = "holdings"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)  # 所属用户（多用户数据隔离）
    market: str   # 市场：a_share / us_stock / hk_stock / fund / bond
    code: str     # 证券代码：600519 / AAPL / 00700 / 005827
    name: str     # 证券名称：贵州茅台
    currency: str = Field(default="CNY")   # 原币种：CNY / USD / HKD
    account: Optional[str] = None   # 所属账户/券商：华泰证券、富途牛牛
    freq: str = Field(default="unknown")   # 派息频率：monthly/quarterly/semi_annual/annual/irregular/unknown（后台/爬虫回填）
    note: Optional[str] = None      # 备注
    current_price: Optional[float] = None  # 手填现价（可选，用于现价股息率），docs/04 §6.6
    created_at: str = Field(default_factory=now_str)  # 创建时间
    updated_at: str = Field(default_factory=now_str)  # 更新时间

    class Config:
        json_encoders = {}
