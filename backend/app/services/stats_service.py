"""统计服务：看板/趋势/市场占比/预测/排行（docs/03 §5、§6，docs/04 §六）。"""
from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from ..models import Dividend, Holding
from ..utils.timeutil import days_ago_iso, today_str
from . import fx_service
from .lots_service import computed_summary
from .money import r2, r4

CONFIRMED = "confirmed"
PENDING = "pending"


def _month_add(ym: str, n: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    total = y * 12 + (m - 1) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _last_months(n: int) -> list[str]:
    cur = today_str()[:7]
    return [_month_add(cur, -i) for i in range(n - 1, -1, -1)]


def _user_confirmed(session: Session, user_id: int) -> list[Dividend]:
    return list(session.exec(
        select(Dividend).where(Dividend.user_id == user_id,
                               Dividend.status == CONFIRMED)
    ).all())


def _net_cny(session: Session, div: Dividend) -> Decimal:
    return fx_service.to_cny(session, div.net_amount, div.currency, div.pay_date)


def summary(session: Session, user_id: int) -> dict:
    divs = _user_confirmed(session, user_id)
    year = today_str()[:4]
    prev_year = str(int(year) - 1)

    year_cny = sum(_net_cny(session, d) for d in divs if d.pay_date[:4] == year)
    prev_cny = sum(_net_cny(session, d) for d in divs if d.pay_date[:4] == prev_year)
    month = today_str()[:7]
    month_divs = [d for d in divs if d.pay_date[:7] == month]

    holdings = list(session.exec(select(Holding).where(Holding.user_id == user_id)).all())
    breakdown: dict[str, int] = {}
    for h in holdings:
        breakdown[h.market] = breakdown.get(h.market, 0) + 1

    since_years = [d.pay_date[:4] for d in divs]
    ttm_divs = [d for d in divs if d.pay_date >= days_ago_iso(365)]

    # 下月预告：pending 分红（税前折 CNY）
    nxt = _month_add(month, 1)
    pendings = list(session.exec(
        select(Dividend).where(Dividend.user_id == user_id, Dividend.status == PENDING)
    ).all())
    next_month_forecast = sum(
        fx_service.to_cny(session, p.gross_amount, p.currency, p.pay_date)
        for p in pendings if p.pay_date[:7] == nxt
    )

    year_cny_f, prev_cny_f = r2(year_cny), r2(prev_cny)
    return {
        "year_dividend_cny": year_cny_f,
        "year_growth": r2((year_cny - prev_cny) / prev_cny) if prev_cny > 0 else None,
        "month_dividend_cny": r2(sum(_net_cny(session, d) for d in month_divs)),
        "month_count": len(month_divs),
        "total_dividend_cny": r2(sum(_net_cny(session, d) for d in divs)),
        "since_year": int(min(since_years)) if since_years else None,
        "holding_count": len(holdings),
        "holding_breakdown": breakdown,
        "ttm_dividend_cny": r2(sum(_net_cny(session, d) for d in ttm_divs)),
        "ttm_monthly_avg": r2(sum(_net_cny(session, d) for d in ttm_divs) / 12),
        "next_month_forecast_cny": r2(next_month_forecast),
    }


def monthly_trend(session: Session, user_id: int, rng: str = "12m") -> dict:
    divs = _user_confirmed(session, user_id)
    amounts: dict[str, Decimal] = {}
    for d in divs:
        key = d.pay_date[:7]
        amounts[key] = amounts.get(key, Decimal("0")) + _net_cny(session, d)

    if rng == "year":
        year = today_str()[:4]
        months = [f"{year}-{m:02d}" for m in range(1, 13)]
    elif rng == "all":
        since = summary(session, user_id).get("since_year") or today_str()[:4]
        months, cur = [], f"{since}-01"
        while cur <= today_str()[:7]:
            months.append(cur)
            cur = _month_add(cur, 1)
    else:  # 12m
        months = _last_months(12)
    return {"months": months, "amounts_cny": [r2(amounts.get(m, 0)) for m in months]}


def by_market(session: Session, user_id: int) -> dict:
    holdings = {h.id: h.market for h in
                session.exec(select(Holding).where(Holding.user_id == user_id)).all()}
    agg: dict[str, Decimal] = {}
    for d in _user_confirmed(session, user_id):
        market = holdings.get(d.holding_id)
        if market:
            agg[market] = agg.get(market, Decimal("0")) + _net_cny(session, d)
    return {"items": [{"market": m, "amount_cny": r2(v)} for m, v in agg.items()]}


def forecast(session: Session, user_id: int) -> dict:
    """未来 12 个月预测（docs/03 §6）。

    P0：published 全 0（预案表 P1 接入）；estimated 按近 3 年同月 dps 均值 × 当前持仓。
    """
    months = _last_months(1)  # placeholder to get current month key
    cur = months[0]
    future = [_month_add(cur, i) for i in range(1, 13)]
    cutoff = (date.today() - timedelta(days=3 * 365)).isoformat()

    estimated = [Decimal("0")] * 12
    freq_summary: dict[str, int] = {}
    holdings = list(session.exec(select(Holding).where(Holding.user_id == user_id)).all())

    for h in holdings:
        freq_summary[h.freq] = freq_summary.get(h.freq, 0) + 1
        divs = list(session.exec(
            select(Dividend).where(Dividend.holding_id == h.id,
                                   Dividend.status == CONFIRMED,
                                   Dividend.pay_date >= cutoff)  # type: ignore
        ).all())
        if not divs:
            continue
        months_set = {d.pay_date[5:7] for d in divs}
        # 近 3 年同月份 dps 均值
        dps_by_mm: dict[str, list[float]] = {}
        for d in divs:
            dps_by_mm.setdefault(d.pay_date[5:7], []).append(d.dps)
        now = computed_summary(session, h)["shares_now"]
        if now <= 0:
            continue
        today = today_str()
        for i, fm in enumerate(future):
            mm = fm[5:7]
            if mm not in months_set:
                continue
            dps_avg = sum(dps_by_mm[mm]) / len(dps_by_mm[mm])
            est_orig = Decimal(str(dps_avg)) * Decimal(str(now))
            estimated[i] += fx_service.to_cny(session, float(est_orig), h.currency, today)

    return {
        "months": future,
        "published": [0] * 12,  # P1：已公告预案部分
        "estimated": [r2(v) for v in estimated],
        "freq_summary": freq_summary,
    }


def top_holdings(session: Session, user_id: int, limit: int = 10) -> dict:
    holdings = {h.id: h for h in
                session.exec(select(Holding).where(Holding.user_id == user_id)).all()}
    agg: dict[int, Decimal] = {}
    for d in _user_confirmed(session, user_id):
        if d.holding_id in holdings:
            agg[d.holding_id] = agg.get(d.holding_id, Decimal("0")) + _net_cny(session, d)
    items = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return {"items": [{"holding_id": hid, "name": holdings[hid].name, "amount_cny": r2(v)}
                      for hid, v in items]}


def yield_ranking(session: Session, user_id: int) -> dict:
    """股息率排行：现价股息率（需手填现价）vs 成本股息率 YoC（docs/03 §5）。"""
    today = today_str()
    year = today[:4]
    items = []
    for h in session.exec(select(Holding).where(Holding.user_id == user_id)).all():
        cs = computed_summary(session, h)
        if cs["shares_now"] <= 0 or cs["ttm_dps"] <= 0:
            continue
        divs = [d for d in _user_confirmed(session, user_id) if d.holding_id == h.id]
        year_div_cny = sum(_net_cny(session, d) for d in divs if d.pay_date[:4] == year)
        yield_price = (r4(cs["ttm_dps"] / h.current_price)
                       if h.current_price and h.current_price > 0 else None)
        market_value = (r2(Decimal(str(h.current_price)) * Decimal(str(cs["shares_now"]))
                           * fx_service.get_rate_cny(session, h.currency, today))
                        if h.current_price else None)
        items.append({
            "holding_id": h.id, "name": h.name, "market": h.market,
            "market_value_cny": market_value,
            "year_dividend_cny": r2(year_div_cny),
            "yield_price": yield_price,
            "yoc_ttm": cs["yoc_ttm"],
        })
    items.sort(key=lambda x: x["yoc_ttm"], reverse=True)
    return {"items": items}


def holding_stats(session: Session, h: Holding) -> dict:
    """单持仓统计（持仓详情页，docs/04 §6.7）。"""
    cs = computed_summary(session, h)
    divs = [d for d in session.exec(
        select(Dividend).where(Dividend.holding_id == h.id, Dividend.status == CONFIRMED)
    ).all()]
    year = today_str()[:4]
    yearly: dict[str, Decimal] = {}
    for d in divs:
        y = d.pay_date[:4]
        yearly[y] = yearly.get(y, Decimal("0")) + _net_cny(session, d)
    return {
        **cs,
        "year_gross": r2(sum(d.gross_amount for d in divs if d.pay_date[:4] == year)),
        "year_net_cny": r2(sum(_net_cny(session, d) for d in divs if d.pay_date[:4] == year)),
        "total_net": cs["total_dividend"],
        "total_net_cny": r2(sum(_net_cny(session, d) for d in divs)),
        "yearly": [{"year": y, "net_cny": r2(v)} for y, v in sorted(yearly.items())],
    }
