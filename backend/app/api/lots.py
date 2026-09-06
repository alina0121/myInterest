"""批次接口：多批次买入/卖出/送转 CRUD（docs/04 §三）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..database import get_session
from ..models import Lot, User
from ..schemas import LotCreate, LotUpdate
from ..services import dividend_service, lots_service
from ..utils.errors import AppError, Codes, not_found, ok
from .deps import get_current_user
from .holdings import get_owned_holding, holding_out

router = APIRouter(tags=["lots"])


def get_owned_lot(session: Session, user: User, lot_id: int) -> Lot:
    lot = session.get(Lot, lot_id)
    if lot is None or lot.user_id != user.id:
        raise not_found()
    return lot


def _check_buy_price(direction: str, price: float) -> None:
    if direction == "buy" and price <= 0:
        raise AppError(Codes.VALIDATION, "买入批次成交价必须大于 0", status=422)
    if direction == "bonus_share" and price != 0:
        raise AppError(Codes.VALIDATION, "送转批次成交价必须为 0", status=422)


@router.get("/api/holdings/{holding_id}/lots")
def list_lots(holding_id: int, session: Session = Depends(get_session),
              user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    lots = lots_service.get_lots(session, h.id)
    return ok({"items": [lots_service.lot_out(session, l) for l in lots],
               "total": len(lots)})


@router.post("/api/holdings/{holding_id}/lots")
def create_lot(holding_id: int, body: LotCreate,
               session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    _check_buy_price(body.direction, body.price)
    lots_service.validate_sell(session, h.id, body.direction, body.shares)
    lot = Lot(user_id=user.id, holding_id=h.id, trade_date=body.trade_date.isoformat(),
              direction=body.direction, shares=body.shares, price=body.price,
              fee=body.fee, note=body.note)
    session.add(lot)
    session.commit()
    session.refresh(lot)
    # 触发相关分红重算（docs/03 §2.4）
    dividend_service.recalc_holding_dividends(session, h.id, lot.trade_date)
    return ok({"lot": lots_service.lot_out(session, lot), "holding": holding_out(session, h)})


@router.patch("/api/lots/{lot_id}")
def update_lot(lot_id: int, body: LotUpdate, session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    lot = get_owned_lot(session, user, lot_id)
    old_date = lot.trade_date
    changes = body.model_dump(exclude_unset=True)
    if "trade_date" in changes:
        changes["trade_date"] = changes["trade_date"].isoformat()
    new_direction = changes.get("direction", lot.direction)
    new_price = changes.get("price", lot.price)
    new_shares = changes.get("shares", lot.shares)
    _check_buy_price(new_direction, new_price)
    lots_service.validate_sell(session, lot.holding_id, new_direction, new_shares,
                               exclude_lot_id=lot.id)
    for k, v in changes.items():
        setattr(lot, k, v)
    session.add(lot)
    session.commit()
    from_date = min(old_date, lot.trade_date)
    dividend_service.recalc_holding_dividends(session, lot.holding_id, from_date)
    session.refresh(lot)
    return ok(lots_service.lot_out(session, lot))


@router.delete("/api/lots/{lot_id}")
def delete_lot(lot_id: int, session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    lot = get_owned_lot(session, user, lot_id)
    trade_date = lot.trade_date
    holding_id = lot.holding_id
    session.delete(lot)  # allocations.lot_id 由 FK SET NULL 保留快照
    session.commit()
    dividend_service.recalc_holding_dividends(session, holding_id, trade_date)
    return ok({"deleted": lot_id})
