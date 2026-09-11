"""分红预案服务（docs/04 §五、§4.6；docs/06 §3.2）。

- auto-match：扫描已发布预案，为持有对应标的的用户生成 pending 分红（幂等）
- estimate：按归属算法预估某持仓在某预案下的股数/税前/税后（不落库）
- generate_forecast_schedules：季派/月派持仓按历史派息节奏生成推算预案
- check_dividend_reminders：派息日前 3 天/当天提醒检查
"""
import logging
from datetime import date as Date, timedelta
from sqlmodel import Session, select

from ..models import (Dividend, DividendSchedule, Holding, Lot, User, UserSetting)
from ..utils.timeutil import hold_days, today_str
from . import config_service, security_service
from .dividend_service import (BUY_DIRS, apply_allocation, compute_eligible,
                               default_record_date, tax_rate_for)
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
    """扫描已发布预案 → 为当前用户（或全体用户）生成 pending 分红（docs/04 §4.6）。

    幂等：同 (holding, schedule) 只生成一次；登记日无持仓股数则跳过。
    """
    schedules = session.exec(
        select(DividendSchedule)
        .where(DividendSchedule.status == "published",
               DividendSchedule.ex_date != None,  # noqa: E711
               DividendSchedule.dps != None)  # noqa: E711  要素不全的预案不参与自动匹配
        .order_by(DividendSchedule.ex_date)  # type: ignore
    ).all()
    if not schedules:
        return {"matched": 0, "created": [], "skipped": 0}

    # 一次性把用户持仓捞出来，按 (市场, 代码) 建索引，
    # 避免「预案数 × 持仓数」地反复查库
    holding_stmt = select(Holding)
    if user_id is not None:
        holding_stmt = holding_stmt.where(Holding.user_id == user_id)
    holdings = session.exec(holding_stmt).all()
    by_key: dict[tuple[str, str], list[Holding]] = {}
    for h in holdings:
        by_key.setdefault((h.market, h.code), []).append(h)  # 同一标的可能在多个账户持有

    created, skipped, matched = [], 0, 0
    for sch in schedules:
        for holding in by_key.get((sch.market, sch.code), []):
            # 用户关闭了「预案自动生成」则跳过（docs/02 §9）
            setting = session.get(UserSetting, holding.user_id)
            if setting and not setting.auto_match_schedule:
                continue
            # 幂等：该持仓已存在此预案生成的分红
            exists = session.exec(select(Dividend).where(
                Dividend.holding_id == holding.id,
                Dividend.schedule_id == sch.id)).first()
            if exists:
                continue
            # 登记日没有可参与分红的持仓（如股票已清仓）→ 跳过并计数
            est = estimate_for_holding(session, holding, sch)
            if est is None:
                skipped += 1
                continue
            # 生成的是 pending（待到账）：派息实际到账后由用户确认转 confirmed
            div = Dividend(
                user_id=holding.user_id, holding_id=holding.id, schedule_id=sch.id,
                ex_date=sch.ex_date, record_date=effective_record_date(sch, holding.market),
                pay_date=sch.pay_date or sch.ex_date, dps=r4(sch.dps),
                currency=holding.currency, div_type=sch.div_type,
                source="auto_schedule", status="pending",
            )
            session.add(div)
            session.flush()       # 先拿到 div.id，归属明细才能挂上去
            apply_allocation(session, div)  # 预生成批次归属明细（预估税费）
            created.append({"schedule_id": sch.id, "holding_id": holding.id,
                            "net_amount": div.net_amount})
            matched += 1
    session.commit()
    return {"matched": matched, "created": created, "skipped": skipped}


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
    """
    if not config_service.get_bool("forecast_freq"):
        return 0
    today = today_str()
    interval_map = {"monthly": 30, "quarterly": 90}
    holdings = session.exec(select(Holding).where(
        Holding.freq.in_(("monthly", "quarterly")))).all()  # type: ignore
    created = 0
    for h in holdings:
        days = interval_map[h.freq]
        last_div = session.exec(
            select(Dividend).where(Dividend.holding_id == h.id,
                                   Dividend.status == "confirmed")
            .order_by(Dividend.pay_date.desc())  # type: ignore
        ).first()
        if last_div is None or not last_div.pay_date:
            continue
        try:
            next_pay = (Date.fromisoformat(last_div.pay_date)
                        + timedelta(days=days)).isoformat()
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
            dps=r4(last_div.dps),
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
