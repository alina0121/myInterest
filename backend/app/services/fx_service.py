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
from . import config_service


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
    """返回 1 base = ? CNY；CNY 本身返回 1。结果落库缓存。

    取数按四级降级，保证离线也能出统计：
      ① DB 中 <= 当日的最近一条汇率（派息日落在周末/假日时取前一交易日）
      ② 在线拉取当日汇率并写入 exchange_rates 缓存
      ③ DB 中任意日期的最近一条（远期兜底）
      ④ 系统配置中的兜底汇率（后台可改，库完全为空时）
    """
    if base == "CNY":
        return Decimal("1")
    # ① 历史汇率：rate_date <= 派息日，取最近一天
    row = session.exec(
        select(ExchangeRate)
        .where(ExchangeRate.base == base, ExchangeRate.quote == "CNY",
               ExchangeRate.rate_date <= date_iso)
        .order_by(ExchangeRate.rate_date.desc())  # type: ignore
    ).first()
    if row:
        return Decimal(str(row.rate))

    # ② DB 没有 → 在线拉取并缓存，下次同一日期直接命中 ①
    fetched = fetch_rate_http(base, "CNY", date_iso)
    if fetched is not None:
        session.add(ExchangeRate(base=base, quote="CNY", rate=float(fetched),
                                 rate_date=date_iso, source="frankfurter"))
        session.commit()
        return fetched

    # ③ 在线失败 → 退而求其次用库里最近的任意日期汇率
    row_any = session.exec(
        select(ExchangeRate)
        .where(ExchangeRate.base == base, ExchangeRate.quote == "CNY")
        .order_by(ExchangeRate.rate_date.desc())  # type: ignore
    ).first()
    if row_any:
        return Decimal(str(row_any.rate))
    # ④ 全部不可用 → 系统配置里的兜底汇率，统计页面不致于报错
    key = "fx_fallback_usd" if base == "USD" else "fx_fallback_hkd" if base == "HKD" else None
    if key:
        return config_service.get_float(key)
    return Decimal("1")


def to_cny(session: Session, amount: float, currency: str, date_iso: str) -> Decimal:
    """原币金额按「date_iso 当日汇率」折算人民币，返回 2 位小数 Decimal。

    历史分红统一用派息日（pay_date）汇率，而非今天汇率，
    保证「去年的美元分红」按去年的汇率入账，不随汇率波动漂移。
    """
    return (Decimal(str(amount)) * get_rate_cny(session, currency, date_iso)
            ).quantize(Decimal("0.01"))
