"""持仓接口：CRUD + 计算字段（docs/04 §二）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Dividend, DividendAllocation, Holding, Lot, Security, User
from ..schemas import HoldingCreate, HoldingUpdate
from ..services import lots_service, security_service
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


def holding_out(session: Session, h: Holding, system_freq: str | None = None,
                latest_price: float | None = None) -> dict:
    return {
        "id": h.id, "market": h.market, "code": h.code, "name": h.name,
        "currency": h.currency, "account": h.account, "freq": h.freq,
        # 系统按分红历史推断的频率（securities.freq），供前端展示/「恢复系统推断」
        "system_freq": system_freq or "unknown",
        "note": h.note,
        # 最新价：优先用 securities.latest_price（爬虫实时更新），回落 holdings.current_price（创建时快照）
        "current_price": latest_price if latest_price is not None else h.current_price,
        "created_at": h.created_at,
        **lots_service.computed_summary(session, h),
    }


@router.get("")
def list_holdings(market: str | None = None, keyword: str | None = None,
                  freq: str | None = None,
                  account: str | None = None,
                  session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    """v8：去掉币种筛选，改为按 display_currency 转换（前端 store 控制）。
    account 支持 '__all__'/None 表示全部。
    """
    stmt = select(Holding).where(Holding.user_id == user.id)
    if market:
        stmt = stmt.where(Holding.market == market)
    if freq:
        stmt = stmt.where(Holding.freq == freq)
    # v8：账户筛选
    if account and account != "__all__":
        stmt = stmt.where(Holding.account == account)
    holdings = list(session.exec(stmt.order_by(Holding.id.desc())).all())  # type: ignore
    if keyword:
        kw = keyword.lower()
        holdings = [h for h in holdings
                    if kw in h.code.lower() or kw in h.name.lower()]
    sec_map = security_service.security_map(
        session, [(h.market, h.code) for h in holdings])
    items = []
    for h in holdings:
        sec = sec_map.get((h.market, h.code))
        latest_price = sec.latest_price if sec and sec.latest_price else h.current_price
        items.append(holding_out(
            session, h,
            system_freq=(sec.freq if sec else "unknown"),
            latest_price=latest_price))
    return ok({"items": items, "total": len(holdings)})


@router.post("")
def create_holding(body: HoldingCreate, session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    dup = session.exec(select(Holding).where(
        Holding.user_id == user.id, Holding.market == body.market,
        Holding.code == body.code)).first()
    if dup:
        raise AppError(Codes.HOLDING_EXISTS, "该标的持仓已存在，可直接添加批次", status=409)
    # 仅允许添加「已有分红数据」的标的：securities 表只在创建预案时 upsert
    sec = security_service.get_security(session, body.market, body.code)
    if sec is None:
        raise AppError(Codes.VALIDATION,
                       "该标的暂无分红数据，暂不支持添加；请先在后台补充分红预案（爬虫或手工录入）",
                       status=422)
    h = Holding(user_id=user.id, market=body.market, code=body.code, name=body.name,
                currency=body.currency, account=body.account, freq=body.freq,
                note=body.note, current_price=sec.latest_price)
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
    return ok(holding_out(session, h, sec.freq))


@router.get("/{holding_id}")
def get_holding(holding_id: int, session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    sec = security_service.get_security(session, h.market, h.code)
    latest_price = sec.latest_price if sec and sec.latest_price else h.current_price
    return ok(holding_out(session, h,
                          system_freq=(sec.freq if sec else "unknown"),
                          latest_price=latest_price))


@router.patch("/{holding_id}")
def update_holding(holding_id: int, body: HoldingUpdate,
                   session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    changes = body.model_dump(exclude_unset=True)
    # freq="auto"：放弃用户手动值，恢复 securities 表按分红历史推断的系统频率
    if changes.get("freq") == "auto":
        sec = security_service.get_security(session, h.market, h.code)
        changes["freq"] = sec.freq if sec else "unknown"
    for k, v in changes.items():
        setattr(h, k, v)
    h.updated_at = now_str()
    session.add(h)
    session.commit()
    session.refresh(h)
    sec = security_service.get_security(session, h.market, h.code)
    return ok(holding_out(session, h, sec.freq if sec else "unknown"))


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
