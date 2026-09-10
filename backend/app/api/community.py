"""公告与反馈用户端接口（docs/04 §十）。"""
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Announcement, Feedback, User
from ..schemas import FeedbackCreate
from ..utils.errors import ok
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["community"])


def feedback_out(f: Feedback) -> dict:
    return {"id": f.id, "content": f.content, "contact": f.contact,
            "status": f.status, "reply": f.reply, "created_at": f.created_at}


@router.get("/announcements")
def list_announcements(session: Session = Depends(get_session)):
    """已发布公告，按发布时间倒序（docs/04 §10.1）。

    注意：此接口【不需要登录】（无 get_current_user 依赖），
    供登录页/小程序首页在未登录状态也能看到系统公告。
    """
    items = session.exec(
        select(Announcement).where(Announcement.status == "published")
        .order_by(Announcement.published_at.desc())  # type: ignore
    ).all()
    return ok({"items": [{"id": a.id, "title": a.title, "content": a.content,
                          "published_at": a.published_at} for a in items]})


@router.post("/feedback")
def create_feedback(body: FeedbackCreate, session: Session = Depends(get_session),
                    user: User = Depends(get_current_user)):
    fb = Feedback(user_id=user.id, content=body.content, contact=body.contact)
    session.add(fb)
    session.commit()
    session.refresh(fb)
    return ok(feedback_out(fb))


@router.get("/feedback/me")
def my_feedback(session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    """我的反馈：含处理状态与回复（docs/04 §10.3）。"""
    items = session.exec(
        select(Feedback).where(Feedback.user_id == user.id)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())  # type: ignore
    ).all()
    return ok({"items": [feedback_out(f) for f in items]})
