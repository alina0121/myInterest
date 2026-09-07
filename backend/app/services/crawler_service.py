"""分红预案采集服务（docs/06 §3.2）。

P1 数据源：
- A 股：东方财富数据中心公开接口（A股分红送配），写死在配置（源管理界面 V2）。
- 美股：Alpha Vantage TIME_SERIES_MONTHLY_ADJUSTED（按白名单拉取近 1 年月度分红）。
  需配置环境变量 XI_AV_API_KEY（到 https://www.alphavantage.co/support/#api-key 免费申请）。
  无 key 则跳过美股分支并日志提示；免费层 25 次/天，白名单 5 只够用。
- 置信度评分：交易所/官方数据且字段完整 0.90–0.98；缺派息日 0.80；缺除权日 <0.70
- 入库 pending；同 (market, code, ex_date) 已存在（任意状态）则跳过
- 网络失败/离线模式（XI_CRAWL_OFFLINE=1）静默降级，不抛异常
"""
import logging
import os
import time
from datetime import datetime, timedelta

import httpx
from sqlmodel import Session, select

from ..models import DividendSchedule
from ..utils.timeutil import now_str, today_str

log = logging.getLogger("xi.crawler")

_SOURCE_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_MARKET = "a_share"
_CURRENCY = "CNY"

# 美股派息白名单（蓝筹股 + 知名派息股，Alpha Vantage 免费层 25 次/天，控制在 5 只内）
_US_TICKERS = ["AAPL", "MSFT", "JNJ", "KO", "PG"]
_AV_URL = "https://www.alphavantage.co/query"
_AV_FUN = "TIME_SERIES_MONTHLY_ADJUSTED"
_US_CURRENCY = "USD"
_AV_RATE_SLEEP = 12  # Alpha Vantage 限速 5 次/分钟，串行 sleep 12 秒


def _clean_date(v) -> str | None:
    """接口日期形如 '2026-08-06 00:00:00'，取前 10 位。"""
    if not v:
        return None
    s = str(v)[:10]
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return None


def _confidence(ex: str | None, rec: str | None, pay: str | None) -> float:
    if ex and rec and pay:
        return 0.95
    if ex and rec:
        return 0.85
    if ex:
        return 0.70
    return 0.60


def crawl_a_share(session: Session, page_size: int = 100) -> tuple[int, int]:
    """抓取 A股分红送配预案，返回 (fetched, new_pending)。"""
    params = {
        "reportName": "RPT_SHAREBONUS_DET",
        "columns": "ALL",
        "pageSize": page_size,
        "pageNumber": 1,
        "sortColumns": "PLAN_NOTICE_DATE",
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
    }
    resp = httpx.get(_SOURCE_URL, params=params, timeout=10.0,
                     headers={"User-Agent": "Mozilla/5.0 (xi-dividend-tracker)"})
    resp.raise_for_status()
    rows = ((resp.json().get("result") or {}).get("data")) or []

    fetched, new_pending = 0, 0
    seen: set[tuple[str, str]] = set()
    for row in rows:
        code = str(row.get("SECURITY_CODE") or "").strip()
        name = str(row.get("SECURITY_NAME_ABBR") or "").strip()
        per10 = row.get("PRETAX_BONUS_RMB")  # 每 10 股税前派息（元）
        if not code or not name or per10 in (None, "", 0):
            continue  # 无现金分红（纯送转等）不入预案表
        ex = _clean_date(row.get("EX_DIVIDEND_DATE"))
        rec = _clean_date(row.get("EQUITY_RECORD_DATE"))
        pay = _clean_date(row.get("BONUS_PAY_DATE")) or ex
        dps = round(float(per10) / 10.0, 4)
        key = (code, ex or "")
        if key in seen:
            continue
        seen.add(key)
        fetched += 1
        if ex and session.exec(select(DividendSchedule).where(
                DividendSchedule.market == _MARKET,
                DividendSchedule.code == code,
                DividendSchedule.ex_date == ex)).first():
            continue  # 已存在（任意状态）→ 跳过
        title = row.get("PLAN_NOTICE_TITLE") or f"{name} 分红送配预案"
        session.add(DividendSchedule(
            market=_MARKET, code=code, name=name,
            ex_date=ex, record_date=rec, pay_date=pay, dps=dps,
            currency=_CURRENCY, div_type="cash", source="crawler",
            confidence=_confidence(ex, rec, pay), status="pending",
            raw_title=str(title)[:200],
        ))
        new_pending += 1
    session.commit()
    return fetched, new_pending


def crawl_us_stock(session: Session) -> tuple[int, int]:
    """抓取美股分红预案（Alpha Vantage TIME_SERIES_MONTHLY_ADJUSTED）。

    每月数据含 "7. dividend amount" 字段，非零即当月有分红。
    需配置 XI_AV_API_KEY；无 key 则跳过并日志提示。
    返回 (fetched, new_pending)。
    """
    api_key = os.getenv("XI_AV_API_KEY", "").strip()
    if not api_key:
        log.info("us_stock crawl skipped: XI_AV_API_KEY not set "
                 "(申请 https://www.alphavantage.co/support/#api-key)")
        return 0, 0

    today = datetime.utcnow().date()
    range_start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    fetched, new_pending = 0, 0

    for i, ticker in enumerate(_US_TICKERS):
        if i > 0:
            time.sleep(_AV_RATE_SLEEP)  # 限速 5 次/分钟
        try:
            resp = httpx.get(_AV_URL, params={
                "function": _AV_FUN, "symbol": ticker, "apikey": api_key,
            }, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.info("av %s fetch failed: %s", ticker, e)
            continue

        # Alpha Vantage 限流/错误时返回 "Note" 或 "Information" 字段
        if "Note" in data or "Information" in data:
            log.info("av %s rate limit: %s", ticker, data.get("Note") or data.get("Information"))
            continue

        series = data.get("Monthly Adjusted Time Series") or {}
        if not series:
            log.info("av %s empty series", ticker)
            continue

        for date_str, item in series.items():
            if date_str < range_start:
                continue
            try:
                amount = float(item.get("7. dividend amount", 0) or 0)
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue  # 该月无分红
            fetched += 1
            # 月线日期是月末，ex_date 实际在该月内；Alpha Vantage 不给精确 ex_date，用月初近似
            ex_date = date_str[:8] + "01"
            # 已存在（任意状态）→ 跳过
            if session.exec(select(DividendSchedule).where(
                    DividendSchedule.market == "us_stock",
                    DividendSchedule.code == ticker,
                    DividendSchedule.ex_date == ex_date)).first():
                continue
            session.add(DividendSchedule(
                market="us_stock", code=ticker, name=ticker,
                ex_date=ex_date, record_date=ex_date, pay_date=ex_date,
                dps=round(amount, 4),
                currency=_US_CURRENCY, div_type="cash", source="crawler",
                confidence=0.75,  # 月线日期不精确
                status="pending",
                raw_title=f"{ticker} monthly dividend ${amount}",
            ))
            new_pending += 1

    session.commit()
    return fetched, new_pending


def run_crawl(session: Session) -> dict:
    """立即触发采集（docs/04 §11.3 /crawl）。离线或失败返回 0 并附 message。

    顺序执行 A 股 + 美股两个分支；任一分支异常不中断另一分支。
    """
    if os.getenv("XI_CRAWL_OFFLINE", "") == "1":
        return {"fetched": 0, "new_pending": 0, "message": "爬虫离线模式（XI_CRAWL_OFFLINE=1）"}

    total_fetched, total_new = 0, 0
    errors = []

    # A 股分支
    try:
        f, n = crawl_a_share(session)
        total_fetched += f
        total_new += n
    except Exception as e:
        log.warning("a_share crawl failed: %s", e)
        errors.append("a_share: 数据源暂时不可用")

    # 美股分支（需配置 XI_AV_API_KEY）
    try:
        f, n = crawl_us_stock(session)
        total_fetched += f
        total_new += n
    except Exception as e:
        log.warning("us_stock crawl failed: %s", e)
        errors.append("us_stock: Alpha Vantage 暂时不可用或未配置 XI_AV_API_KEY")

    msg = "；".join(errors) if errors else None
    return {"fetched": total_fetched, "new_pending": total_new, "crawled_at": now_str(),
            "date": today_str(), "message": msg}
