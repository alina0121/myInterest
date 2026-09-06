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


# ---------- settings ----------
class SettingsUpdate(BaseModel):
    remind_before_days: Optional[int] = Field(default=None, ge=0, le=30)
    remind_on_payday: Optional[int] = Field(default=None, ge=0, le=1)
    auto_match_schedule: Optional[int] = Field(default=None, ge=0, le=1)
    push_enabled: Optional[int] = Field(default=None, ge=0, le=1)
    wx_subscribe: Optional[int] = Field(default=None, ge=0, le=1)
