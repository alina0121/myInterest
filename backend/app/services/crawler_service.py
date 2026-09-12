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
import json
import logging
import os
import re
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
    # 白名单优先从 securities 表读（crawl_enabled=True）；
    # 表为空时用配置项兜底，并自动建 securities 记录标记为白名单
    tickers = security_service.get_crawl_enabled_codes(session, "us_stock")
    if not tickers:
        tickers = config_service.get_list("crawl_us_tickers")
        for t in tickers:
            security_service.upsert_security(session, "us_stock", t, t, "USD", crawl_enabled=True)
            security_service.set_crawl_enabled(session, "us_stock", t, True)
        session.commit()
        log.info("us_stock whitelist seeded from config: %s", tickers)
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


# ──────────────────────── 港股分红 ────────────────────────

_HK_F10_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
_HK_REPORT = "RPT_HKF10_MAIN_DIVBASIC"
_HK_CURRENCY = "HKD"

# 从「每股派港币5.3元」中提取金额；兼容美元/人民币表述
_HK_AMOUNT_RE = re.compile(r"派([^0-9]*)([\d.]+)")


def _hk_normalize_date(v: str | None) -> str | None:
    """东财港股日期格式 '2026/05/15' → '2026-05-15'。"""
    if not v:
        return None
    s = str(v).strip().replace("/", "-")[:10]
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except ValueError:
        return None


def _hk_parse_amount(plan_explain: str) -> tuple[float | None, str]:
    """从分红方案文本解析每股金额与币种。

    样例：「每股派港币5.3元」「每股派美元0.244元(相当于港币1.898元)」「每股派人民币0.5元」
    规则：取「派」字后的第一个数字；币种按文本关键词推断，默认 HKD。
    """
    if not plan_explain:
        return None, _HK_CURRENCY
    m = _HK_AMOUNT_RE.search(plan_explain)
    if not m:
        return None, _HK_CURRENCY
    try:
        amount = float(m.group(2))
    except ValueError:
        return None, _HK_CURRENCY
    text = plan_explain
    if "美元" in text or "USD" in text.upper():
        currency = "USD"
    elif "人民币" in text or "CNY" in text.upper():
        currency = "CNY"
    else:
        currency = _HK_CURRENCY
    return amount, currency


def crawl_hk_stock(session: Session) -> tuple[int, int]:
    """抓取港股分红预案（东方财富港股 F10 分红送配）。

    数据源：datacenter.eastmoney.com reportName=RPT_HKF10_MAIN_DIVBASIC
    按白名单 (crawl_hk_tickers) 逐只拉取；每股金额从 PLAN_EXPLAIN 文本解析。
    返回 (fetched, new_pending)。
    """
    fetched, new_pending = 0, 0
    # 白名单优先从 securities 表读（crawl_enabled=True）；
    # 表为空时用配置项兜底，并自动建 securities 记录标记为白名单
    tickers = security_service.get_crawl_enabled_codes(session, "hk_stock")
    if not tickers:
        tickers = config_service.get_list("crawl_hk_tickers")
        for t in tickers:
            security_service.upsert_security(session, "hk_stock", t, t, "HKD", crawl_enabled=True)
            security_service.set_crawl_enabled(session, "hk_stock", t, True)
        session.commit()
        log.info("hk_stock whitelist seeded from config: %s", tickers)
    sleep_sec = config_service.get_int("crawl_hk_rate_sleep")
    if not tickers:
        log.info("hk_stock crawl skipped: no crawl_enabled securities and config whitelist empty")
        return 0, 0

    for i, code in enumerate(tickers):
        if i > 0 and sleep_sec > 0:
            time.sleep(sleep_sec)
        try:
            data = _http_get_json(_HK_F10_URL, {
                "reportName": _HK_REPORT, "columns": "ALL",
                "filter": f'(SECURITY_CODE="{code}")(IS_BFP="0")',
                "pageNumber": 1, "pageSize": 50,
                "sortTypes": "-1,-1", "sortColumns": "NOTICE_DATE,EX_DIVIDEND_DATE",
                "source": "F10", "client": "PC",
            })
        except Exception as e:
            log.info("hk %s fetch failed: %s", code, e)
            continue

        rows = (data.get("result") or {}).get("data") or []
        # 取该股票名称（优先用 securities 表已有名称，否则用代码）
        sec_name = code
        existing_sec = security_service.get_security(session, "hk_stock", code)
        if existing_sec and existing_sec.name:
            sec_name = existing_sec.name

        for row in rows:
            ex = _hk_normalize_date(row.get("EX_DIVIDEND_DATE"))
            if not ex:
                continue  # 无除权日的记录无法去重，跳过
            pay = _hk_normalize_date(row.get("DIVIDEND_DATE"))
            # TRANSFER_END_DATE 形如 '2026/05/19-2026/05/20'，取首日作为登记日近似
            rec_raw = str(row.get("TRANSFER_END_DATE") or "")
            rec = _hk_normalize_date(rec_raw.split("-")[0] if "-" in rec_raw else rec_raw) or ex
            amount, currency = _hk_parse_amount(row.get("PLAN_EXPLAIN") or "")
            if amount is None or amount <= 0:
                continue
            fetched += 1
            # 去重：同 (市场,代码,除权日) 任意状态已存在则跳过
            if session.exec(select(DividendSchedule).where(
                    DividendSchedule.market == "hk_stock",
                    DividendSchedule.code == code,
                    DividendSchedule.ex_date == ex)).first():
                continue
            sec = security_service.upsert_security(session, "hk_stock", code, sec_name, currency)
            session.add(DividendSchedule(
                security_id=sec.id, market="hk_stock", code=code,
                ex_date=ex, record_date=rec, pay_date=pay,
                dps=round(amount, 4), div_type="cash", source="crawler",
                confidence=0.85,  # 官方公告但需人工核对金额解析
                status="pending",
                raw_title=str(row.get("PLAN_EXPLAIN") or f"{code} dividend")[:200],
            ))
            new_pending += 1

    session.commit()
    return fetched, new_pending


# ──────────────────────── 基金分红 ────────────────────────

_FUND_URL = "https://fund.eastmoney.com/Data/funddataIndex_Interface.aspx"
_FUND_CURRENCY = "CNY"


def crawl_fund(session: Session) -> tuple[int, int]:
    """抓取基金分红预案（天天基金分红列表）。

    数据源：fund.eastmoney.com/Data/funddataIndex_Interface.aspx?dt=8
    按登记日倒序分页增量抓取；返回 (fetched, new_pending)。
    响应为 JS 文本：var pageinfo=[total,pageSize,page]; var jjfh_data=[[code,name,rec,ex,dps,pay,type],...]
    """
    fetched, new_pending = 0, 0
    page_size = config_service.get_int("crawl_fund_page_size")
    max_pages = config_service.get_int("crawl_fund_max_pages")
    page_size = max(10, min(200, int(page_size)))

    for page in range(1, max_pages + 1):
        try:
            resp = httpx.get(_FUND_URL, params={
                "dt": 8, "page": page, "rank": "DJR", "sort": "desc",
                "gs": "", "ftype": "", "year": "",
            }, timeout=15.0, headers={"User-Agent": "Mozilla/5.0 (xi-dividend-tracker)"})
            resp.raise_for_status()
            text = resp.text
        except Exception as e:
            log.info("fund page %s fetch failed: %s", page, e)
            break

        # 解析 var jjfh_data=[[...],[...]]
        m = re.search(r"var\s+jjfh_data\s*=\s*(\[.*?\]);", text, re.DOTALL)
        if not m:
            break
        try:
            rows = json.loads(m.group(1))
        except (json.JSONDecodeError, ValueError):
            break
        if not isinstance(rows, list) or not rows:
            break

        page_inserts = 0
        for row in rows:
            if not isinstance(row, list) or len(row) < 6:
                continue
            code, name = str(row[0] or ""), str(row[1] or "")
            rec, ex, dps_str, pay = row[2], row[3], row[4], row[5]
            if not code or not name:
                continue
            try:
                dps = float(dps_str) if dps_str not in (None, "") else 0.0
            except (TypeError, ValueError):
                dps = 0.0
            if dps <= 0 or not ex:
                continue
            fetched += 1
            # 去重：同 (市场,代码,除权日)
            if session.exec(select(DividendSchedule).where(
                    DividendSchedule.market == "fund",
                    DividendSchedule.code == code,
                    DividendSchedule.ex_date == ex)).first():
                continue
            sec = security_service.upsert_security(session, "fund", code, name, _FUND_CURRENCY)
            session.add(DividendSchedule(
                security_id=sec.id, market="fund", code=code,
                ex_date=ex, record_date=rec or ex, pay_date=pay,
                dps=round(dps, 4), div_type="cash", source="crawler",
                confidence=0.90,  # 天天基金官方列表，字段完整
                status="pending",
                raw_title=f"{name} 分红"[:200],
            ))
            page_inserts += 1
            new_pending += 1

        session.commit()  # 每页提交一次
        # 增量停止：本页无新增 → 后续更老的页必然已入库
        if page_inserts == 0:
            break
        # 末页不足一页 → 没有更多数据
        if len(rows) < page_size:
            break

    return fetched, new_pending


# ──────────────────────── 统一调度 ────────────────────────

def run_crawl(session: Session, market: str | None = None) -> dict:
    """立即触发采集（docs/04 §11.3 /crawl）。离线或失败返回 0 并附 message。

    market 参数：
      - None / 'all'：顺序执行所有市场分支
      - 'a_share' / 'us_stock' / 'hk_stock' / 'fund'：仅爬指定市场
    任一分支异常不中断其他分支。
    """
    if os.getenv("XI_CRAWL_OFFLINE", "") == "1":
        return {"fetched": 0, "new_pending": 0, "message": "爬虫离线模式（XI_CRAWL_OFFLINE=1）"}

    targets = [market] if market and market != "all" else ["a_share", "us_stock", "hk_stock", "fund"]
    total_fetched, total_new = 0, 0
    errors = []
    # 各市场对应的爬取函数与失败提示
    dispatch = {
        "a_share": (crawl_a_share, "a_share: 数据源暂时不可用"),
        "us_stock": (crawl_us_stock, "us_stock: Alpha Vantage 暂时不可用或未配置 API Key"),
        "hk_stock": (crawl_hk_stock, "hk_stock: 东方财富 F10 暂时不可用"),
        "fund": (crawl_fund, "fund: 天天基金分红接口暂时不可用"),
    }

    for m in targets:
        fn, err_msg = dispatch.get(m, (None, None))
        if fn is None:
            errors.append(f"{m}: 未知市场")
            continue
        try:
            f, n = fn(session)
            total_fetched += f
            total_new += n
        except Exception as e:
            log.warning("%s crawl failed: %s", m, e)
            session.rollback()
            errors.append(err_msg)

    msg = "；".join(errors) if errors else None
    # 新预案入库后重算各标的派息频率（securities.freq 供持仓下拉默认带出）
    try:
        security_service.refresh_all_freq(session)
    except Exception as e:
        log.warning("refresh security freq failed: %s", e)
        session.rollback()
    return {"fetched": total_fetched, "new_pending": total_new, "crawled_at": now_str(),
            "date": today_str(), "message": msg}


# ──────────────────────── 行情（最新价）抓取 ────────────────────────

_TENCENT_QT_URL = "http://qt.gtimg.cn/q="


def _tencent_symbol(market: str, code: str) -> str:
    """腾讯行情代码前缀。

    - 港股：hk + code
    - A股/基金：6/5 开头=沪市(sh)，其余=深市(sz)
    """
    if market == "hk_stock":
        return f"hk{code}"
    return f"sh{code}" if code[0] in ("6", "5") else f"sz{code}"


def crawl_prices(session: Session) -> int:
    """抓取 securities 表里所有标的的最新价，更新 latest_price / price_updated_at。

    - A股/港股/基金：腾讯行情批量接口（免费，无需 key，价格单位直接是元）
    - 美股：Alpha Vantage GLOBAL_QUOTE（复用 av_api_key，限 5 次/分钟）
    不要求实时，每日日任务跑一次即可；网络失败静默降级。
    返回更新条数。
    """
    if os.getenv("XI_CRAWL_OFFLINE", "") == "1":
        return 0
    updated = 0

    # A股 / 港股 / 基金：统一走腾讯行情批量接口，一次最多 50 只
    cn_markets = ("a_share", "hk_stock", "fund")
    for market in cn_markets:
        secs = session.exec(select(Security).where(Security.market == market)).all()
        if not secs:
            continue
        for i in range(0, len(secs), 50):
            batch = secs[i:i + 50]
            symbols = ",".join(_tencent_symbol(market, s.code) for s in batch)
            try:
                resp = httpx.get(_TENCENT_QT_URL + symbols, timeout=10,
                                 headers={"User-Agent": "Mozilla/5.0 (xi-dividend-tracker)"})
                resp.raise_for_status()
                for line in resp.text.strip().split("\n"):
                    if "=" not in line:
                        continue
                    _, val = line.split("=", 1)
                    parts = val.strip('";').split("~")
                    if len(parts) < 4:
                        continue
                    code = parts[2]
                    try:
                        price_f = float(parts[3])
                    except (TypeError, ValueError):
                        continue
                    if price_f <= 0:
                        continue
                    security_service.update_price(session, market, code, price_f)
                    updated += 1
            except Exception as e:
                log.warning("%s price batch failed: %s", market, e)
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
