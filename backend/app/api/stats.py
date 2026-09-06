"""统计接口（docs/04 §六）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..database import get_session
from ..models import User
from ..services import stats_service
from .deps import get_current_user
from ..utils.errors import ok
from .holdings import get_owned_holding

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
def summary(session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    return ok(stats_service.summary(session, user.id))


@router.get("/monthly-trend")
def monthly_trend(range: str = "12m", session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    return ok(stats_service.monthly_trend(session, user.id, range))


@router.get("/by-market")
def by_market(session: Session = Depends(get_session),
              user: User = Depends(get_current_user)):
    return ok(stats_service.by_market(session, user.id))


@router.get("/forecast")
def forecast(session: Session = Depends(get_session),
             user: User = Depends(get_current_user)):
    return ok(stats_service.forecast(session, user.id))


@router.get("/top-holdings")
def top_holdings(limit: int = 10, session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    return ok(stats_service.top_holdings(session, user.id, limit))


@router.get("/yield-ranking")
def yield_ranking(session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    return ok(stats_service.yield_ranking(session, user.id))


@router.get("/holdings/{holding_id}")
def holding_stats(holding_id: int, session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    h = get_owned_holding(session, user, holding_id)
    return ok(stats_service.holding_stats(session, h))
