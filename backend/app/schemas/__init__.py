"""Pydantic 请求模型（入参白名单校验，docs/04 各接口入参表）。"""
from datetime import date as Date
from typing import Literal, Optional

from pydantic import BaseModel, Field

Market = Literal["a_share", "us_stock", "hk_stock", "fund", "bond"]
Currency = Literal["CNY", "USD", "HKD"]
Freq = Literal["monthly", "quarterly", "semi_annual", "annual", "irregular", "unknown"]
Direction = Literal["buy", "sell", "bonus_share"]
DivStatus = Literal["pending", "confirmed"]


# ---------- auth ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=4, max_length=32)
    email: Optional[str] = None
    password: str = Field(min_length=8)
    nickname: Optional[str] = None


class LoginIn(BaseModel):
    account: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class WxLoginIn(BaseModel):
    code: str = Field(min_length=1)
    nickname: Optional[str] = None
    avatar: Optional[str] = None


# ---------- holdings ----------
class FirstLotIn(BaseModel):
    trade_date: Date
    shares: float = Field(gt=0)
    price: float = Field(ge=0)
    fee: float = Field(default=0, ge=0)
    note: Optional[str] = None


class HoldingCreate(BaseModel):
    market: Market
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    currency: Currency
    account: Optional[str] = None
    freq: Freq = "unknown"
    note: Optional[str] = None
    first_lot: Optional[FirstLotIn] = None


class HoldingUpdate(BaseModel):
    name: Optional[str] = None
    account: Optional[str] = None
    freq: Optional[Freq] = None
    note: Optional[str] = None
    currency: Optional[Currency] = None
    current_price: Optional[float] = Field(default=None, ge=0)


# ---------- lots ----------
class LotCreate(BaseModel):
    trade_date: Date
    direction: Direction
    shares: float = Field(gt=0)
    price: float = Field(default=0, ge=0)
    fee: float = Field(default=0, ge=0)
    note: Optional[str] = None


class LotUpdate(BaseModel):
    trade_date: Optional[Date] = None
    direction: Optional[Direction] = None
    shares: Optional[float] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, ge=0)
    fee: Optional[float] = Field(default=None, ge=0)
    note: Optional[str] = None


# ---------- dividends ----------
class DividendCreate(BaseModel):
    holding_id: int
    ex_date: Date
    record_date: Optional[Date] = None
    pay_date: Date
    dps: float = Field(gt=0)
    tax: Optional[float] = Field(default=None, ge=0)  # 传入则不再自动估算
    div_type: Literal["cash", "bonus_share"] = "cash"
    status: DivStatus = "confirmed"
    note: Optional[str] = None


class DividendUpdate(BaseModel):
    ex_date: Optional[Date] = None
    record_date: Optional[Date] = None
    pay_date: Optional[Date] = None
    dps: Optional[float] = Field(default=None, gt=0)
    tax: Optional[float] = Field(default=None, ge=0)
    status: Optional[DivStatus] = None
    note: Optional[str] = None


class ConfirmIn(BaseModel):
    actual_net: Optional[float] = Field(default=None, ge=0)


# ---------- batch：批量录入 ----------
class LotBatchIn(BaseModel):
    """批量录入批次：支持一次提交多个买入/卖出/送转记录。"""
    lots: list[LotCreate] = Field(min_length=1, max_length=100)


class DividendBatchItem(BaseModel):
    """批量录入分红单条（复用 DividendCreate 字段，holding_id 可不同）。"""
    holding_id: int
    ex_date: Date
    record_date: Optional[Date] = None
    pay_date: Date
    dps: float = Field(gt=0)
    tax: Optional[float] = Field(default=None, ge=0)
    div_type: Literal["cash", "bonus_share"] = "cash"
    status: DivStatus = "confirmed"
    note: Optional[str] = None


class DividendBatchIn(BaseModel):
    """批量录入分红：支持一次提交多只持仓的多笔分红。"""
    dividends: list[DividendBatchItem] = Field(min_length=1, max_length=100)


class ScheduleBatchApproveIn(BaseModel):
    """批量审核预案：发布或驳回多条 pending 预案。"""
    ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["publish", "reject"]
    reason: Optional[str] = Field(default=None, max_length=200)


# ---------- settings ----------
class SettingsUpdate(BaseModel):
    remind_before_days: Optional[int] = Field(default=None, ge=0, le=30)
    remind_on_payday: Optional[int] = Field(default=None, ge=0, le=1)
    auto_match_schedule: Optional[int] = Field(default=None, ge=0, le=1)
    push_enabled: Optional[int] = Field(default=None, ge=0, le=1)
    wx_subscribe: Optional[int] = Field(default=None, ge=0, le=1)


# ---------- schedules（预案，docs/04 §5.3/11.3）----------
class ScheduleAdminCreate(BaseModel):
    market: Market
    code: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=64)
    ex_date: Optional[Date] = None
    record_date: Optional[Date] = None
    pay_date: Optional[Date] = None
    dps: Optional[float] = Field(default=None, gt=0)
    currency: Currency = "CNY"
    div_type: Literal["cash", "bonus_share"] = "cash"
    raw_title: Optional[str] = None


class ScheduleRejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=200)


# ---------- community（公告/反馈，docs/04 §十/11.5/11.6）----------
class FeedbackCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    contact: Optional[str] = Field(default=None, max_length=100)


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    publish: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)
    content: Optional[str] = None
    status: Optional[Literal["draft", "published", "offline"]] = None


class FeedbackHandleIn(BaseModel):
    status: Literal["pending", "adopted", "planned", "done", "rejected"]
    reply: Optional[str] = Field(default=None, max_length=500)


# ---------- admin：汇率/税率（docs/04 §11.4）----------
class RateManualIn(BaseModel):
    base: Literal["USD", "HKD"]
    rate: float = Field(gt=0)
    rate_date: Date


class TaxRuleUpdate(BaseModel):
    rate: Optional[float] = Field(default=None, ge=0, le=1)
    enabled: Optional[int] = Field(default=None, ge=0, le=1)
