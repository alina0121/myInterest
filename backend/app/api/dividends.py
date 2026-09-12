"""分红记录接口：CRUD + 确认（docs/04 §四）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Dividend, DividendAllocation, Holding, User
from ..schemas import ConfirmIn, DividendBatchIn, DividendCreate, DividendUpdate
from ..services import dividend_service, fx_service, schedule_service
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
                 with_allocations: bool = False,
                 display_currency: str | None = None) -> dict:
    """v8：新增 display_currency 参数，按显示币种转换金额。
    - None/'CNY'：net_cny 用派息日汇率折 CNY（历史归账）
    - 'USD'/'HKD'：net_display 用今天汇率从 CNY 转出
    - 'ORIGINAL'：net_display 保留原币种金额
    """
    net_cny = float(fx_service.to_cny(session, d.net_amount, d.currency, d.pay_date))
    data = {
        "id": d.id, "holding_id": d.holding_id, "schedule_id": d.schedule_id,
        "holding_name": holding.name, "code": holding.code, "market": holding.market,
        "ex_date": d.ex_date, "record_date": d.record_date, "pay_date": d.pay_date,
        "dps": d.dps, "shares": d.eligible_shares,
        "gross_amount": d.gross_amount, "tax": d.tax, "net_amount": d.net_amount,
        "net_cny": net_cny,
        "currency": d.currency, "div_type": d.div_type, "source": d.source,
        "status": d.status, "tax_overridden": bool(d.tax_overridden), "note": d.note,
    }
    # v8：按显示币种转换
    if display_currency and display_currency != "CNY":
        if display_currency == "ORIGINAL":
            data["net_display"] = float(d.net_amount)
        else:
            data["net_display"] = float(
                fx_service.from_cny(session, net_cny, display_currency,
                                    __import__('datetime').date.today().isoformat())
            )
        data["display_currency"] = display_currency
    else:
        data["net_display"] = net_cny
        data["display_currency"] = "CNY"
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
                   account: str | None = None, display_currency: str | None = None,
                   page: int = 1, page_size: int = 20, expand: str | None = None,
                   session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    # 先把该用户所有持仓捞成 id→Holding 映射：市场/账户筛选、出参拼名称都要用，
    # 避免逐条分红再查一次持仓（N+1 查询）
    holdings = {h.id: h for h in
                session.exec(select(Holding).where(Holding.user_id == user.id)).all()}
    # 列表默认按派息日倒序：最近到账的在最前面
    divs = list(session.exec(
        select(Dividend).where(Dividend.user_id == user.id)
        .order_by(Dividend.pay_date.desc(), Dividend.id.desc())  # type: ignore
    ).all())

    # 以下为可选过滤条件（可叠加），在内存里收窄
    if holding_id is not None:
        divs = [d for d in divs if d.holding_id == holding_id]
    elif market is not None:
        ids = {hid for hid, h in holdings.items() if h.market == market}
        divs = [d for d in divs if d.holding_id in ids]
    # v8：账户筛选（通过 holding.account 反查）
    if account and account != "__all__":
        ids = {hid for hid, h in holdings.items() if h.account == account}
        divs = [d for d in divs if d.holding_id in ids]
    if year is not None:
        divs = [d for d in divs if d.pay_date[:4] == str(year)]  # 按派息日年份归属
    if status is not None:
        divs = [d for d in divs if d.status == status]

    # 内存分页（个人分红条数有限，不值得 SQL 分页）
    total = len(divs)
    start = (page - 1) * page_size
    slice_ = divs[start:start + page_size]
    # expand=allocations 时列表也带批次明细，默认不带以减小响应体
    want_alloc = expand is not None and "allocations" in expand
    return ok({
        "items": [dividend_out(session, d, holdings[d.holding_id], want_alloc,
                                display_currency)
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


@router.post("/batch")
def create_dividends_batch(body: DividendBatchIn,
                           session: Session = Depends(get_session),
                           user: User = Depends(get_current_user)):
    """批量录入分红：支持一次提交多只持仓的多笔分红。

    每条单独调用 create_dividend 自动生成批次归属明细与税费估算。
    任意一条失败则整体回滚。
    """
    results = []
    for item in body.dividends:
        h = get_owned_holding(session, user, item.holding_id)
        d = dividend_service.create_dividend(
            session, user.id, h,
            ex_date=item.ex_date.isoformat(),
            pay_date=item.pay_date.isoformat(),
            dps=item.dps,
            record_date=item.record_date.isoformat() if item.record_date else None,
            tax=item.tax, div_type=item.div_type,
            status=item.status, note=item.note,
        )
        results.append(dividend_out(session, d, h, True))
    return ok({"created": len(results), "dividends": results})


@router.post("/auto-match")
def auto_match(session: Session = Depends(get_session),
               user: User = Depends(get_current_user)):
    """预告自动匹配：扫描已发布预案为本用户生成 pending 分红，幂等（docs/04 §4.6）。"""
    return ok(schedule_service.auto_match(session, user_id=user.id))


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
    # pending → confirmed：预告分红真实到账后确认，此后才计入「已实现」统计
    d.status = "confirmed"
    if body.actual_net is not None:
        # 用户按券商实际到账金额回填：以实际到账为准，倒推真实税费
        d.net_amount = round(body.actual_net, 2)
        d.tax = round(d.gross_amount - body.actual_net, 2)
        d.tax_overridden = 1
    d.updated_at = now_str()
    session.add(d)
    session.commit()
    session.refresh(d)
    h = session.get(Holding, d.holding_id)
    return ok(dividend_out(session, d, h, True))
