"""批次与持仓聚合服务（docs/03 §1）——v0.3 改为实时计算。

「当前持仓数量、平均成本、总投入」不落库，由批次实时聚合。

v0.3 变更：
- computed_summary 里 Dividend 落表查询改为调 dividend_service.list_user_dividends 实时派生
- lot_out 里 DividendAllocation 落表查询（批次累计分红）在实时模式下不可从 lot 维度反查，
  暂时返回 0.0（需额外设计实时归属反向索引）
"""
from decimal import Decimal
from datetime import date

from sqlmodel import Session, select

from ..models import Holding, Lot
from ..utils.errors import AppError, Codes
from ..utils.timeutil import days_ago_iso, today_str
from .dividend_service import list_user_dividends
from .money import r2, r4

BUY_DIRS = ("buy", "bonus_share")


def get_lots(session: Session, holding_id: int) -> list[Lot]:
    return list(session.exec(
        select(Lot).where(Lot.holding_id == holding_id)
        .order_by(Lot.trade_date, Lot.id)  # type: ignore
    ).all())


def shares_now(lots: list[Lot]) -> float:
    """当前净持仓股数：买入/送股加，卖出减（不落库，实时聚合）。"""
    total = 0.0
    for l in lots:
        if l.direction in BUY_DIRS:
            total += l.shares
        elif l.direction == "sell":
            total -= l.shares
    return total


def cost_total(lots: list[Lot]) -> float:
    """总投入 = Σ 买入数量×价格 + 费用。

    口径：只统计 direction=buy 的真金白银投入；
    送股（bonus_share）价格为 0 自然不计；卖出回款不冲减成本（成本股息率分母用）。
    """
    return r2(sum((l.shares * l.price + l.fee) for l in lots if l.direction == "buy"))


def cost_basis(lots: list[Lot]) -> float:
    """当前持仓的加权平均成本（加权平均法）。

    与 cost_total 的区别：卖出时按比例冲减成本，反映当前实际持仓的成本。
    - 买入：成本 += shares × price + fee，股数 += shares
    - 卖出：成本 -= (成本/股数) × 卖出股数，股数 -= 卖出股数
    - 送股：股数 += shares，成本不变（摊薄每股成本）

    用于浮动盈亏、总成本展示、avg_cost 计算。
    """
    total_cost = Decimal("0")
    total_shares = Decimal("0")
    for l in sorted(lots, key=lambda x: (x.trade_date, x.id)):
        shares = Decimal(str(l.shares))
        price = Decimal(str(l.price))
        fee = Decimal(str(l.fee or 0))
        if l.direction == "buy":
            total_cost += shares * price + fee
            total_shares += shares
        elif l.direction == "bonus_share":
            total_shares += shares
        elif l.direction == "sell":
            if total_shares > 0:
                avg = total_cost / total_shares
                total_cost -= avg * shares
            total_shares -= shares
    return r2(total_cost)


def validate_sell(session: Session, holding_id: int, direction: str,
                  shares: float, exclude_lot_id: int | None = None) -> None:
    """卖出后净持仓不得为负（docs/03 §1.3）。"""
    if direction != "sell":
        return
    lots = [l for l in get_lots(session, holding_id) if l.id != exclude_lot_id]
    if shares_now(lots) - shares < 0:
        raise AppError(Codes.NEGATIVE_SHARES, "卖出数量超过当前持仓，拒绝", status=400)


def computed_summary(session: Session, h: Holding) -> dict:
    """持仓列表/详情的计算字段（docs/04 §2.1）。"""
    lots = get_lots(session, h.id)
    now = shares_now(lots)
    cost = cost_basis(lots)   # 当前持仓的加权平均成本（卖出按比例冲减）
    avg = r4(cost / now) if now > 0 else 0.0

    divs = [d for d in list_user_dividends(
        session, h.user_id, year=None, market=None, want_batches=False)
        if d["holding_id"] == h.id and d["status"] == "confirmed"]
    year = today_str()[:4]
    year_dividend = r2(sum(float(d["gross_amount"]) for d in divs if d["pay_date"][:4] == year))
    total_dividend = r2(sum(float(d["net_amount"]) for d in divs))

    # TTM 每股分红（每 share 口径）：近 365 天各次 dps 之和
    ttm_dps = sum(float(d["dps"]) for d in divs if d["pay_date"] >= days_ago_iso(365))
    yoc = r4(ttm_dps / avg) if avg > 0 and ttm_dps > 0 else 0.0

    return {
        "shares_now": round(now, 4),
        "avg_cost": avg,
        "cost_total": cost,
        "lot_count": len(lots),
        "year_dividend": year_dividend,
        "total_dividend": total_dividend,
        "ttm_dps": r4(ttm_dps),
        "yoc_ttm": yoc,
    }


def lot_out(session: Session, lot: Lot) -> dict:
    """批次输出：含批次金额与该批次累计分红（docs/04 §3.1）。

    v0.3：实时模式下 DividendAllocation 已删除，无法从 lot 维度反查历史累计分红，
    暂时 lot_dividend 返回 0.0（未来可从所有分红的 batches 里汇总）。
    """
    # 批次金额：买入=成交额+费用；卖出批次的费用通常已在回款中扣除，此处不再加
    amount = lot.shares * lot.price + (lot.fee if lot.direction == "buy" else 0)
    return {
        "id": lot.id,
        "trade_date": lot.trade_date,
        "direction": lot.direction,
        "shares": lot.shares,
        "price": lot.price,
        "fee": lot.fee,
        "amount": r2(amount),
        "lot_dividend": 0.0,  # v0.3：实时模式下无法从 lot 维度反查，暂置 0
        "note": lot.note,
    }
