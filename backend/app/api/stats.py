"""统计接口（docs/04 §六）。

本文件是纯薄路由：只负责鉴权 + 转发，所有计算口径都在 services/stats_service.py。
改统计逻辑请去 service 层改，这里不要写业务。
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import User, UserSetting
from ..services import stats_service
from .deps import get_current_user
from ..utils.errors import ok
from .holdings import get_owned_holding

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
def summary(session: Session = Depends(get_session),
            user: User = Depends(get_current_user)):
    return ok(stats_service.summary(session, user.id))


@router.get("/enhanced-summary")
def enhanced_summary(session: Session = Depends(get_session),
                     user: User = Depends(get_current_user)):
    """新版看板汇总：含市值/盈亏/收益率等全部指标。"""
    return ok(stats_service.enhanced_summary(session, user.id))


@router.get("/dashboard-metrics")
def dashboard_metrics(session: Session = Depends(get_session),
                      user: User = Depends(get_current_user)):
    """获取指标注册表 + 用户已选指标列表。"""
    # 读取用户偏好
    setting = session.exec(
        select(UserSetting).where(UserSetting.user_id == user.id)
    ).first()
    selected = stats_service.get_default_metrics()
    if setting and setting.dashboard_metrics:
        try:
            selected = json.loads(setting.dashboard_metrics)
        except Exception:
            selected = stats_service.get_default_metrics()
    return ok({
        "registry": stats_service.get_dashboard_metrics(),
        "selected": selected,
        "max_select": 9,
        "min_select": 1,
    })


@router.put("/dashboard-metrics")
def save_dashboard_metrics(payload: dict,
                           session: Session = Depends(get_session),
                           user: User = Depends(get_current_user)):
    """保存用户已选指标列表。payload: {"selected": ["key1", "key2", ...]}"""
    keys = payload.get("selected", [])
    # 校验：只能选注册表中存在的 key，数量 1~9
    valid_keys = {m["key"] for m in stats_service.DASHBOARD_METRICS}
    keys = [k for k in keys if k in valid_keys][:9]
    if not keys:
        raise HTTPException(status_code=400, detail="至少选择 1 个指标")
    setting = session.exec(
        select(UserSetting).where(UserSetting.user_id == user.id)
    ).first()
    if setting is None:
        setting = UserSetting(user_id=user.id)
        session.add(setting)
    setting.dashboard_metrics = json.dumps(keys, ensure_ascii=False)
    session.commit()
    return ok({"selected": keys})


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
