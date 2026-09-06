"""分红记录接口：CRUD + 确认（docs/04 §四）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Dividend, DividendAllocation, Holding, User
from ..schemas import ConfirmIn, DividendCreate, DividendUpdate
from ..services import dividend_service, fx_service
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.timeutil import now_str
from .deps import get_current_user
from .holdings import get_owned_holding

router = APIRouter(prefix="/api/dividends", tags=["dividends"])


def get_owned_dividend(session: Session, user: User, dividend_id: int) -> Dividend:
    d = session.get(Dividend, dividend_id)
    if d is None or d.user_id != user.id:
        raise not_found()
    return d


def dividend_out(session: Session, d: Dividend, holding: Holding,
                 with_allocations: bool = False) -> dict:
    data = {
        "id": d.id, "holding_id": d.holding_id,
        "holding_name": holding.name, "code": holding.code, "market": holding.market,
        "ex_date": d.ex_date, "record_date": d.record_date, "pay_date": d.pay_date,
        "dps": d.dps, "shares": d.eligible_shares,
        "gross_amount": d.gross_amount, "tax": d.tax, "net_amount": d.net_amount,
        "net_cny": float(fx_service.to_cny(session, d.net_amount, d.currency, d.pay_date)),
        "currency": d.currency, "div_type": d.div_type, "source": d.source,
        "status": d.status, "tax_overridden": bool(d.tax_overridden), "note": d.note,
    }
    if with_allocations:
        allocs = session.exec(select(DividendAllocation)
                              .where(DividendAllocation.dividend_id == d.id)
                              .order_by(DividendAllocation.lot_date)).all()  # type: ignore
        data["allocations"] = [{
            "lot_id": a.lot_id, "lot_date": a.lot_date, "shares": a.shares,
            "gross": a.gross, "tax": a.tax, "net": a.net,
        } for a in allocs]
    return data


@router.get("")
def list_dividends(year: int | None = None, market: str | None = None,
                   holding_id: int | None = None, status: str | None = None,
                   page: int = 1, page_size: int = 20, expand: str | None = None,
                   session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    holdings = {h.id: h for h in
                session.exec(select(Holding).where(Holding.user_id == user.id)).all()}
    divs = list(session.exec(
        select(Dividend).where(Dividend.user_id == user.id)
        .order_by(Dividend.pay_date.desc(), Dividend.id.desc())  # type: ignore
    ).all())

    if holding_id is not None:
        divs = [d for d in divs if d.holding_id == holding_id]
    elif market is not None:
        ids = {hid for hid, h in holdings.items() if h.market == market}
        divs = [d for d in divs if d.holding_id in ids]
    if year is not None:
        divs = [d for d in divs if d.pay_date[:4] == str(year)]
    if status is not None:
        divs = [d for d in divs if d.status == status]

    total = len(divs)
    start = (page - 1) * page_size
    slice_ = divs[start:start + page_size]
    want_alloc = expand is not None and "allocations" in expand
    return ok({
        "items": [dividend_out(session, d, holdings[d.holding_id], want_alloc)
                  for d in slice_],
        "total": total, "page": page, "page_size": page_size,
    })


@router.post("")
def create_dividend(body: DividendCreate, session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, body.holding_id)
    d = dividend_service.create_dividend(
        session, user.id, h,
        ex_date=body.ex_date.isoformat(),
        pay_date=body.pay_date.isoformat(),
        dps=body.dps,
        record_date=body.record_date.isoformat() if body.record_date else None,
        tax=body.tax, div_type=body.div_type, status=body.status, note=body.note,
    )
    if body.record_date is None and h.market == "a_share":
        d.updated_at = d.updated_at  # no-op，保持字段
    out = dividend_out(session, d, h, True)
    out["record_date_auto"] = (body.record_date is None and h.market == "a_share")
    return ok(out)


@router.get("/{dividend_id}")
def get_dividend(dividend_id: int, session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    d = get_owned_dividend(session, user, dividend_id)
    h = session.get(Holding, d.holding_id)
    return ok(dividend_out(session, d, h, True))


@router.patch("/{dividend_id}")
def update_dividend(dividend_id: int, body: DividendUpdate,
                    session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    d = get_owned_dividend(session, user, dividend_id)
    changes = body.model_dump(exclude_unset=True)
    for k in ("ex_date", "record_date", "pay_date"):
        if k in changes:
            changes[k] = changes[k].isoformat()
    if "tax" in changes:
        d.tax_overridden = 1
    for k, v in changes.items():
        setattr(d, k, v)
    d.updated_at = now_str()
    session.add(d)
    session.flush()
    dividend_service.apply_allocation(session, d)  # 重算归属（税 overridden 时保留税费）
    session.commit()
    session.refresh(d)
    h = session.get(Holding, d.holding_id)
    return ok(dividend_out(session, d, h, True))


@router.delete("/{dividend_id}")
def delete_dividend(dividend_id: int, session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    d = get_owned_dividend(session, user, dividend_id)
    for a in session.exec(select(DividendAllocation)
                          .where(DividendAllocation.dividend_id == d.id)).all():
        session.delete(a)
    session.delete(d)
    session.commit()
    return ok({"deleted": dividend_id})


@router.post("/{dividend_id}/confirm")
def confirm_dividend(dividend_id: int, body: ConfirmIn,
                     session: Session = Depends(get_session),
                     user: User = Depends(get_current_user)):
    d = get_owned_dividend(session, user, dividend_id)
    if d.status == "confirmed":
        raise AppError(Codes.VALIDATION, "该分红已确认", status=422)
    d.status = "confirmed"
    if body.actual_net is not None:
        d.net_amount = round(body.actual_net, 2)
        d.tax = round(d.gross_amount - body.actual_net, 2)
        d.tax_overridden = 1
    d.updated_at = now_str()
    session.add(d)
    session.commit()
    session.refresh(d)
    h = session.get(Holding, d.holding_id)
    return ok(dividend_out(session, d, h, True))
