"""分红实时计算服务（docs/03 §2、§3）——无落表，纯派生。

所有分红数据实时计算得出：DividendSchedule（预案）是唯一数据源，
Lot（用户交易批次）是归属判定依据。不再落表 Dividend/DividendAllocation。

规则：
1. 以「股权登记日 record_date」为归属判定日：trade_date <= record_date 的批次参与
2. 卖出按 FIFO 核销最早买入批次
3. 税费按「批次持有天数」分档（A股 0/10%/20%；美股 10%；港股通 20%；基金/债券 0）
4. 待到账/已到账：用 pay_date 与今天比较（pay_date >= today 为待到账）
"""
from datetime import date as _date
from decimal import Decimal

from sqlmodel import Session, select

from ..models import DividendSchedule, Holding, Lot, TaxRule
from ..utils.timeutil import add_days, hold_days, today_str
from .money import d, r2, r4

BUY_DIRS = ("buy", "bonus_share")

# tax_rules 表不可用时的兜底税率
_FALLBACK_RATE = {"us_stock": 0.10, "hk_stock": 0.20}
_FALLBACK_A_SHARE = ((366, 0.00), (31, 0.10), (0, 0.20))


def tax_rate_for(session: Session, market: str, hold_days_: int) -> Decimal:
    """按市场 + 批次持有天数取税率（tax_rules 表，docs/02 §8 种子数据）。"""
    rules = session.exec(
        select(TaxRule).where(TaxRule.market == market, TaxRule.enabled == 1)
    ).all()
    for r in rules:
        lo = r.hold_min_days if r.hold_min_days is not None else 0
        hi = r.hold_max_days
        if hold_days_ >= lo and (hi is None or hold_days_ <= hi):
            return d(r.rate)
    if market == "a_share":
        for min_days, rate in _FALLBACK_A_SHARE:
            if hold_days_ >= min_days:
                return d(rate)
    return d(_FALLBACK_RATE.get(market, 0.0))


def default_record_date(market: str, ex_date: str) -> str:
    """未填登记日时的缺省：美股/港股/基金=除权日；A股=除权日前一自然日。"""
    return add_days(ex_date, -1) if market == "a_share" else ex_date


def compute_eligible(lots: list[Lot], record_date: str) -> tuple[dict[int, float], float]:
    """纯函数：返回 {批次id: 登记日仍持有股数} 与总 eligible 股数。

    sells（trade_date <= record_date）按 FIFO 从最早买入批次核销。
    """
    buys = [l for l in lots if l.direction in BUY_DIRS and l.trade_date <= record_date]
    remaining = {l.id: float(l.shares) for l in buys}
    order = [l.id for l in buys]
    sells = [l for l in lots if l.direction == "sell" and l.trade_date <= record_date]
    for s in sells:
        need = float(s.shares)
        for lid in order:
            if need <= 1e-9:
                break
            take = min(remaining[lid], need)
            remaining[lid] -= take
            need -= take
    eligible = sum(remaining.values())
    return remaining, eligible


def _calc_dividend_for_holding(session: Session, holding: Holding,
                               sch: DividendSchedule) -> dict | None:
    """对单条预案 + 单个持仓做完整计算，返回分红明细 dict（不落表）。"""
    if not sch.ex_date or not sch.dps:
        return None  # 预案要素不全（缺除权日或 dps）则跳过
    rd = sch.record_date or default_record_date(holding.market, sch.ex_date)
    lots = list(session.exec(
        select(Lot).where(Lot.holding_id == holding.id)
        .order_by(Lot.trade_date, Lot.id)  # type: ignore
    ).all())
    remaining, eligible = compute_eligible(lots, rd)
    if eligible <= 1e-9:
        return None  # 登记日无持仓 → 不产生分红

    dps = d(sch.dps)
    gross = r2(r4(eligible) * float(dps))

    # 按批次分档算税费
    tax = Decimal("0")
    batches = []
    for lot in lots:
        if lot.direction not in BUY_DIRS:
            continue
        shares = remaining.get(lot.id, 0.0)
        if shares <= 1e-9:
            continue
        shares = r4(shares)
        lot_gross = r2(shares * float(dps))
        rate = tax_rate_for(session, holding.market, hold_days(lot.trade_date, rd))
        lot_tax = r2(Decimal(str(lot_gross)) * rate)
        tax += Decimal(str(lot_tax))
        batches.append({
            "lot_date": lot.trade_date,
            "shares": shares,
            "gross": lot_gross,
            "tax": lot_tax,
            "rate": float(rate),
        })

    tax = r2(float(tax))
    net = r2(gross - tax)

    # 状态：用 pay_date 与今天比较（待落到账/已到账）
    today = today_str()
    pay_date = sch.pay_date or sch.ex_date
    status = "pending" if pay_date >= today else "confirmed"

    return {
        "holding_id": holding.id,
        "security_id": sch.security_id,
        "schedule_id": sch.id,
        "market": sch.market,
        "code": sch.code,
        "name": sch.code,  # 由调用方填，这里只放基础数据
        "ex_date": sch.ex_date,
        "record_date": rd,
        "pay_date": pay_date,
        "dps": r4(float(dps)),
        "eligible_shares": r4(eligible),
        "gross_amount": gross,
        "tax": tax,
        "net_amount": net,
        "currency": holding.currency,
        "div_type": sch.div_type,
        "status": status,
        "batches": batches,
    }


def list_user_dividends(session: Session, user_id: int,
                        year: str | None = None,
                        market: str | None = None,
                        want_batches: bool = False) -> list[dict]:
    """主入口：实时计算指定用户的全部分红列表。

    扫描所有已发布预案，匹配用户持仓，对每条匹配做完整计算。
    不落表，每次调用都从 DividendSchedule + Lot 派生。
    """
    # 拉全量已发布预案（含 ex_date 和 dps）
    stmt = select(DividendSchedule).where(
        DividendSchedule.status == "published",
        DividendSchedule.ex_date != None,  # noqa: E711
        DividendSchedule.dps != None,      # noqa: E711
    )
    schedules = session.exec(stmt).all()
    if not schedules:
        return []

    # 拉用户全部持仓，按 (market, code) 建索引
    holdings = session.exec(
        select(Holding).where(Holding.user_id == user_id)
    ).all()
    by_key: dict[tuple[str, str], list[Holding]] = {}
    for h in holdings:
        by_key.setdefault((h.market, h.code), []).append(h)

    results: list[dict] = []
    for sch in schedules:
        for h in by_key.get((sch.market, sch.code), []):
            row = _calc_dividend_for_holding(session, h, sch)
            if row is None:
                continue
            # 过滤（如果是 None 跳过，year/market 过滤在 list 返回前做）
            if market and row["market"] != market:
                continue
            if year and row["pay_date"] and not row["pay_date"].startswith(year):
                continue
            # 补 name（查 securities）
            from .security_service import get_security
            sec = get_security(session, h.market, h.code)
            if sec:
                row["name"] = sec.name or row["code"]
            # 按调用要求裁剪批次明细
            if not want_batches:
                row.pop("batches", None)
            results.append(row)

    # 按 pay_date 降序
    results.sort(key=lambda r: r["pay_date"] or "", reverse=True)
    return results


def estimate_for_holding(session: Session, holding: Holding,
                         sch: DividendSchedule) -> dict | None:
    """按归属算法预估某持仓在某预案下的股数/税前/税后（不落库，docs/04 §5.1）。"""
    return _calc_dividend_for_holding(session, holding, sch)


def recalc_holding_dividends(session: Session, holding_id: int, from_date: str) -> None:
    """批次变更后触发重算——实时计算模式无需重算入口，查询时自动算对。占位保留。"""
    pass
