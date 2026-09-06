"""用户设置接口（docs/04 §七）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import User, UserSetting
from ..schemas import SettingsUpdate
from ..utils.errors import ok
from ..utils.timeutil import now_str
from .deps import get_current_user

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create(session: Session, user_id: int) -> UserSetting:
    s = session.exec(select(UserSetting).where(UserSetting.user_id == user_id)).first()
    if s is None:
        s = UserSetting(user_id=user_id)
        session.add(s)
        session.commit()
        session.refresh(s)
    return s


def _settings_out(s: UserSetting) -> dict:
    return {"remind_before_days": s.remind_before_days,
            "remind_on_payday": bool(s.remind_on_payday),
            "auto_match_schedule": bool(s.auto_match_schedule),
            "push_enabled": bool(s.push_enabled),
            "wx_subscribe": bool(s.wx_subscribe),
            "updated_at": s.updated_at}


@router.get("")
def get_settings(session: Session = Depends(get_session),
                 user: User = Depends(get_current_user)):
    return ok(_settings_out(_get_or_create(session, user.id)))


@router.put("")
def update_settings(body: SettingsUpdate, session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    s = _get_or_create(session, user.id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    s.updated_at = now_str()
    session.add(s)
    session.commit()
    session.refresh(s)
    return ok(_settings_out(s))
