"""分红预案采集服务（docs/06 §3.2）。

P1 数据源：
- A 股：东方财富数据中心公开接口（A股分红送配），分页增量抓取
  （按公告日倒序翻页，遇到整页都已入库即停止；page_size 走后台配置）。
- 美股：Alpha Vantage TIME_SERIES_MONTHLY_ADJUSTED（按白名单拉取全部历史月度分红）。
  需配置系统配置 av_api_key；留空则跳过美股分支并日志提示。
  免费层 25 次/天，白名单 5 只够用。
- 置信度评分：交易所/官方数据且字段完整 0.90–0.98；缺派息日 0.80；缺除权日 <0.70
- 入库 pending；同 (market, code, ex_date) 已存在（任意状态）则跳过
- 网络失败/离线模式（XI_CRAWL_OFFLINE=1）静默降级，不抛异常
"""
import logging
import os
import time
from datetime import datetime

import httpx
from sqlmodel import Session, select

from ..models import DividendSchedule, Security
from . import config_service, security_service
from ..utils.timeutil import now_str, today_str

log = logging.getLogger("xi.crawler")

_SOURCE_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
_MARKET = "a_share"
_CURRENCY = "CNY"

_AV_URL = "https://www.alphavantage.co/query"
_AV_FUN = "TIME_SERIES_MONTHLY_ADJUSTED"
_US_CURRENCY = "USD"

# A 股分页抓取安全上限：每页最多 500，最多 20 页 = 单次最多 1 万条，
# 防止接口异常时无限翻页；正常增量抓取在遇到「整页都已入库」时即提前停止。
_MAX_CRAWL_PAGES = 20


def _http_get_json(url: str, params: dict, timeout: float = 10.0) -> dict:
    """带 3 次重试的 GET，应对瞬时网络抖动；全部失败抛出最后一次异常。"""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = httpx.get(url, params=params, timeout=timeout,
                             headers={"User-Agent": "Mozilla/5.0 (xi-dividend-tracker)"})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if attempt < 2:
                time.sleep(1.0 + attempt)  # 1s / 2s 退避
    assert last_exc is not None
    raise last_exc


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
    """数据置信度：关键日期越完整越可信。低于 0.8 的后台审核时需重点核对。"""
    if ex and rec and pay:
        return 0.95
    if ex and rec:
        return 0.85
    if ex:
        return 0.70
    return 0.60  # 连除权日都没有，基本只能当线索


def crawl_a_share(session: Session, page_size: int | None = None) -> tuple[int, int]:
    """抓取 A股分红送配预案，返回 (fetched, new_pending)。

    fetched=抓到的有效现金分红条数（跨页合计）；new_pending=实际新入库（去重后）条数。
    分页策略：按公告日倒序翻页，遇到「整页都已入库（无新增无升级）」即停止增量；
    单轮最多翻 _MAX_CRAWL_PAGES 页作为安全上限，避免接口异常时失控。
    """
    if page_size is None:
        page_size = config_service.get_int("crawl_a_share_page_size")
    page_size = max(10, min(500, int(page_size)))  # 东财接口单页范围，且避免 0/负数

    total_fetched, total_new = 0, 0

    for page in range(1, _MAX_CRAWL_PAGES + 1):
        # 东财数据中心固定参数：RPT_SHAREBONUS_DET=分红送配明细报表
        params = {
            "reportName": "RPT_SHAREBONUS_DET",
            "columns": "ALL",
            "pageSize": page_size,
            "pageNumber": page,
            "sortColumns": "PLAN_NOTICE_DATE",
            "sortTypes": "-1",  # -1=倒序，最新公告在前
            "source": "WEB",
            "client": "WEB",
        }
        data = _http_get_json(_SOURCE_URL, params)
        # 返回结构：{"result": {"data": [...]}}，无数据时 result 可能为 None
        rows = (data.get("result") or {}).get("data")
        if not isinstance(rows, list) or not rows:
            break  # 接口无更多数据

        # ── 阶段1：解析本页，按 (代码, 报告期) 收敛 ──
        # 同一份方案在东财表里可能出现多行（董事会决议→实施公告），
        # 同页遇到同方案时保留「除权日等日期更全」的一行。
        parsed: list[dict] = []
        idx_by_key: dict[tuple[str, str], int] = {}
        for row in rows:
            code = str(row.get("SECURITY_CODE") or "").strip()
            name = str(row.get("SECURITY_NAME_ABBR") or "").strip()
            per10 = row.get("PRETAX_BONUS_RMB")  # 每 10 股税前派息（元）
            # 先转 float 再判断是否为 0，避免字符串 "0.00" 绕过检查插入 dps=0 垃圾
            try:
                per10_f = float(per10) if per10 not in (None, "") else 0.0
            except (TypeError, ValueError):
                per10_f = 0.0
            if not code or not name or per10_f <= 0:
                continue  # 无现金分红（纯送转等）不入预案表
            item = {
                "code": code, "name": name,
                "report_date": _clean_date(row.get("REPORT_DATE")),  # 方案所属报告期
                "ex": _clean_date(row.get("EX_DIVIDEND_DATE")),
                "rec": _clean_date(row.get("EQUITY_RECORD_DATE")),
                # 未公告派息日先顶着除权日（可能两者都为 None）
                "pay": _clean_date(row.get("BONUS_PAY_DATE")) or _clean_date(
                    row.get("EX_DIVIDEND_DATE")),
                "dps": round(per10_f / 10.0, 4),  # 东财口径「每10股」→ 每股
                "title": str(row.get("PLAN_NOTICE_TITLE") or ""),
            }
            # 同一方案多行：优先留信息更全（有除权日）的；无报告期时退回用除权日区分
            key = (code, item["report_date"] or item["ex"] or "")
            prev = idx_by_key.get(key)
            if prev is not None:
                if item["ex"] and not parsed[prev]["ex"]:
                    parsed[prev] = item  # 旧行只是预案，本行已公布除权日 → 替换升级
                continue
            idx_by_key[key] = len(parsed)
            parsed.append(item)

        # ── 阶段2：查库去重 / 升级 / 插入 ──
        page_inserts, page_upgrades = 0, 0
        for it in parsed:
            ex, rec, pay, dps = it["ex"], it["rec"], it["pay"], it["dps"]
            if ex:
                # 已公布除权日：按 (市场,代码,除权日) 去重（任意状态，含已驳回不再捞回）
                existing = session.exec(select(DividendSchedule).where(
                    DividendSchedule.market == _MARKET,
                    DividendSchedule.code == it["code"],
                    DividendSchedule.ex_date == ex)).first()
                if existing:
                    continue
                # 同金额的旧「未定日」预案（董事会阶段先爬到）→ 原地补全，不新增
                pending_one = session.exec(select(DividendSchedule).where(
                    DividendSchedule.market == _MARKET,
                    DividendSchedule.code == it["code"],
                    DividendSchedule.dps == dps,
                    DividendSchedule.ex_date == None,  # noqa: E711
                    DividendSchedule.status == "pending",
                    DividendSchedule.source == "crawler")
                    .order_by(DividendSchedule.id.desc())).first()  # type: ignore
                if pending_one is not None:
                    pending_one.ex_date = ex
                    pending_one.record_date = rec
                    pending_one.pay_date = pay
                    pending_one.confidence = _confidence(ex, rec, pay)  # 0.60 → 0.95
                    session.add(pending_one)
                    page_upgrades += 1
                    continue
            else:
                # 纯预案（除权日未公布）：若同代码同金额「已有除权日」的更完整记录存在，
                # 直接跳过（防止已公告除权日的记录与未定日预案重复入库）；
                # 否则按 (代码,金额,未定日) 去重，任意状态都不再捞回
                # （否则定时任务每天两次重复堆积、驳回的垃圾也会复活）
                has_better = session.exec(select(DividendSchedule).where(
                    DividendSchedule.market == _MARKET,
                    DividendSchedule.code == it["code"],
                    DividendSchedule.dps == dps,
                    DividendSchedule.ex_date != None)).first()  # noqa: E711
                if has_better:
                    continue
                existing = session.exec(select(DividendSchedule).where(
                    DividendSchedule.market == _MARKET,
                    DividendSchedule.code == it["code"],
                    DividendSchedule.dps == dps,
                    DividendSchedule.ex_date == None,  # noqa: E711
                    DividendSchedule.source == "crawler")).first()
                if existing:
                    continue
            title = it["title"] or f"{it['name']} 分红送配预案"
            sec = security_service.upsert_security(session, _MARKET, it["code"], it["name"], _CURRENCY)
            session.add(DividendSchedule(
                security_id=sec.id, market=_MARKET, code=it["code"],
                ex_date=ex, record_date=rec, pay_date=pay, dps=dps,
                div_type="cash", source="crawler",
                confidence=_confidence(ex, rec, pay), status="pending",
                raw_title=title[:200],  # 留痕：出问题可回溯是哪条公告
            ))
            page_inserts += 1

        total_fetched += len(parsed)
        total_new += page_inserts
        session.commit()  # 每页提交一次，后续页失败不丢失已抓进度

        # 增量停止条件：本页既无新增也无升级 → 后续更老的页必然也都已入库
        if page_inserts == 0 and page_upgrades == 0:
            break
        # 末页不足一页 → 没有更多数据
        if len(rows) < page_size:
            break

    return total_fetched, total_new


def crawl_us_stock(session: Session) -> tuple[int, int]:
    """抓取美股分红预案（Alpha Vantage TIME_SERIES_MONTHLY_ADJUSTED）。

    每月数据含 "7. dividend amount" 字段，非零即当月有分红。
    API Key 取系统配置 av_api_key（后台可配），其次环境变量 XI_AV_API_KEY；
    未配置则跳过并日志提示。返回 (fetched, new_pending)。
    """
    api_key = config_service.get_text("av_api_key").strip()
    if not api_key:
        log.info("us_stock crawl skipped: av_api_key not configured "
                 "(后台系统配置或 XI_AV_API_KEY，申请 https://www.alphavantage.co/support/#api-key)")
        return 0, 0

    fetched, new_pending = 0, 0
    tickers = config_service.get_list("crawl_us_tickers")  # 后台可配的白名单
    sleep_sec = config_service.get_int("crawl_us_rate_sleep")

    # 串行拉白名单：Alpha Vantage 免费层限 5 次/分钟、25 次/天
    for i, ticker in enumerate(tickers):
        if i > 0 and sleep_sec > 0:
            time.sleep(sleep_sec)  # 限速间隔（后台可配）
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
            # AV 一次返回全部历史月线，全量入库（"按历史预测分红"需要足够样本）；
            # 已存在（任意状态）的按 (代码, 近似除权日) 去重跳过。
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
            sec = security_service.upsert_security(session, "us_stock", ticker, ticker, _US_CURRENCY)
            session.add(DividendSchedule(
                security_id=sec.id, market="us_stock", code=ticker,
                ex_date=ex_date, record_date=ex_date, pay_date=ex_date,
                dps=round(amount, 4),
                div_type="cash", source="crawler",
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
        errors.append("us_stock: Alpha Vantage 暂时不可用或未配置 API Key")

    msg = "；".join(errors) if errors else None
    return {"fetched": total_fetched, "new_pending": total_new, "crawled_at": now_str(),
            "date": today_str(), "message": msg}


# ──────────────────────── 行情（最新价）抓取 ────────────────────────

_PUSH2_URL = "https://push2.eastmoney.com/api/qt/ulist.np/get"


def _a_share_secid(code: str) -> str:
    """东财行情 secid：6 开头=沪市(1)，其余=深市(0)。"""
    return f"1.{code}" if code.startswith("6") else f"0.{code}"


def crawl_prices(session: Session) -> int:
    """抓取 securities 表里所有标的的最新价，更新 latest_price / price_updated_at。

    - A股：东方财富 push2 批量行情接口（免费，无需 key）
    - 美股：Alpha Vantage GLOBAL_QUOTE（复用 av_api_key，限 5 次/分钟）
    不要求实时，每日日任务跑一次即可；网络失败静默降级。
    返回更新条数。
    """
    if os.getenv("XI_CRAWL_OFFLINE", "") == "1":
        return 0
    updated = 0

    # A 股：按 market 过滤（命中 uq_security_market_code 前导列），批量拉取，一次最多 80 只
    a_shares = session.exec(select(Security).where(Security.market == _MARKET)).all()
    for i in range(0, len(a_shares), 80):
        batch = a_shares[i:i + 80]
        secids = ",".join(_a_share_secid(s.code) for s in batch)
        try:
            data = _http_get_json(_PUSH2_URL, {
                "secids": secids, "fields": "f12,f14,f2",
            })
            rows = (data.get("data") or {}).get("diff") or []
            for r in rows:
                code = str(r.get("f12") or "")
                price = r.get("f2")
                if not code or price in (None, "-", ""):
                    continue
                try:
                    price_f = float(price)
                except (TypeError, ValueError):
                    continue
                if price_f <= 0:
                    continue
                security_service.update_price(session, _MARKET, code, price_f)
                updated += 1
        except Exception as e:
            log.warning("a_share price batch failed: %s", e)
    if updated:
        session.commit()

    # 美股：逐只 GLOBAL_QUOTE（受限于免费层 5 次/分钟），按 market 过滤命中唯一索引前导列
    us = session.exec(select(Security).where(Security.market == "us_stock")).all()
    api_key = config_service.get_text("av_api_key").strip()
    if us and api_key:
        sleep_sec = config_service.get_int("crawl_us_rate_sleep")
        for j, s in enumerate(us):
            if j > 0 and sleep_sec > 0:
                time.sleep(sleep_sec)
            try:
                data = _http_get_json(_AV_URL, {
                    "function": "GLOBAL_QUOTE", "symbol": s.code, "apikey": api_key,
                })
                quote = data.get("Global Quote") or {}
                price = quote.get("05. price")
                if price:
                    price_f = float(price)
                    if price_f > 0:
                        security_service.update_price(session, "us_stock", s.code, price_f)
                        updated += 1
            except Exception as e:
                log.info("us price %s failed: %s", s.code, e)
        session.commit()

    return updated
