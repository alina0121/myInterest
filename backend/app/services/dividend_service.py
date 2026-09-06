"""分红归属算法（docs/03 §2、§3）——本项目的核心业务。

规则：
1. 以「股权登记日 record_date」为归属判定日：trade_date <= record_date 的批次参与
2. 卖出按 FIFO 核销最早买入批次
3. 税费按「批次持有天数」分档（A股 0/10%/20%；美股 10%；港股通 20%；基金/债券 0）
4. 批次变更触发相关分红重算（tax_overridden 的分红保留税费）
"""
from datetime import date
from decimal import Decimal

from sqlmodel import Session, select

from ..models import Dividend, DividendAllocation, Holding, Lot, TaxRule
from ..utils.errors import AppError, Codes
from ..utils.timeutil import add_days, hold_days
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
    """未填登记日时的缺省：美股/港股/基金=除权日；A股=除权日前一自然日（提示校对）。"""
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


def apply_allocation(session: Session, div: Dividend) -> None:
    """对一笔分红执行归属计算：写 allocations 明细 + 回填 dividend 汇总字段。"""
    holding = session.get(Holding, div.holding_id)
    if holding is None:
        raise AppError(Codes.NOT_FOUND, "持仓不存在")
    lots = list(session.exec(
        select(Lot).where(Lot.holding_id == div.holding_id)
        .order_by(Lot.trade_date, Lot.id)  # type: ignore
    ).all())
    rd = div.record_date
    remaining, eligible = compute_eligible(lots, rd)
    if eligible <= 1e-9:
        raise AppError(Codes.NO_ELIGIBLE,
                       f"股权登记日 {rd} 无符合条件持仓股数，无法生成分红", status=400)

    dps = d(div.dps)
    new_allocs = []
    for lot in lots:
        if lot.direction not in BUY_DIRS:
            continue
        shares = remaining.get(lot.id, 0.0)
        if shares <= 1e-9:
            continue  # 已被卖出核销完或尚未买入（晚于登记日）→ 不产生归属行
        shares = r4(shares)
        gross = r2(shares * float(dps))
        rate = tax_rate_for(session, holding.market, hold_days(lot.trade_date, rd))
        tax = r2(Decimal(str(gross)) * rate)
        new_allocs.append(DividendAllocation(
            dividend_id=div.id, lot_id=lot.id, lot_date=lot.trade_date,
            shares=shares, gross=gross, tax=tax,
            net=r2(Decimal(str(gross)) - Decimal(str(tax))),
        ))

    for old in session.exec(select(DividendAllocation)
                            .where(DividendAllocation.dividend_id == div.id)).all():
        session.delete(old)
    session.add_all(new_allocs)
    session.flush()

    div.eligible_shares = r4(eligible)
    div.gross_amount = r2(sum(Decimal(str(a.gross)) for a in new_allocs))
    if not div.tax_overridden:
        div.tax = r2(sum(Decimal(str(a.tax)) for a in new_allocs))
    div.net_amount = r2(Decimal(str(div.gross_amount)) - Decimal(str(div.tax)))
    div.updated_at = div.updated_at  # 保持原值，由调用方负责


def recalc_holding_dividends(session: Session, holding_id: int, from_date: str) -> None:
    """批次新增/编辑/删除后重算该持仓 record_date >= 变更日的分红（docs/03 §2.4）。

    注：tax_overridden=1 的分红保留用户手工税费，仅重算股数与税前金额。
    """
    divs = session.exec(
        select(Dividend).where(Dividend.holding_id == holding_id,
                               Dividend.record_date >= from_date)  # type: ignore
    ).all()
    for div in divs:
        apply_allocation(session, div)
    session.commit()


def create_dividend(session: Session, user_id: int, holding: Holding,
                    ex_date: str, pay_date: str, dps: float,
                    record_date: str | None = None, tax: float | None = None,
                    div_type: str = "cash", status: str = "confirmed",
                    note: str | None = None, source: str = "manual") -> Dividend:
    if dps <= 0:
        raise AppError(Codes.VALIDATION, "每股分红 dps 必须大于 0", status=422)
    div = Dividend(
        user_id=user_id, holding_id=holding.id,
        ex_date=ex_date,
        record_date=record_date or default_record_date(holding.market, ex_date),
        pay_date=pay_date, dps=r4(dps), currency=holding.currency,
        div_type=div_type, status=status, source=source, note=note,
        tax_overridden=1 if tax is not None else 0,
    )
    if tax is not None:
        div.tax = r2(tax)
    session.add(div)
    session.flush()  # 取 div.id
    apply_allocation(session, div)
    session.commit()
    session.refresh(div)
    return div
