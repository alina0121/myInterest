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
    last_day = _cal.monthrange(year, month)[1]
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year:04d}-{month:02d}-{last_day:02d}"
    holdings = {h.id: h for h in
                session.exec(select(Holding).where(Holding.user_id == user.id)).all()}
    divs = list(session.exec(
        select(Dividend).where(Dividend.user_id == user.id,
                               Dividend.pay_date >= start,
                               Dividend.pay_date <= end)  # type: ignore
    ).all())

    days: dict[str, list] = {}
    confirmed_cny, pending_cny = 0.0, 0.0
    for d in divs:
        day = str(int(d.pay_date[8:10]))
        h = holdings.get(d.holding_id)
        if h is None:
            continue
        days.setdefault(day, []).append({
            "holding_id": h.id, "holding_name": h.name, "code": h.code,
            "dps": d.dps, "shares": d.eligible_shares,
            "gross": d.gross_amount, "tax": d.tax, "net": d.net_amount,
            "currency": d.currency, "status": d.status,
        })
        if d.status == "confirmed":
            confirmed_cny += float(fx_service.to_cny(session, d.net_amount,
                                                     d.currency, d.pay_date))
        else:
            pending_cny += float(fx_service.to_cny(session, d.gross_amount,
                                                   d.currency, d.pay_date))
    return ok({"year": year, "month": month, "days": days,
               "month_confirmed_cny": round(confirmed_cny, 2),
               "month_pending_cny": round(pending_cny, 2)})
