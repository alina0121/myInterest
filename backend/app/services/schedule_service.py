"""分红预案服务（docs/04 §五；docs/06 §3.2）——v0.3 改为实时计算。

- estimate：按归属算法预估某持仓在某预案下的股数/税前/税后（不落库）
- auto-match：v0.3 改为纯占位（实时模式下分红不落表）
- generate_forecast_schedules：季派/月派持仓按历史派息节奏生成推算预案
- check_dividend_reminders：派息日前 3 天/当天提醒检查

v0.3 变更：
- 删除 auto-match 里的落表逻辑（Dividend/DividendAllocation），改为返回空结果
- generate_forecast_schedules 里 Dividend 查询改为调 dividend_service.list_user_dividends
"""
import logging
from datetime import date as Date, timedelta
from sqlmodel import Session, select

from ..models import DividendSchedule, Holding, Lot, UserSetting
from ..utils.timeutil import hold_days, today_str
from . import config_service, security_service
from .dividend_service import (BUY_DIRS, compute_eligible,
                               default_record_date, tax_rate_for,
                               list_user_dividends)
from .money import r2, r4

log = logging.getLogger("xi.schedule")


def effective_record_date(sch: DividendSchedule, market: str) -> str:
    """预案登记日缺省口径与手动记账一致：A股=除权日前一自然日。"""
    return sch.record_date or default_record_date(market, sch.ex_date)


def get_lots(session: Session, holding_id: int) -> list[Lot]:
    return list(session.exec(
        select(Lot).where(Lot.holding_id == holding_id)
        .order_by(Lot.trade_date, Lot.id)  # type: ignore
    ).all())


def estimate_for_holding(session: Session, holding: Holding,
                         sch: DividendSchedule) -> dict | None:
    """按归属算法预估（docs/04 §5.1 my_shares/est_*）；无符合股数返回 None。"""
    if not sch.ex_date or not sch.dps:
        return None
    rd = effective_record_date(sch, holding.market)
    lots = get_lots(session, holding.id)
    remaining, eligible = compute_eligible(lots, rd)
    if eligible <= 1e-9:
        return None
    shares = r4(eligible)
    gross = r2(shares * float(sch.dps))
    # 税费预估：按批次持有天数分档，与归属算法同口径
    tax = 0.0
    for lot in lots:
        if lot.direction not in BUY_DIRS:
            continue
        lot_shares = float(remaining.get(lot.id, 0.0))
        if lot_shares <= 1e-9:
            continue
        rate = tax_rate_for(session, holding.market, hold_days(lot.trade_date, rd))
        tax += lot_shares * float(sch.dps) * float(rate)
    return {"my_shares": shares, "est_gross": gross, "est_net": r2(gross - r2(tax))}


def auto_match(session: Session, user_id: int | None = None) -> dict:
    """v0.3：实时计算模式下 auto-match 已废弃（分红不落表）。

    保留函数签名避免调用方报错，直接返回空结果。
    """
    return {
        "matched": 0,
        "created": [],
        "skipped": 0,
        "note": "实时计算模式下 auto-match 已废弃，分红数据每次查询时实时派生",
    }


def auto_match_all_background() -> None:
    """预案发布后的后台任务：开独立 Session 跑全体用户 auto-match。"""
    from ..database import engine
    with Session(engine) as session:
        auto_match(session)


def run_daily_job() -> None:
    """定时任务入口：爬取预案 + 全体用户 auto-match（docs/06 §3.2）。"""
    from . import crawler_service
    from ..database import engine
    with Session(engine) as session:
        try:
            crawler_service.run_crawl(session)
        except Exception:  # pragma: no cover - 定时任务不允许中断
            pass
        try:
            crawler_service.crawl_prices(session)
        except Exception:  # pragma: no cover
            pass
        auto_match(session)
        generate_forecast_schedules(session)
        check_dividend_reminders(session)


def generate_forecast_schedules(session: Session) -> int:
    """季派/月派持仓按历史派息节奏生成推算预案（受系统配置 forecast_freq 控制）。

    对 freq 为 monthly/quarterly 的持仓，取最近一笔已确认分红的派息日，
    叠加对应间隔（月派 1 个月 / 季派 3 个月）推算下一次派息日，
    生成一条 pending 预案（source=forecast，需人工审核）。
    幂等：同 (market, code, ex_date) 已存在任意状态预案则跳过。
    返回生成条数。

    v0.3 变更：已确认分红从 dividend_service.list_user_dividends 实时查询获取。
    """
    if not config_service.get_bool("forecast_freq"):
        return 0
    today = today_str()
    interval_map = {"monthly": 30, "quarterly": 90}
    holdings = session.exec(select(Holding).where(
        Holding.freq.in_(("monthly", "quarterly")))).all()  # type: ignore
    created = 0
    # 按 user_id 缓存分红列表，避免同一用户多持仓时重复实时计算
    user_div_cache: dict[int, list[dict]] = {}
    for h in holdings:
        if h.user_id not in user_div_cache:
            user_div_cache[h.user_id] = list_user_dividends(
                session, h.user_id, year=None, market=None, want_batches=False)
        holding_divs = [d for d in user_div_cache[h.user_id]
                        if d["holding_id"] == h.id and d["status"] == "confirmed"]
        if not holding_divs:
            continue
        # 按 pay_date 倒序，取最近一条
        holding_divs.sort(key=lambda d: d.get("pay_date") or "", reverse=True)
        last_div = holding_divs[0]
        last_pay_date = last_div.get("pay_date")
        last_dps = last_div.get("dps")
        if not last_pay_date or not last_dps:
            continue
        try:
            next_pay = (Date.fromisoformat(last_pay_date)
                        + timedelta(days=interval_map[h.freq])).isoformat()
        except ValueError:
            continue
        if next_pay <= today:
            continue  # 推算日已过，等下一轮
        # 幂等：同标的同推算除权日已存在预案则跳过
        exists = session.exec(select(DividendSchedule).where(
            DividendSchedule.market == h.market,
            DividendSchedule.code == h.code,
            DividendSchedule.ex_date == next_pay)).first()
        if exists:
            continue
        sec = security_service.upsert_security(session, h.market, h.code, h.name, h.currency)
        session.add(DividendSchedule(
            security_id=sec.id, market=h.market, code=h.code,
            ex_date=next_pay, pay_date=next_pay,
            dps=r4(float(last_dps)),
            div_type="cash", source="forecast",
            confidence=0.65, status="pending",
            raw_title=f"{h.name} {h.freq} 推算预案（基于历史派息节奏）"[:200],
        ))
        created += 1
    session.commit()
    if created:
        log.info("forecast schedules generated: %d", created)
    return created


def check_dividend_reminders(session: Session) -> int:
    """派息日前 3 天 / 当天提醒检查（受系统配置 remind_3d 控制）。

    扫描 pay_date 在 [今天, 今天+3] 的已发布预案，对持仓且开启提醒的用户
    记录日志（实际推送通道 V2 接入）。返回触发提醒的用户数。
    """
    if not config_service.get_bool("remind_3d"):
        return 0
    today = today_str()
    window_end = (Date.fromisoformat(today) + timedelta(days=3)).isoformat()
    schedules = session.exec(select(DividendSchedule).where(
        DividendSchedule.status == "published",
        DividendSchedule.pay_date != None,  # noqa: E711
        DividendSchedule.pay_date >= today,
        DividendSchedule.pay_date <= window_end)).all()
    if not schedules:
        return 0
    reminded_users: set[int] = set()
    for sch in schedules:
        holdings = session.exec(select(Holding).where(
            Holding.market == sch.market, Holding.code == sch.code)).all()
        for h in holdings:
            setting = session.get(UserSetting, h.user_id)
            # 用户未开启推送或未开启派息日提醒 → 跳过
            if setting and (not setting.push_enabled or not setting.remind_on_payday):
                continue
            reminded_users.add(h.user_id)
            sec = security_service.get_security(session, sch.market, sch.code)
            sec_name = sec.name if sec else sch.code
            log.info("dividend reminder: user=%s %s %s pay_date=%s",
                     h.user_id, sch.code, sec_name, sch.pay_date)
    return len(reminded_users)
