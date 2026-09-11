"""securities 股票基础信息表（全局公共，docs/02 §6 扩展）。

与 dividend_schedules 分离：一只股票对应多条分红预案，
name/currency/latest_price/freq 等股票级属性只存一份，避免重复。

索引策略（覆盖全部访问路径）：
- uq_security_market_code UNIQUE(market, code)：主键级访问路径，
  同时覆盖 WHERE market=? / ORDER BY market, code（前导列 market）。
- ix_securities_code(code)：单列索引，支撑仅按代码搜索（如下拉模糊匹配时的 SQL 检索）。
"""
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class Security(SQLModel, table=True):
    __tablename__ = "securities"
    # 唯一索引 (market, code)：所有按 (市场,代码) 的精确查询与 upsert 幂等判断都走它
    __table_args__ = (UniqueConstraint("market", "code", name="uq_security_market_code"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    # market 无需单列索引：唯一索引 (market, code) 的前导列已覆盖 WHERE market=? 查询
    market: str                  # 市场：a_share / us_stock / hk_stock / fund / bond
    # code 单列索引：单独按代码检索时命中（唯一索引前导列是 market，无法覆盖 code-only 查询）
    code: str = Field(index=True)
    name: str                        # 证券名称
    currency: str = Field(default="CNY")   # 币种
    latest_price: Optional[float] = None    # 最新价（爬虫/行情获取，不要求实时）
    price_updated_at: Optional[str] = None  # 价格更新时间
    freq: str = Field(default="unknown")    # 派息频率（爬虫/回填）
    created_at: str = Field(default_factory=now_str)
    updated_at: str = Field(default_factory=now_str)
