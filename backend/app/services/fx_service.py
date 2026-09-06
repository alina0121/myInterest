"""汇率服务：DB 查询 → 在线获取（frankfurter）→ 最近一条 → 兜底值。

折算口径见 docs/03 §4：统计折算用「派息日当日汇率」，查不到取最近前一交易日。
"""
import os
from datetime import date
from decimal import Decimal

import httpx
from sqlmodel import Session, select

from ..config import FX_API_BASE, FX_OFFLINE
from ..models import ExchangeRate

# 兜底值：离线/接口故障时保证统计可用
FALLBACK = {"USD": Decimal("7.1200"), "HKD": Decimal("0.9128")}


def fetch_rate_http(base: str, quote: str, date_iso: str) -> Decimal | None:
    """取某日汇率（frankfurter 对周末/假日自动返回前一交易日数据）。"""
    if FX_OFFLINE or os.getenv("XI_FX_OFFLINE") == "1":
        return None
    try:
        resp = httpx.get(f"{FX_API_BASE}/{date_iso}",
                         params={"from": base, "to": quote}, timeout=6.0,
                         follow_redirects=True)  # frankfurter 会 307 重定向
        if resp.status_code == 200:
            rate = resp.json().get("rates", {}).get(quote)
            if rate:
                return Decimal(str(rate))
    except Exception:
        return None
    return None


def fetch_latest_rate(base: str, quote: str = "CNY") -> float | None:
    rate = fetch_rate_http(base, quote, date.today().isoformat())
    return float(rate) if rate is not None else None


def get_rate_cny(session: Session, base: str, date_iso: str) -> Decimal:
    """返回 1 base = ? CNY；CNY 本身返回 1。结果落库缓存。"""
    if base == "CNY":
        return Decimal("1")
    row = session.exec(
        select(ExchangeRate)
        .where(ExchangeRate.base == base, ExchangeRate.quote == "CNY",
               ExchangeRate.rate_date <= date_iso)
        .order_by(ExchangeRate.rate_date.desc())  # type: ignore
    ).first()
    if row:
        return Decimal(str(row.rate))

    fetched = fetch_rate_http(base, "CNY", date_iso)
    if fetched is not None:
        session.add(ExchangeRate(base=base, quote="CNY", rate=float(fetched),
                                 rate_date=date_iso, source="frankfurter"))
        session.commit()
        return fetched

    row_any = session.exec(
        select(ExchangeRate)
        .where(ExchangeRate.base == base, ExchangeRate.quote == "CNY")
        .order_by(ExchangeRate.rate_date.desc())  # type: ignore
    ).first()
    if row_any:
        return Decimal(str(row_any.rate))
    return FALLBACK.get(base, Decimal("1"))


def to_cny(session: Session, amount: float, currency: str, date_iso: str) -> Decimal:
    return (Decimal(str(amount)) * get_rate_cny(session, currency, date_iso)
            ).quantize(Decimal("0.01"))
