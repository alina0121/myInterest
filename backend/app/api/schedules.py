"""分红预案用户端接口（docs/04 §五）：即将到账 + 全市场查询。"""
from datetime import date as Date

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Dividend, DividendSchedule, Holding, User
from ..services import fx_service, schedule_service
from ..utils.errors import ok
from ..utils.timeutil import today_str
from .deps import get_current_user

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("/upcoming")
def upcoming(session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    """我的即将到账：仅返回当前用户持有标的的已发布预案（docs/04 §5.1）。"""
    today = today_str()
    # 用户持仓按 (市场,代码) 建索引：全市场预案只保留「我持有」的
    holdings = session.exec(select(Holding).where(Holding.user_id == user.id)).all()
    by_key = {(h.market, h.code): h for h in holdings}

    # 只看已发布且要素完整（有除权日 + dps）的预案
    schedules = session.exec(
        select(DividendSchedule)
        .where(DividendSchedule.status == "published",
               DividendSchedule.ex_date != None,  # noqa: E711
               DividendSchedule.dps != None)  # noqa: E711
        .order_by(DividendSchedule.ex_date)  # type: ignore
    ).all()

    items, month_total = [], 0.0
    month = today[:7]
    for sch in schedules:
        holding = by_key.get((sch.market, sch.code))
        if holding is None:
            continue  # 没持有这只票，与我无关
        eff = sch.pay_date or sch.ex_date  # 排序/月份归集用
        if eff < today:
            continue  # 已过期的预案不展示在「即将到账」
        est = schedule_service.estimate_for_holding(session, holding, sch)
        if est is None:
            continue  # 登记日没有可参与的持仓（如登记日后才建仓）
        # 该预案是否已生成过分红记录：前端据此隐藏「一键生成」按钮，避免重复
        has_record = session.exec(select(Dividend).where(
            Dividend.holding_id == holding.id,
            Dividend.schedule_id == sch.id)).first() is not None
        items.append({
            "id": sch.id, "market": sch.market, "code": sch.code, "name": sch.name,
            "record_date": schedule_service.effective_record_date(sch, holding.market),
            "ex_date": sch.ex_date, "pay_date": sch.pay_date,
            "dps": sch.dps, "currency": sch.currency,
            **est, "has_dividend_record": has_record,
            # 距派息还剩几天（前端做倒计时/提醒高亮）
            "days_to_pay": (Date.fromisoformat(eff) - Date.fromisoformat(today)).days
            if eff else None,
        })
        # 本月预计到账合计（税后折 CNY），看板卡片用
        if eff and eff[:7] == month:
            month_total += float(fx_service.to_cny(session, est["est_net"],
                                                   sch.currency, eff))
    # 派息日缺失时退回用除权日排序，同日期再按代码排，顺序稳定
    items.sort(key=lambda x: (x["pay_date"] or x["ex_date"], x["code"]))
    return ok({"items": items, "month_total_cny": round(month_total, 2)})


@router.get("")
def list_schedules(market: str | None = None, keyword: str | None = None,
                   page: int = 1, page_size: int = 20,
                   session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    """预案查询：全市场已发布预案分页（docs/04 §5.2）。"""
    stmt = select(DividendSchedule).where(DividendSchedule.status == "published")
    if market:
        stmt = stmt.where(DividendSchedule.market == market)
    schedules = list(session.exec(
        stmt.order_by(DividendSchedule.ex_date.desc(), DividendSchedule.id.desc())  # type: ignore
    ).all())
    if keyword:
        kw = keyword.lower()
        schedules = [s for s in schedules
                     if kw in s.code.lower() or kw in s.name.lower()]
    total = len(schedules)
    start = (page - 1) * page_size
    return ok({
        "items": [{
            "id": s.id, "market": s.market, "code": s.code, "name": s.name,
            "ex_date": s.ex_date, "record_date": s.record_date, "pay_date": s.pay_date,
            "dps": s.dps, "currency": s.currency, "div_type": s.div_type,
        } for s in schedules[start:start + page_size]],
        "total": total, "page": page, "page_size": page_size,
    })
