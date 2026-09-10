"""分红日历接口（docs/04 §五）。"""
import calendar as _cal

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Dividend, Holding, User
from ..services import fx_service
from ..utils.errors import ok
from .deps import get_current_user

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("")
def calendar(year: int, month: int, session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    # monthrange 返回 (星期几, 当月天数)，用于拼月末日期
    last_day = _cal.monthrange(year, month)[1]
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year:04d}-{month:02d}-{last_day:02d}"
    holdings = {h.id: h for h in
                session.exec(select(Holding).where(Holding.user_id == user.id)).all()}
    # 按【派息日】落在本月筛分红（含已到账 + 待到账）
    divs = list(session.exec(
        select(Dividend).where(Dividend.user_id == user.id,
                               Dividend.pay_date >= start,
                               Dividend.pay_date <= end)  # type: ignore
    ).all())

    # days: {"15": [当天分红...], "28": [...]}，前端日历按「日」挂点
    days: dict[str, list] = {}
    confirmed_cny, pending_cny = 0.0, 0.0
    for d in divs:
        day = str(int(d.pay_date[8:10]))  # 派息日的「几号」，去掉前导 0 方便前端 key
        h = holdings.get(d.holding_id)
        if h is None:
            continue
        days.setdefault(day, []).append({
            "holding_id": h.id, "holding_name": h.name, "code": h.code,
            "dps": d.dps, "shares": d.eligible_shares,
            "gross": d.gross_amount, "tax": d.tax, "net": d.net_amount,
            "currency": d.currency, "status": d.status,
        })
        # 月合计口径不同：已到账算税后净收入；待到账只能算税前预估
        if d.status == "confirmed":
            confirmed_cny += float(fx_service.to_cny(session, d.net_amount,
                                                     d.currency, d.pay_date))
        else:
            pending_cny += float(fx_service.to_cny(session, d.gross_amount,
                                                   d.currency, d.pay_date))
    return ok({"year": year, "month": month, "days": days,
               "month_confirmed_cny": round(confirmed_cny, 2),
               "month_pending_cny": round(pending_cny, 2)})
