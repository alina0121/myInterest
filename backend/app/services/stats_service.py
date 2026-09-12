"""统计服务：看板/趋势/市场占比/预测/排行（docs/03 §5、§6，docs/04 §六）。"""
import json
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from sqlmodel import Session, select

from ..models import Dividend, Holding, Lot
from ..utils.timeutil import days_ago_iso, today_str
from . import config_service, fx_service, security_service
from .lots_service import computed_summary, shares_now, cost_basis
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


def _user_holdings(session: Session, user_id: int,
                   account: str | None = None) -> list[Holding]:
    """带账户过滤的持仓查询。account='__all__'/None 表示不过滤。
    v8：不再按币种筛选，改为按 display_currency 转换显示。
    """
    stmt = select(Holding).where(Holding.user_id == user_id)
    if account and account != "__all__":
        stmt = stmt.where(Holding.account == account)
    return list(session.exec(stmt).all())


def _user_confirmed_filtered(session: Session, user_id: int,
                            account: str | None = None) -> list[Dividend]:
    """带账户过滤的已到账分红。无过滤时回退 _user_confirmed。
    v8：不再按币种筛选，改为按 display_currency 转换显示。
    """
    if not account or account == "__all__":
        return _user_confirmed(session, user_id)
    divs = _user_confirmed(session, user_id)
    holdings_map = {h.id: h for h in _user_holdings(session, user_id, account)}
    return [d for d in divs if d.holding_id in holdings_map]


def _net_cny(session: Session, div: Dividend) -> Decimal:
    return fx_service.to_cny(session, div.net_amount, div.currency, div.pay_date)


def _net_display(session: Session, div: Dividend,
                 display_currency: str | None = None) -> Decimal:
    """v8：按显示币种转换分红净额。
    - None/'CNY'：折人民币（用派息日汇率，历史归账不波动）
    - 'USD'/'HKD'：先折 CNY 再用今天汇率转成目标币种
    - 'ORIGINAL'：保留原币种金额
    """
    if not display_currency or display_currency == "CNY":
        return _net_cny(session, div)
    if display_currency == "ORIGINAL":
        return Decimal(str(div.net_amount)).quantize(Decimal("0.01"))
    # 先折 CNY（派息日汇率），再用今天汇率转成显示币种
    cny = _net_cny(session, div)
    return fx_service.from_cny(session, float(cny), display_currency, today_str())


def _gross_display(session: Session, div: Dividend,
                   display_currency: str | None = None) -> Decimal:
    """v8：按显示币种转换分红税前金额（用于 pending 分红预估）。"""
    if not display_currency or display_currency == "CNY":
        return fx_service.to_cny(session, div.gross_amount, div.currency, div.pay_date)
    if display_currency == "ORIGINAL":
        return Decimal(str(div.gross_amount)).quantize(Decimal("0.01"))
    cny = fx_service.to_cny(session, div.gross_amount, div.currency, div.pay_date)
    return fx_service.from_cny(session, float(cny), display_currency, today_str())


def summary(session: Session, user_id: int,
           account: str | None = None,
           display_currency: str | None = None) -> dict:
    """看板汇总（docs/04 §6.1）。金额按 display_currency 转换显示；

    - year_dividend：本年已到账税后分红（按派息日年份归属）
    - year_growth：同比 = (本年 - 去年) / 去年；去年为 0 时返回 None（不做除零）
    - ttm_dividend / ttm_monthly_avg：近 365 天税后分红 / 12（月均）
    - next_month_forecast：下月预告，取 pending 分红的【税前】折算
    - account/display_currency：v8 账户过滤 + 显示币种转换

    v8 修正：ORIGINAL 模式下聚合统计（跨持仓多币种混算）无意义，回落 CNY。
    单持仓的 holding_stats 仍保留 ORIGINAL 行为。
    """
    # v8：ORIGINAL 模式下聚合无意义（CNY+USD 混算），回落 CNY
    if display_currency == "ORIGINAL":
        display_currency = None
    divs = _user_confirmed_filtered(session, user_id, account)
    year = today_str()[:4]
    prev_year = str(int(year) - 1)

    year_amt = sum(_net_display(session, d, display_currency) for d in divs if d.pay_date[:4] == year)
    prev_amt = sum(_net_display(session, d, display_currency) for d in divs if d.pay_date[:4] == prev_year)
    month = today_str()[:7]
    month_divs = [d for d in divs if d.pay_date[:7] == month]

    holdings = _user_holdings(session, user_id, account)
    breakdown: dict[str, int] = {}
    for h in holdings:
        breakdown[h.market] = breakdown.get(h.market, 0) + 1

    since_years = [d.pay_date[:4] for d in divs]
    ttm_divs = [d for d in divs if d.pay_date >= days_ago_iso(365)]

    # 下月预告：pending 分红（税前折算）
    nxt = _month_add(month, 1)
    pendings = list(session.exec(
        select(Dividend).where(Dividend.user_id == user_id, Dividend.status == PENDING)
    ).all())
    # v8：pending 按账户过滤
    if account and account != "__all__":
        h_map = {h.id: h for h in _user_holdings(session, user_id, account)}
        pendings = [p for p in pendings if p.holding_id in h_map]
    next_month_forecast = sum(
        _gross_display(session, p, display_currency)
        for p in pendings if p.pay_date[:7] == nxt
    )

    return {
        "year_dividend": r2(year_amt),
        "year_growth": r2((year_amt - prev_amt) / prev_amt) if prev_amt > 0 else None,
        "month_dividend": r2(sum(_net_display(session, d, display_currency) for d in month_divs)),
        "month_count": len(month_divs),
        "total_dividend": r2(sum(_net_display(session, d, display_currency) for d in divs)),
        "since_year": int(min(since_years)) if since_years else None,
        "holding_count": len(holdings),
        "holding_breakdown": breakdown,
        "ttm_dividend": r2(sum(_net_display(session, d, display_currency) for d in ttm_divs)),
        "ttm_monthly_avg": r2(sum(_net_display(session, d, display_currency) for d in ttm_divs) / 12),
        "next_month_forecast": r2(next_month_forecast),
        "display_currency": display_currency or "CNY",
    }


def monthly_trend(session: Session, user_id: int, rng: str = "12m",
                  account: str | None = None,
                  display_currency: str | None = None) -> dict:
    """v8：支持 account 过滤 + display_currency 转换。
    v8 修正：ORIGINAL 模式下聚合多币种混算无意义，回落 CNY。
    """
    if display_currency == "ORIGINAL":
        display_currency = None
    divs = _user_confirmed_filtered(session, user_id, account)
    amounts: dict[str, Decimal] = {}
    for d in divs:
        key = d.pay_date[:7]
        amounts[key] = amounts.get(key, Decimal("0")) + _net_display(session, d, display_currency)

    if rng == "year":
        year = today_str()[:4]
        months = [f"{year}-{m:02d}" for m in range(1, 13)]
    elif rng == "all":
        since = summary(session, user_id, account, display_currency).get("since_year") or today_str()[:4]
        months, cur = [], f"{since}-01"
        while cur <= today_str()[:7]:
            months.append(cur)
            cur = _month_add(cur, 1)
    else:  # 12m
        months = _last_months(12)
    return {"months": months, "amounts": [r2(amounts.get(m, 0)) for m in months],
            "display_currency": display_currency or "CNY"}


def by_market(session: Session, user_id: int,
              account: str | None = None,
              display_currency: str | None = None) -> dict:
    """市场分红占比：分红表本身不存 market，需经 holding_id 反查持仓的市场。
    v9：统计页改为「原币种明细 + CNY 折算口径占比/总额」——
    - items[].amount：原币种金额（美股 $、港股 HK$、A股/基金 ¥）
    - items[].amount_cny：该市场折算 CNY（用于环形占比，跨币种可比）
    - items[].currency：该市场主要币种（前端据此显示符号）
    - total_cny：所有市场折算 CNY 总额（环形中心）
    """
    holdings = {h.id: h for h in _user_holdings(session, user_id, account)}
    agg_orig: dict[str, Decimal] = {}
    agg_cny: dict[str, Decimal] = {}
    cur_mode: dict[str, Counter] = {}
    for d in _user_confirmed_filtered(session, user_id, account):
        h = holdings.get(d.holding_id)
        if h:
            # 原币种金额直接相加（同市场通常同币种，不做汇率折算）
            agg_orig[h.market] = agg_orig.get(h.market, Decimal("0")) + Decimal(str(d.net_amount))
            # 折算 CNY 用于占比/排序
            agg_cny[h.market] = agg_cny.get(h.market, Decimal("0")) + _net_cny(session, d)
            cur_mode.setdefault(h.market, Counter())[h.currency] += 1
    items = [{
        "market": m,
        "amount": r2(agg_orig[m]),
        "amount_cny": r2(agg_cny[m]),
        "currency": cur_mode[m].most_common(1)[0][0] if cur_mode[m] else "CNY",
    } for m in agg_orig]
    items.sort(key=lambda x: x["amount_cny"], reverse=True)
    return {"items": items, "total_cny": r2(sum(agg_cny.values()))}


def forecast(session: Session, user_id: int,
             account: str | None = None,
             display_currency: str | None = None) -> dict:
    """未来 12 个月预测（docs/03 §6）。

    P0：published 全 0（预案表 P1 接入）；estimated 按近 3 年同月 dps 均值 × 当前持仓。
    后台关闭 forecast_by_history 时，estimated 直接全 0（只保留已公告预案口径）。
    v8：支持 account 过滤 + display_currency 转换。
    v8 修正：ORIGINAL 模式下聚合多币种混算无意义，回落 CNY。
    """
    if display_currency == "ORIGINAL":
        display_currency = None
    months = _last_months(1)  # placeholder to get current month key
    cur = months[0]
    future = [_month_add(cur, i) for i in range(1, 13)]
    history_enabled = config_service.get_bool("forecast_by_history")
    cutoff = (date.today() - timedelta(days=3 * 365)).isoformat()

    estimated = [Decimal("0")] * 12
    freq_summary: dict[str, int] = {}
    holdings = (_user_holdings(session, user_id, account)
                if history_enabled else [])

    today = today_str()
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
        for i, fm in enumerate(future):
            mm = fm[5:7]
            if mm not in months_set:
                continue
            dps_avg = sum(dps_by_mm[mm]) / len(dps_by_mm[mm])
            est_orig = Decimal(str(dps_avg)) * Decimal(str(now))
            # v8：按显示币种转换
            if not display_currency or display_currency == "CNY":
                estimated[i] += fx_service.to_cny(session, float(est_orig), h.currency, today)
            elif display_currency == "ORIGINAL":
                estimated[i] += est_orig
            else:
                cny = fx_service.to_cny(session, float(est_orig), h.currency, today)
                estimated[i] += fx_service.from_cny(session, float(cny), display_currency, today)

    return {
        "months": future,
        "published": [0] * 12,  # P1：已公告预案部分
        "estimated": [r2(v) for v in estimated],
        "freq_summary": freq_summary,
    }


def top_holdings(session: Session, user_id: int, limit: int = 10,
                 account: str | None = None,
                 display_currency: str | None = None) -> dict:
    """持仓分红贡献排行：分红表本身不存市场，需经 holding_id 反查持仓。
    v9：按 CNY 折算口径排序（跨币种可比），明细金额按原币种显示——
    - items[].amount：原币种累计分红（前端按 currency 显示符号）
    - items[].amount_cny：折算 CNY（用于排序与条形占比）
    - items[].currency：持仓币种
    """
    holdings = {h.id: h for h in _user_holdings(session, user_id, account)}
    agg_orig: dict[int, Decimal] = {}
    agg_cny: dict[int, Decimal] = {}
    for d in _user_confirmed_filtered(session, user_id, account):
        if d.holding_id in holdings:
            agg_orig[d.holding_id] = agg_orig.get(d.holding_id, Decimal("0")) + Decimal(str(d.net_amount))
            agg_cny[d.holding_id] = agg_cny.get(d.holding_id, Decimal("0")) + _net_cny(session, d)
    items = sorted(agg_cny.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return {"items": [{
        "holding_id": hid, "name": holdings[hid].name,
        "amount": r2(agg_orig[hid]), "amount_cny": r2(agg_cny[hid]),
        "currency": holdings[hid].currency,
    } for hid, _ in items]}


def yield_ranking(session: Session, user_id: int,
                  account: str | None = None,
                  display_currency: str | None = None) -> dict:
    """股息率排行：现价股息率（需手填现价）vs 成本股息率 YoC（docs/03 §5）。
    v9：金额字段（year_dividend / market_value）改为按原币种返回 + currency，
    前端按持仓币种显示符号；股息率是比值不受币种影响。
    """
    today = today_str()
    year = today[:4]
    holdings = _user_holdings(session, user_id, account)
    # 批量取 securities（含 latest_price）
    sec_map = security_service.security_map(
        session, [(h.market, h.code) for h in holdings])
    items = []
    user_divs = _user_confirmed_filtered(session, user_id, account)
    for h in holdings:
        cs = computed_summary(session, h)
        if cs["shares_now"] <= 0 or cs["ttm_dps"] <= 0:
            continue
        divs = [d for d in user_divs if d.holding_id == h.id]
        # 本年分红按原币种（d.net_amount 直接相加，不做汇率折算）
        year_div_amt = sum(Decimal(str(d.net_amount)) for d in divs if d.pay_date[:4] == year)
        # 现价：优先用 securities.latest_price（爬虫实时更新），回落 holdings.current_price
        sec = sec_map.get((h.market, h.code))
        latest_price = (sec.latest_price if sec and sec.latest_price else None) or h.current_price
        # 现价股息率 = TTM 每股分红 / 最新价（没价格则为 None，前端显示「—」）
        yield_price = (r4(cs["ttm_dps"] / latest_price)
                       if latest_price and latest_price > 0 else None)
        # 当前市值按原币种 = 最新价 × 净持仓（v9：不再折算）
        market_value = (r2(Decimal(str(latest_price)) * Decimal(str(cs["shares_now"])))
                        if latest_price else None)
        items.append({
            "holding_id": h.id, "name": h.name, "market": h.market,
            "currency": h.currency,
            "market_value": market_value,
            "year_dividend": r2(year_div_amt),
            "yield_price": yield_price,
            "yoc_ttm": cs["yoc_ttm"],
        })
    items.sort(key=lambda x: x["yoc_ttm"], reverse=True)
    return {"items": items}


def holding_stats(session: Session, h: Holding,
                  display_currency: str | None = None) -> dict:
    """单持仓统计（持仓详情页，docs/04 §6.7）。

    v8：支持 display_currency 转换。
    - year_net / total_net / yearly[].net：按显示币种折算的税后分红
    - year_gross：本年税前（原币种，gross_amount 求和）
    - cs 中的 year_dividend / total_dividend 仍为原币种
    """
    cs = computed_summary(session, h)
    divs = [d for d in session.exec(
        select(Dividend).where(Dividend.holding_id == h.id, Dividend.status == CONFIRMED)
    ).all()]
    year = today_str()[:4]
    yearly: dict[str, Decimal] = {}
    for d in divs:
        y = d.pay_date[:4]
        yearly[y] = yearly.get(y, Decimal("0")) + _net_display(session, d, display_currency)
    return {
        **cs,
        "year_gross": r2(sum(d.gross_amount for d in divs if d.pay_date[:4] == year)),
        "year_net": r2(sum(_net_display(session, d, display_currency) for d in divs if d.pay_date[:4] == year)),
        "total_net": r2(sum(_net_display(session, d, display_currency) for d in divs)),
        "yearly": [{"year": y, "net": r2(v)} for y, v in sorted(yearly.items())],
        "display_currency": display_currency or "CNY",
    }


# ========== Enhanced Summary (for new dashboard hero card) ==========

def enhanced_summary(session: Session, user_id: int,
                     account: str | None = None,
                     display_currency: str | None = None) -> dict:
    """新版看板汇总：所有可选指标一次性计算，前端按用户偏好选取展示。

    计算口径：
    - forecast_year: 预测年度分红 = forecast 12个月 estimated 合计
    - year_received: 今年已收（confirmed 当年）
    - total_cost: 总成本 = Σ 各 holding cost_total × 汇率
    - net_investment: 净投入 = 买入总额 − 卖出总额（原币 × 今日汇率）
    - market_value: 总市值 = Σ current_price × shares_now × 汇率
    - floating_pnl: 浮动盈亏 = 总市值 − 总成本
    - pnl_rate: 盈亏率 = 浮动盈亏 / 总成本
    - yield_on_cost: 成本息率 = 预测年分红 / 总成本
    - yield_on_price: 市值息率 = 预测年分红 / 总市值
    - monthly_forecast: 月均预测分红 = 预测年分红 / 12
    - daily_forecast: 日均预测分红 = 预测年分红 / 365
    - total_received: 累计收息（不限年）
    - holding_count: 持仓只数
    v8：支持 account 过滤 + display_currency 转换。
    v8 修正：ORIGINAL 模式下聚合多币种混算无意义，回落 CNY。
    """
    # v8：ORIGINAL 模式下聚合无意义（CNY+USD+HKD 混算），回落 CNY
    if display_currency == "ORIGINAL":
        display_currency = None
    today = today_str()

    # 1) 基础数据
    holdings = _user_holdings(session, user_id, account)
    divs_confirmed = _user_confirmed_filtered(session, user_id, account)
    year = today[:4]

    # 2) 预测年度分红（复用 forecast 的 estimated 12月合计）
    fc = forecast(session, user_id, account, display_currency)
    forecast_year = sum(Decimal(str(v)) for v in fc["estimated"])

    # 3) 今年已收 & 累计收息
    year_received = sum(_net_display(session, d, display_currency) for d in divs_confirmed if d.pay_date[:4] == year)
    total_received = sum(_net_display(session, d, display_currency) for d in divs_confirmed)

    # 4) 总成本 & 净投入 & 总市值（逐 holding 计算后聚合）
    total_cost = Decimal("0")
    market_value = Decimal("0")
    buy_total = Decimal("0")   # 买入总额（原币 × 今日汇率）
    sell_total = Decimal("0")  # 卖出总额（原币 × 今日汇率）

    # 批量取 securities（含 latest_price），避免逐 holding 查询
    sec_map = security_service.security_map(
        session, [(h.market, h.code) for h in holdings])

    for h in holdings:
        lots_list = list(session.exec(
            select(Lot).where(Lot.holding_id == h.id)
        ).all())
        n = shares_now(lots_list)
        cost = Decimal(str(cost_basis(lots_list)))   # 当前持仓的加权平均成本

        # v8：按显示币种转换成本
        if not display_currency or display_currency == "CNY":
            rate_today = fx_service.get_rate_cny(session, h.currency, today)
            total_cost += cost * rate_today
        elif display_currency == "ORIGINAL":
            total_cost += cost
        else:
            cny = cost * fx_service.get_rate_cny(session, h.currency, today)
            total_cost += fx_service.from_cny(session, float(cny), display_currency, today)

        # 总市值：优先用 securities.latest_price（爬虫实时更新），
        # 回落到 holdings.current_price（创建时快照，可能过时）
        sec = sec_map.get((h.market, h.code))
        latest_price = (sec.latest_price if sec and sec.latest_price else None) or h.current_price
        if latest_price and latest_price > 0:
            if not display_currency or display_currency == "CNY":
                rate_today = fx_service.get_rate_cny(session, h.currency, today)
                market_value += (Decimal(str(latest_price)) * Decimal(str(n))) * rate_today
            elif display_currency == "ORIGINAL":
                market_value += Decimal(str(latest_price)) * Decimal(str(n))
            else:
                cny = Decimal(str(latest_price)) * Decimal(str(n)) * fx_service.get_rate_cny(session, h.currency, today)
                market_value += fx_service.from_cny(session, float(cny), display_currency, today)

        # 买入/卖出总额（净投入 = 买入 − 卖出）
        for l in lots_list:
            if l.direction == "buy":
                buy_amt = Decimal(str(l.shares)) * Decimal(str(l.price)) + Decimal(str(l.fee or 0))
            elif l.direction == "sell":
                buy_amt = Decimal(str(l.shares)) * Decimal(str(l.price)) - Decimal(str(l.fee or 0))
            else:
                buy_amt = Decimal("0")
            if display_currency == "ORIGINAL":
                buy_total += buy_amt
            elif not display_currency or display_currency == "CNY":
                buy_total += buy_amt * fx_service.get_rate_cny(session, h.currency, today)
            else:
                cny = buy_amt * fx_service.get_rate_cny(session, h.currency, today)
                buy_total += fx_service.from_cny(session, float(cny), display_currency, today)
            if l.direction == "sell":
                sell_amt = Decimal(str(l.shares)) * Decimal(str(l.price)) - Decimal(str(l.fee or 0))
                if display_currency == "ORIGINAL":
                    sell_total += sell_amt
                elif not display_currency or display_currency == "CNY":
                    sell_total += sell_amt * fx_service.get_rate_cny(session, h.currency, today)
                else:
                    cny = sell_amt * fx_service.get_rate_cny(session, h.currency, today)
                    sell_total += fx_service.from_cny(session, float(cny), display_currency, today)

    net_investment = buy_total - sell_total

    # 5) 收益率 & 盈亏（分母为 0 时返回 None）
    floating_pnl = market_value - total_cost
    pnl_rate = (floating_pnl / total_cost) if total_cost > 0 else None
    yield_on_cost = (forecast_year / total_cost) if total_cost > 0 else None
    yield_on_price = (forecast_year / market_value) if market_value > 0 else None
    monthly_forecast = forecast_year / 12
    daily_forecast = forecast_year / 365

    # 6) 同比（复用原 summary 的 year_growth）
    prev_year = str(int(year) - 1)
    prev_amt = sum(_net_display(session, d, display_currency) for d in divs_confirmed if d.pay_date[:4] == prev_year)
    year_growth = (year_received - prev_amt) / prev_amt if prev_amt > 0 else None

    # v8：统一固定字段名（无后缀），返回 display_currency 标识
    return {
        # 核心指标
        "forecast_year": r2(forecast_year),
        "year_received": r2(year_received),
        "year_growth": r2(year_growth) if year_growth is not None else None,
        # 成本面
        "total_cost": r2(total_cost),
        "net_investment": r2(net_investment),
        # 估值面
        "market_value": r2(market_value),
        "holding_count": len(holdings),
        # 收益率
        "yield_on_cost": r4(yield_on_cost) if yield_on_cost is not None else None,
        "yield_on_price": r4(yield_on_price) if yield_on_price is not None else None,
        # 时间维度
        "monthly_forecast": r2(monthly_forecast),
        "daily_forecast": r2(daily_forecast),
        # 盈亏
        "floating_pnl": r2(floating_pnl),
        "pnl_rate": r4(pnl_rate) if pnl_rate is not None else None,
        # 累计
        "total_received": r2(total_received),
        # 显示币种标识
        "display_currency": display_currency or "CNY",
        # 预测明细（给前端图表用）
        "forecast_months": fc["months"],
        "forecast_published": fc["published"],
        "forecast_estimated": fc["estimated"],
    }


# ========== Dashboard Metric Registry ==========

# 所有可选指标定义（前端按此渲染设置页，后端按此计算）
# key 与 enhanced_summary 返回的字段名一一对应（v8 统一去掉 _cny 后缀）
DASHBOARD_METRICS = [
    {
        "key": "forecast_year",
        "name": "预测年度分红",
        "desc": "未来 12 个月分红预测合计",
        "category": "核心收益",
        "format": "currency",       # currency / percent / number / text
    },
    {
        "key": "year_received",
        "name": "今年已收",
        "desc": "当年已到账分红总额",
        "category": "核心收益",
        "format": "currency",
    },
    {
        "key": "total_cost",
        "name": "总成本",
        "desc": "各股买入成本 × 数量之和",
        "category": "成本面",
        "format": "currency",
    },
    {
        "key": "market_value",
        "name": "总市值",
        "desc": "最新价 × 数量之和（T-1）",
        "category": "估值面",
        "format": "currency",
    },
    {
        "key": "yield_on_cost",
        "name": "成本息率",
        "desc": "预测年分红 ÷ 总成本",
        "category": "收益率",
        "format": "percent",
    },
    {
        "key": "yield_on_price",
        "name": "市值息率",
        "desc": "预测年分红 ÷ 总市值",
        "category": "收益率",
        "format": "percent",
    },
    {
        "key": "monthly_forecast",
        "name": "月均预测分红",
        "desc": "预测年分红 ÷ 12",
        "category": "时间维度",
        "format": "currency",
    },
    {
        "key": "daily_forecast",
        "name": "日均预测分红",
        "desc": "预测年分红 ÷ 365",
        "category": "时间维度",
        "format": "currency",
    },
    {
        "key": "floating_pnl",
        "name": "浮动盈亏",
        "desc": "总市值 − 总成本（T-1）",
        "category": "盈亏",
        "format": "currency",
    },
    {
        "key": "pnl_rate",
        "name": "盈亏率",
        "desc": "浮动盈亏 ÷ 总成本（T-1）",
        "category": "盈亏",
        "format": "percent",
    },
    {
        "key": "total_received",
        "name": "累计收息",
        "desc": "历史已收分红总额（不限年）",
        "category": "累计",
        "format": "currency",
    },
    {
        "key": "net_investment",
        "name": "净投入",
        "desc": "买入总额 − 卖出总额",
        "category": "成本面",
        "format": "currency",
    },
    {
        "key": "holding_count",
        "name": "持仓只数",
        "desc": "当前持有标的数量",
        "category": "估值面",
        "format": "number",
    },
]

# 默认展示的 6 个指标（首次进入时）
DEFAULT_METRICS = [
    "forecast_year",   # 主指标
    "year_received",
    "total_cost",
    "market_value",
    "yield_on_cost",
    "yield_on_price",
]


def get_dashboard_metrics() -> list[dict]:
    """返回指标注册表（前端设置页渲染用）。"""
    return DASHBOARD_METRICS


def get_default_metrics() -> list[str]:
    return list(DEFAULT_METRICS)
