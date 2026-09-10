"""系统级接口：汇率查询（docs/04 §七 7.3）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import ExchangeRate, User
from ..services import fx_service
from ..utils.timeutil import today_str
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/rates")
def get_rates(date: str | None = None,
              session: Session = Depends(get_session),
              user: User = Depends(get_current_user)):
    day = date or today_str()
    rates = {}
    sources = []  # 每个币种汇率的实际来源：frankfurter/manual/fallback，便于前端标注
    for base in ("USD", "HKD"):
        rate = fx_service.get_rate_cny(session, base, day)  # 触发 DB→在线→兜底 四级降级
        rates[base] = float(rate)
        row = session.exec(
            select(ExchangeRate).where(ExchangeRate.base == base,
                                       ExchangeRate.rate_date <= day)
            .order_by(ExchangeRate.rate_date.desc())  # type: ignore
        ).first()
        sources.append(row.source if row else "fallback")
    return {"code": 0, "msg": "ok", "data": {"date": day, "base": "CNY",
                                             "rates": rates, "sources": sources}}
