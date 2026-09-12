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
def calendar(year: int, month: int, account: str | None = None,
             display_currency: str | None = None,
             session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    """v8：支持 account 过滤 + display_currency 转换。"""
    from datetime import date as _date
    # monthrange 返回 (星期几, 当月天数)，用于拼月末日期
    last_day = _cal.monthrange(year, month)[1]
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year:04d}-{month:02d}-{last_day:02d}"
    # v8：按账户过滤持仓
    hold_query = select(Holding).where(Holding.user_id == user.id)
    if account:
        hold_query = hold_query.where(Holding.account == account)
    holdings = {h.id: h for h in session.exec(hold_query).all()}
    holding_ids = set(holdings.keys())
    # 按【派息日】落在本月筛分红（含已到账 + 待到账）
    divs = list(session.exec(
        select(Dividend).where(Dividend.user_id == user.id,
                               Dividend.pay_date >= start,
                               Dividend.pay_date <= end)  # type: ignore
    ).all())
    # v8：只保留属于当前账户持仓的分红
    divs = [d for d in divs if d.holding_id in holding_ids]

    today = _date.today().isoformat()
    # days: {"15": [当天分红...], "28": [...]}，前端日历按「日」挂点
    days: dict[str, list] = {}
    confirmed_amt, pending_amt = 0.0, 0.0
    for d in divs:
        day = str(int(d.pay_date[8:10]))  # 派息日的「几号」，去掉前导 0 方便前端 key
        h = holdings.get(d.holding_id)
        if h is None:
            continue
        # v8：按显示币种转换
        if not display_currency or display_currency == "CNY":
            net_disp = float(fx_service.to_cny(session, d.net_amount, d.currency, d.pay_date))
            gross_disp = float(fx_service.to_cny(session, d.gross_amount, d.currency, d.pay_date))
        elif display_currency == "ORIGINAL":
            net_disp = float(d.net_amount)
            gross_disp = float(d.gross_amount)
        else:
            net_cny = float(fx_service.to_cny(session, d.net_amount, d.currency, d.pay_date))
            net_disp = float(fx_service.from_cny(session, net_cny, display_currency, today))
            gross_cny = float(fx_service.to_cny(session, d.gross_amount, d.currency, d.pay_date))
            gross_disp = float(fx_service.from_cny(session, gross_cny, display_currency, today))
        days.setdefault(day, []).append({
            "holding_id": h.id, "holding_name": h.name, "code": h.code,
            "dps": d.dps, "shares": d.eligible_shares,
            "gross": d.gross_amount, "tax": d.tax, "net": d.net_amount,
            f"net_display": net_disp, "display_currency": display_currency or "CNY",
            "currency": d.currency, "status": d.status,
        })
        # 月合计口径不同：已到账算税后净收入；待到账只能算税前预估
        if d.status == "confirmed":
            confirmed_amt += net_disp
        else:
            pending_amt += gross_disp
    return ok({"year": year, "month": month, "days": days,
               "month_confirmed": round(confirmed_amt, 2),
               "month_pending": round(pending_amt, 2),
               "display_currency": display_currency or "CNY"})
