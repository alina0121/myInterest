"""分红记录接口（docs/04 §四）——v0.3 改为实时计算。

v0.3 变更：
- 删除 Dividend / DividendAllocation 落表模型，分红数据完全实时计算
  （数据源：DividendSchedule 预案表 + Lot 交易批次）
- 分红状态由 pay_date 与今天比较动态决定（pay_date >= today 为 pending，否则 confirmed）
- 删除所有写操作路由（POST/PATCH/DELETE/CONFIRM/BATCH/AUTO-MATCH）
  ——手动分红统一走预案表，auto-match 改为纯查询不落表
"""
from datetime import date as _date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models import DividendSchedule, Holding, User
from ..services import dividend_service, fx_service
from ..utils.errors import not_found, ok
from .deps import get_current_user

router = APIRouter(prefix="/api/dividends", tags=["dividends"])


def get_dividend_by_schedule(session: Session, user_id: int,
                             schedule_id: int, holding_id: int) -> dict:
    """辅助函数：按预案 + 持仓实时计算单条分红明细（含 batches）。"""
    sch = session.get(DividendSchedule, schedule_id)
    if sch is None or sch.status != "published":
        raise not_found("预案不存在或未发布")
    holding = session.get(Holding, holding_id)
    if holding is None or holding.user_id != user_id:
        raise not_found()
    row = dividend_service.estimate_for_holding(session, holding, sch)
    if row is None:
        raise not_found("登记日无符合条件持仓股数")
    return row


def _out(session: Session, d: dict, holdings_map: dict[int, Holding],
         with_batches: bool = False,
         display_currency: str | None = None) -> dict:
    """把实时分红 dict 组装成前端出参（含币种转换）。"""
    h = holdings_map.get(d["holding_id"])
    net_cny = float(fx_service.to_cny(session, d["net_amount"], d["currency"], d["pay_date"]))
    data = {
        # 无落表 id，用 (schedule_id, holding_id) 合成稳定标识
        "id": f"{d['schedule_id']}-{d['holding_id']}",
        "holding_id": d["holding_id"], "schedule_id": d["schedule_id"],
        "holding_name": h.name if h else d.get("name", d["code"]),
        "code": d["code"], "market": d["market"],
        "ex_date": d["ex_date"], "record_date": d["record_date"],
        "pay_date": d["pay_date"],
        "dps": d["dps"], "shares": d["eligible_shares"],
        "gross_amount": d["gross_amount"], "tax": d["tax"],
        "net_amount": d["net_amount"],
        "net_cny": net_cny,
        "currency": d["currency"], "div_type": d["div_type"],
        "status": d["status"],
    }
    # 显示币种转换
    if display_currency and display_currency != "CNY":
        today = _date.today().isoformat()
        if display_currency == "ORIGINAL":
            data["net_display"] = float(d["net_amount"])
        else:
            data["net_display"] = float(
                fx_service.from_cny(session, net_cny, display_currency, today))
        data["display_currency"] = display_currency
    else:
        data["net_display"] = net_cny
        data["display_currency"] = "CNY"
    if with_batches and "batches" in d:
        data["batches"] = d["batches"]
    return data


@router.get("")
def list_dividends(year: int | None = None, market: str | None = None,
                   holding_id: int | None = None, status: str | None = None,
                   account: str | None = None, display_currency: str | None = None,
                   page: int = 1, page_size: int = 20,
                   expand: str | None = None,
                   session: Session = Depends(get_session),
                   user: User = Depends(get_current_user)):
    """实时计算用户全部分红列表（v0.3）。

    无落表，每次调用从 DividendSchedule + Lot 派生。
    """
    # 一次性拉持仓：market/account 过滤 + 拼 holding_name
    holdings = {h.id: h for h in
                session.exec(select(Holding).where(Holding.user_id == user.id)).all()}

    # 调实时计算服务（传 year=None/market=None 让它不过滤，自己在内存过滤更灵活）
    want_batches = expand is not None and "batches" in expand
    divs = dividend_service.list_user_dividends(
        session, user.id, year=None, market=None, want_batches=want_batches)

    # 过滤条件
    if holding_id is not None:
        divs = [d for d in divs if d["holding_id"] == holding_id]
    elif market is not None:
        ids = {hid for hid, h in holdings.items() if h.market == market}
        divs = [d for d in divs if d["holding_id"] in ids]
    if account and account != "__all__":
        ids = {hid for hid, h in holdings.items() if h.account == account}
        divs = [d for d in divs if d["holding_id"] in ids]
    if year is not None:
        divs = [d for d in divs
                if d.get("pay_date") and str(d["pay_date"]).startswith(str(year))]
    if status is not None:
        divs = [d for d in divs if d["status"] == status]

    # 内存分页
    total = len(divs)
    start = (page - 1) * page_size
    slice_ = divs[start:start + page_size]

    return ok({
        "items": [_out(session, d, holdings, want_batches, display_currency)
                  for d in slice_],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/detail")
def get_dividend_detail(schedule_id: int = Query(..., description="分红预案 ID"),
                        holding_id: int = Query(..., description="持仓 ID"),
                        display_currency: str | None = None,
                        session: Session = Depends(get_session),
                        user: User = Depends(get_current_user)):
    """单条分红明细（v0.3 改 query params，不再用落表 id）。"""
    d = get_dividend_by_schedule(session, user.id, schedule_id, holding_id)
    holdings = {h.id: h for h in
                session.exec(select(Holding).where(Holding.user_id == user.id)).all()}
    return ok(_out(session, d, holdings, with_batches=True,
                   display_currency=display_currency))
