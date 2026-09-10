"""持仓接口：CRUD + 计算字段（docs/04 §二）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Dividend, DividendAllocation, Holding, Lot, User
from ..schemas import HoldingCreate, HoldingUpdate
from ..services import lots_service
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.timeutil import now_str
from .deps import get_current_user

router = APIRouter(prefix="/api/holdings", tags=["holdings"])


def get_owned_holding(session: Session, user: User, holding_id: int) -> Holding:
    h = session.get(Holding, holding_id)
    # 归属校验：他人的资源一律 404，不暴露存在性（docs/01 §5）
    if h is None or h.user_id != user.id:
        raise not_found()
    return h


def holding_out(session: Session, h: Holding) -> dict:
    return {
        "id": h.id, "market": h.market, "code": h.code, "name": h.name,
        "currency": h.currency, "account": h.account, "freq": h.freq,
        "note": h.note, "current_price": h.current_price,
        "created_at": h.created_at,
        **lots_service.computed_summary(session, h),
    }


@router.get("")
def list_holdings(market: str | None = None, keyword: str | None = None,
                  freq: str | None = None,
                  session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    stmt = select(Holding).where(Holding.user_id == user.id)
    if market:
        stmt = stmt.where(Holding.market == market)
    if freq:
        stmt = stmt.where(Holding.freq == freq)
    holdings = list(session.exec(stmt.order_by(Holding.id.desc())).all())  # type: ignore
    if keyword:
        kw = keyword.lower()
        holdings = [h for h in holdings
                    if kw in h.code.lower() or kw in h.name.lower()]
    return ok({"items": [holding_out(session, h) for h in holdings], "total": len(holdings)})


@router.post("")
def create_holding(body: HoldingCreate, session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    dup = session.exec(select(Holding).where(
        Holding.user_id == user.id, Holding.market == body.market,
        Holding.code == body.code)).first()
    if dup:
        raise AppError(Codes.HOLDING_EXISTS, "该标的持仓已存在，可直接添加批次", status=409)
    h = Holding(user_id=user.id, market=body.market, code=body.code, name=body.name,
                currency=body.currency, account=body.account, freq=body.freq,
                note=body.note)
    session.add(h)
    session.flush()
    if body.first_lot:
        fl = body.first_lot
        if fl.price <= 0:
            raise AppError(Codes.VALIDATION, "首笔买入的成交价必须大于 0", status=422)
        session.add(Lot(user_id=user.id, holding_id=h.id, trade_date=fl.trade_date.isoformat(),
                        direction="buy", shares=fl.shares, price=fl.price,
                        fee=fl.fee, note=fl.note))
    session.commit()
    session.refresh(h)
    return ok(holding_out(session, h))


@router.get("/{holding_id}")
def get_holding(holding_id: int, session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    return ok(holding_out(session, h))


@router.patch("/{holding_id}")
def update_holding(holding_id: int, body: HoldingUpdate,
                   session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(h, k, v)
    h.updated_at = now_str()
    session.add(h)
    session.commit()
    session.refresh(h)
    return ok(holding_out(session, h))


@router.delete("/{holding_id}")
def delete_holding(holding_id: int, session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    # 手动级联删除，顺序按外键依赖反着来：分红明细 → 分红 → 批次 → 持仓
    # （SQLite 默认外键不强制 ON DELETE 连锁，且 allocations.lot_id 是 SET NULL，
    #   整只持仓删时需要显式清干净，每步即时落库避免约束冲突）
    divs = session.exec(select(Dividend).where(Dividend.holding_id == h.id)).all()
    for d in divs:
        for a in session.exec(select(DividendAllocation)
                              .where(DividendAllocation.dividend_id == d.id)).all():
            session.delete(a)
        session.delete(d)
    for l in session.exec(select(Lot).where(Lot.holding_id == h.id)).all():
        session.delete(l)
    session.delete(h)
    session.commit()
    return ok({"deleted": holding_id})
