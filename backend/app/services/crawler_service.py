"""分红预案采集服务（docs/06 §3.2）。

P1 数据源：东方财富数据中心公开接口（A股分红送配），写死在配置（源管理界面 V2）。
- 置信度评分：交易所/官方数据且字段完整 0.90–0.98；缺派息日 0.80；缺除权日 <0.70
- 入库 pending；同 (market, code, ex_date) 已存在（任意状态）则跳过
- 网络失败/离线模式（XI_CRAWL_OFFLINE=1）静默降级，不抛异常
"""
import logging
import os
from datetime import datetime

import httpx
from sqlmodel import Session, select

from ..models import DividendSchedule
from ..utils.timeutil import now_str, today_str

log = logging.getLogger("xi.crawler")

_SOURCE_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_MARKET = "a_share"
_CURRENCY = "CNY"


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


def run_crawl(session: Session) -> dict:
    """立即触发采集（docs/04 §11.3 /crawl）。离线或失败返回 0 并附 message。"""
    if os.getenv("XI_CRAWL_OFFLINE", "") == "1":
        return {"fetched": 0, "new_pending": 0, "message": "爬虫离线模式（XI_CRAWL_OFFLINE=1）"}
    try:
        fetched, new_pending = crawl_a_share(session)
    except Exception as e:  # 网络异常不中断后台任务
        log.warning("crawl failed: %s", e)
        return {"fetched": 0, "new_pending": 0, "message": "数据源暂时不可用，请稍后重试"}
    return {"fetched": fetched, "new_pending": new_pending, "crawled_at": now_str(),
            "date": today_str()}
