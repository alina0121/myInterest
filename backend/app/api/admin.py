"""运营后台接口（docs/04 §十一、docs/06）。

权限模型（docs/06 §2）：
- admin：看板、预案审核、公告、反馈、用户查询/重置密码
- super_admin：另可 封禁/解封、汇率/税率维护
- 红线：对用户业务数据只读；所有写操作落 admin_operation_logs
"""
import json
import secrets
import string

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlmodel import Session, func, select

from ..database import get_session
from ..models import (AdminOperationLog, Announcement, Dividend, DividendSchedule,
                      ExchangeRate, Feedback, Holding, Lot, TaxRule, User)
from ..schemas import (AnnouncementCreate, AnnouncementUpdate, ConfigUpdateIn,
                       FeedbackHandleIn, RateManualIn, ScheduleAdminCreate,
                       ScheduleBatchApproveIn, ScheduleRejectIn, TaxRuleUpdate)
from ..services import (config_service, crawler_service, fx_service, lots_service,
                        schedule_service)
from ..utils.errors import AppError, Codes, not_found, ok
from ..utils.security import hash_password
from ..utils.timeutil import add_days, days_ago_iso, now_str, today_str
from .deps import get_admin_user, require_super_admin
from .holdings import holding_out

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------- 通用小工具 ----------
def _log(session: Session, admin: User, request: Request, action: str,
         target_type: str, target_id: int | None = None, detail=None) -> None:
    """写操作留痕（docs/06 §2 红线）。由调用方负责随业务一并 commit。"""
    session.add(AdminOperationLog(
        admin_id=admin.id, action=action, target_type=target_type, target_id=target_id,
        detail=json.dumps(detail, ensure_ascii=False) if detail else None,
        ip=request.client.host if request.client else None,
    ))


def _mask_email(email: str | None) -> str | None:
    """列表默认脱敏：vi****@163.com（docs/06 §3.3）。"""
    if not email:
        return None
    if "@" not in email:
        return email[:2] + "****"
    local, domain = email.split("@", 1)
    return f"{local[:2]}****@{domain}"


def _can_operate(operator: User, target: User) -> bool:
    """admin 只能操作普通用户；super_admin 可操作 admin；均不可操作 super_admin。"""
    if target.role == "user":
        return True
    return operator.role == "super_admin" and target.role == "admin"


def _gen_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------- 11.1 看板 ----------
@router.get("/stats/overview")
def stats_overview(session: Session = Depends(get_session),
                   admin: User = Depends(get_admin_user)):
    today = today_str()
    users = session.exec(select(User)).all()
    user_total = len(users)
    new_users_7d = sum(1 for u in users if (u.created_at or "")[:10] >= add_days(today, -6))
    dau = sum(1 for u in users if (u.last_login_at or "")[:10] == today)
    mau = sum(1 for u in users if (u.last_login_at or "")[:10] >= add_days(today, -29))

    def _count(model) -> int:
        return session.exec(select(func.count()).select_from(model)).one()

    def _sch_count(status: str) -> int:
        return session.exec(select(func.count()).select_from(DividendSchedule)
                            .where(DividendSchedule.status == status)).one()

    crawl_rows = [s for s in session.exec(select(DividendSchedule)
                  .where(DividendSchedule.source == "crawler")).all()
                  if s.created_at[:10] == today]
    crawl_today = {
        "fetched": len(crawl_rows),
        "published": sum(1 for s in crawl_rows if s.status == "published"),
        "need_manual": sum(1 for s in crawl_rows
                           if s.status == "pending" and s.confidence < 0.7),
    }

    days = [days_ago_iso(d) for d in range(29, -1, -1)]
    new_users_30d = [sum(1 for u in users if (u.created_at or "")[:10] == d) for d in days]
    dau_30d = [sum(1 for u in users if (u.last_login_at or "")[:10] == d) for d in days]

    return ok({
        "user_total": user_total, "new_users_7d": new_users_7d,
        "dau": dau, "mau": mau,
        "holding_total": _count(Holding), "lot_total": _count(Lot),
        "dividend_total": _count(Dividend),
        "schedule_pending": _sch_count("pending"),
        "schedule_published_total": _sch_count("published"),
        "schedule_rejected_total": _sch_count("rejected"),
        "crawl_today": crawl_today,
        "new_users_30d": new_users_30d, "dau_30d": dau_30d,
    })


# ---------- 11.2 用户管理 ----------
def _user_row(session: Session, u: User) -> dict:
    holding_count = session.exec(select(func.count()).select_from(Holding)
                                 .where(Holding.user_id == u.id)).one()
    divs = session.exec(select(Dividend).where(Dividend.user_id == u.id)).all()
    rate_cache: dict[tuple[str, str], float] = {}
    total_cny = 0.0
    for d in divs:
        key = (d.currency, d.pay_date[:10])
        if key not in rate_cache:
            rate_cache[key] = float(fx_service.get_rate_cny(session, d.currency, key[1]))
        total_cny += d.net_amount * rate_cache[key]
    return {
        "id": u.id, "username": u.username, "email": _mask_email(u.email),
        "nickname": u.nickname, "holding_count": holding_count,
        "dividend_count": len(divs), "total_dividend_cny": round(total_cny, 2),
        "created_at": u.created_at, "last_login_at": u.last_login_at,
        "role": u.role, "status": u.status,
    }


@router.get("/users")
def admin_list_users(keyword: str | None = None, status: str | None = None,
                     role: str | None = None, page: int = 1, page_size: int = 20,
                     session: Session = Depends(get_session),
                     admin: User = Depends(get_admin_user)):
    users = list(session.exec(select(User).order_by(User.id)).all())  # type: ignore
    if keyword:
        kw = keyword.lower()
        users = [u for u in users
                 if kw in u.username.lower()
                 or (u.email and kw in u.email.lower())
                 or str(u.id) == keyword]
    if status:
        users = [u for u in users if u.status == status]
    if role:
        users = [u for u in users if u.role == role]
    total = len(users)
    start = (page - 1) * page_size
    return ok({"items": [_user_row(session, u) for u in users[start:start + page_size]],
               "total": total, "page": page, "page_size": page_size})


@router.get("/users/{user_id}/data")
def admin_user_data(user_id: int, session: Session = Depends(get_session),
                    admin: User = Depends(get_admin_user)):
    """该用户持仓/分红只读汇总（客服排查，docs/06 §3.3）。"""
    target = session.get(User, user_id)
    if target is None:
        raise not_found()
    holdings = session.exec(select(Holding).where(Holding.user_id == user_id)).all()
    divs = session.exec(select(Dividend).where(Dividend.user_id == user_id)
                        .order_by(Dividend.pay_date.desc())).all()  # type: ignore
    return ok({
        "user": {
            "id": target.id, "username": target.username,
            "email": target.email if admin.role == "super_admin"
            else _mask_email(target.email),
            "nickname": target.nickname, "role": target.role, "status": target.status,
            "created_at": target.created_at, "last_login_at": target.last_login_at,
        },
        "holdings": [holding_out(session, h) for h in holdings],
        "dividends": [{
            "id": d.id, "holding_id": d.holding_id, "ex_date": d.ex_date,
            "pay_date": d.pay_date, "dps": d.dps, "gross_amount": d.gross_amount,
            "tax": d.tax, "net_amount": d.net_amount, "currency": d.currency,
            "status": d.status, "source": d.source,
        } for d in divs],
    })


@router.post("/users/{user_id}/ban")
def ban_user(user_id: int, request: Request,
             session: Session = Depends(get_session),
             admin: User = Depends(require_super_admin)):
    target = session.get(User, user_id)
    if target is None:
        raise not_found()
    if target.id == admin.id:
        raise AppError(Codes.VALIDATION, "不能封禁自己", status=422)
    if not _can_operate(admin, target):
        raise AppError(Codes.FORBIDDEN, "不可操作管理员账号", status=403)
    target.status = "banned"
    _log(session, admin, request, "user.ban", "user", target.id,
         {"username": target.username})
    session.commit()
    return ok({"id": target.id, "status": "banned"})


@router.post("/users/{user_id}/unban")
def unban_user(user_id: int, request: Request,
               session: Session = Depends(get_session),
               admin: User = Depends(require_super_admin)):
    target = session.get(User, user_id)
    if target is None:
        raise not_found()
    if not _can_operate(admin, target):
        raise AppError(Codes.FORBIDDEN, "不可操作管理员账号", status=403)
    target.status = "active"
    _log(session, admin, request, "user.unban", "user", target.id,
         {"username": target.username})
    session.commit()
    return ok({"id": target.id, "status": "active"})


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, request: Request,
                   session: Session = Depends(get_session),
                   admin: User = Depends(get_admin_user)):
    target = session.get(User, user_id)
    if target is None:
        raise not_found()
    if not _can_operate(admin, target):
        raise AppError(Codes.FORBIDDEN, "不可操作管理员账号", status=403)
    temp = _gen_temp_password()
    target.password_hash = hash_password(temp)  # 临时密码不落日志
    _log(session, admin, request, "user.reset_password", "user", target.id,
         {"username": target.username})
    session.commit()
    return ok({"temp_password": temp})


# ---------- 11.3 预案审核 ----------
def schedule_out(session: Session, s: DividendSchedule) -> dict:
    submitter = session.get(User, s.submitted_by) if s.submitted_by else None
    reviewer = session.get(User, s.reviewed_by) if s.reviewed_by else None
    return {
        "id": s.id, "market": s.market, "code": s.code, "name": s.name,
        "ex_date": s.ex_date, "record_date": s.record_date, "pay_date": s.pay_date,
        "dps": s.dps, "currency": s.currency, "div_type": s.div_type,
        "source": s.source, "confidence": s.confidence, "status": s.status,
        "submitter_name": (submitter.nickname or submitter.username) if submitter else None,
        "reviewer_name": (reviewer.nickname or reviewer.username) if reviewer else None,
        "reviewed_at": s.reviewed_at, "reject_reason": s.reject_reason,
        "raw_title": s.raw_title, "created_at": s.created_at,
    }


@router.get("/schedules")
def admin_list_schedules(status: str | None = None, market: str | None = None,
                         keyword: str | None = None,
                         min_confidence: float | None = None,
                         max_confidence: float | None = None,
                         page: int = 1, page_size: int = 20,
                         session: Session = Depends(get_session),
                         admin: User = Depends(get_admin_user)):
    stmt = select(DividendSchedule)
    if status:
        stmt = stmt.where(DividendSchedule.status == status)
    if market:
        stmt = stmt.where(DividendSchedule.market == market)
    rows = list(session.exec(
        stmt.order_by(DividendSchedule.created_at.desc(), DividendSchedule.id.desc())  # type: ignore
    ).all())
    if keyword:
        kw = keyword.lower()
        rows = [s for s in rows if kw in s.code.lower() or kw in s.name.lower()]
    if min_confidence is not None:
        rows = [s for s in rows if s.confidence >= min_confidence]
    if max_confidence is not None:
        rows = [s for s in rows if s.confidence <= max_confidence]

    counts = {"pending": 0, "published": 0, "rejected": 0}
    for s in session.exec(select(DividendSchedule)).all():
        counts[s.status] = counts.get(s.status, 0) + 1

    total = len(rows)
    start = (page - 1) * page_size
    return ok({"items": [schedule_out(session, s) for s in rows[start:start + page_size]],
               "total": total, "page": page, "page_size": page_size,
               "status_counts": counts})


@router.post("/schedules")
def admin_create_schedule(body: ScheduleAdminCreate, request: Request,
                          session: Session = Depends(get_session),
                          admin: User = Depends(get_admin_user)):
    s = DividendSchedule(
        market=body.market, code=body.code, name=body.name,
        ex_date=body.ex_date.isoformat() if body.ex_date else None,
        record_date=body.record_date.isoformat() if body.record_date else None,
        pay_date=body.pay_date.isoformat() if body.pay_date else None,
        dps=body.dps, currency=body.currency, div_type=body.div_type,
        source="manual", confidence=1.0, status="pending", raw_title=body.raw_title,
    )
    session.add(s)
    session.flush()
    _log(session, admin, request, "schedule.create", "schedule", s.id,
         {"market": s.market, "code": s.code, "ex_date": s.ex_date, "dps": s.dps})
    session.commit()
    session.refresh(s)
    return ok(schedule_out(session, s))


@router.post("/schedules/{sid}/approve")
def approve_schedule(sid: int, background_tasks: BackgroundTasks, request: Request,
                     session: Session = Depends(get_session),
                     admin: User = Depends(get_admin_user)):
    s = session.get(DividendSchedule, sid)
    if s is None:
        raise not_found()
    if s.status == "published":
        raise AppError(Codes.VALIDATION, "该预案已发布", status=422)
    if not s.ex_date or not s.dps:
        raise AppError(Codes.VALIDATION, "缺少除权日或每股分红，无法发布", status=422)
    # 发布前防重：同一 (市场,代码,除权日) 只能有一条 published
    # （DB 层还有部分唯一索引 uq_sch_published 兜底）
    dup = session.exec(select(DividendSchedule).where(
        DividendSchedule.market == s.market, DividendSchedule.code == s.code,
        DividendSchedule.ex_date == s.ex_date,
        DividendSchedule.status == "published",
        DividendSchedule.id != s.id)).first()
    if dup:
        raise AppError(Codes.SCHEDULE_DUPLICATE, "该标的除权日预案已存在", status=409)
    s.status = "published"
    s.reviewed_by = admin.id
    s.reviewed_at = now_str()
    _log(session, admin, request, "schedule.approve", "schedule", s.id,
         {"market": s.market, "code": s.code, "ex_date": s.ex_date, "dps": s.dps})
    session.commit()
    session.refresh(s)
    # 发布后异步触发全体相关用户 auto-match（docs/06 §3.2）
    background_tasks.add_task(schedule_service.auto_match_all_background)
    return ok(schedule_out(session, s))


@router.post("/schedules/batch-approve")
def batch_approve_schedules(body: ScheduleBatchApproveIn,
                            background_tasks: BackgroundTasks, request: Request,
                            session: Session = Depends(get_session),
                            admin: User = Depends(get_admin_user)):
    """批量审核预案：一次发布或驳回多条 pending 预案。

    action="publish"：发布（校验同单条逻辑，任一失败则整体回滚）
    action="reject"：驳回（需提供 reason）
    """
    handled = []
    for sid in body.ids:
        s = session.get(DividendSchedule, sid)
        if s is None:
            raise not_found()
        if body.action == "publish":
            if s.status == "published":
                raise AppError(Codes.VALIDATION, f"预案 #{sid} 已发布", status=422)
            if not s.ex_date or not s.dps:
                raise AppError(Codes.VALIDATION,
                               f"预案 #{sid} 缺少除权日或每股分红", status=422)
            dup = session.exec(select(DividendSchedule).where(
                DividendSchedule.market == s.market, DividendSchedule.code == s.code,
                DividendSchedule.ex_date == s.ex_date,
                DividendSchedule.status == "published",
                DividendSchedule.id != s.id)).first()
            if dup:
                raise AppError(Codes.SCHEDULE_DUPLICATE,
                               f"预案 #{sid} 除权日已存在发布记录", status=409)
            s.status = "published"
            _log(session, admin, request, "schedule.batch_approve", "schedule", s.id,
                 {"action": "publish", "market": s.market, "code": s.code})
        else:  # reject
            if s.status != "pending":
                raise AppError(Codes.VALIDATION, f"预案 #{sid} 非待审核状态", status=422)
            if not body.reason:
                raise AppError(Codes.VALIDATION, "驳回需提供 reason", status=422)
            s.status = "rejected"
            s.reject_reason = body.reason
            _log(session, admin, request, "schedule.batch_approve", "schedule", s.id,
                 {"action": "reject", "reason": body.reason})
        s.reviewed_by = admin.id
        s.reviewed_at = now_str()
        session.add(s)
        handled.append(s)
    session.commit()
    if body.action == "publish":
        background_tasks.add_task(schedule_service.auto_match_all_background)
    return ok({
        "action": body.action,
        "handled": len(handled),
        "items": [schedule_out(session, s) for s in handled],
    })


@router.post("/schedules/{sid}/reject")
def reject_schedule(sid: int, body: ScheduleRejectIn, request: Request,
                    session: Session = Depends(get_session),
                    admin: User = Depends(get_admin_user)):
    s = session.get(DividendSchedule, sid)
    if s is None:
        raise not_found()
    if s.status != "pending":
        raise AppError(Codes.VALIDATION, "仅待审核预案可驳回", status=422)
    s.status = "rejected"
    s.reject_reason = body.reason
    s.reviewed_by = admin.id
    s.reviewed_at = now_str()
    _log(session, admin, request, "schedule.reject", "schedule", s.id,
         {"reason": body.reason})
    session.commit()
    session.refresh(s)
    return ok(schedule_out(session, s))


@router.post("/schedules/crawl")
def crawl_schedules(request: Request, session: Session = Depends(get_session),
                    admin: User = Depends(get_admin_user)):
    result = crawler_service.run_crawl(session)
    _log(session, admin, request, "schedule.crawl", "schedule", None, result)
    session.commit()
    return ok(result)


# ---------- 11.4 汇率与税率 ----------
@router.get("/rates")
def admin_list_rates(base: str | None = None, start: str | None = None,
                     end: str | None = None, page: int = 1, page_size: int = 50,
                     session: Session = Depends(get_session),
                     admin: User = Depends(get_admin_user)):
    stmt = select(ExchangeRate)
    if base:
        stmt = stmt.where(ExchangeRate.base == base)
    rows = list(session.exec(
        stmt.order_by(ExchangeRate.rate_date.desc(), ExchangeRate.id.desc())  # type: ignore
    ).all())
    if start:
        rows = [r for r in rows if r.rate_date >= start]
    if end:
        rows = [r for r in rows if r.rate_date <= end]
    total = len(rows)
    start_idx = (page - 1) * page_size
    return ok({"items": [{
        "id": r.id, "base": r.base, "quote": r.quote, "rate": r.rate,
        "rate_date": r.rate_date, "source": r.source, "created_at": r.created_at,
    } for r in rows[start_idx:start_idx + page_size]],
        "total": total, "page": page, "page_size": page_size})


def _upsert_rate(session: Session, base: str, rate: float, rate_date: str,
                 source: str) -> ExchangeRate:
    row = session.exec(select(ExchangeRate).where(
        ExchangeRate.base == base, ExchangeRate.quote == "CNY",
        ExchangeRate.rate_date == rate_date)).first()
    if row:
        row.rate = rate
        row.source = source
    else:
        row = ExchangeRate(base=base, quote="CNY", rate=rate,
                           rate_date=rate_date, source=source)
        session.add(row)
    return row


@router.post("/rates")
def admin_create_rate(body: RateManualIn, request: Request,
                      session: Session = Depends(get_session),
                      admin: User = Depends(require_super_admin)):
    row = _upsert_rate(session, body.base, body.rate, body.rate_date.isoformat(), "manual")
    _log(session, admin, request, "rate.update", "rate", None,
         {"base": body.base, "rate": body.rate, "rate_date": body.rate_date.isoformat()})
    session.commit()
    session.refresh(row)
    return ok({"id": row.id, "base": row.base, "rate": row.rate,
               "rate_date": row.rate_date, "source": row.source})


@router.post("/rates/refresh")
def refresh_rates(request: Request, session: Session = Depends(get_session),
                  admin: User = Depends(require_super_admin)):
    """拉取最新汇率（frankfurter 央行中间价口径，docs/06 §3.4）。"""
    updated = []
    for base in ("USD", "HKD"):
        rate = fx_service.fetch_latest_rate(base)
        if rate is not None:
            _upsert_rate(session, base, rate, today_str(), "frankfurter")
            updated.append({"base": base, "rate": rate})
    _log(session, admin, request, "rate.refresh", "rate", None, {"updated": updated})
    session.commit()
    return ok({"updated": updated})


def _tax_rule_out(r: TaxRule) -> dict:
    return {"id": r.id, "market": r.market, "condition": r.condition, "rate": r.rate,
            "hold_min_days": r.hold_min_days, "hold_max_days": r.hold_max_days,
            "description": r.description, "enabled": r.enabled, "updated_at": r.updated_at}


@router.get("/tax-rules")
def admin_list_tax_rules(session: Session = Depends(get_session),
                         admin: User = Depends(get_admin_user)):
    rules = session.exec(select(TaxRule).order_by(TaxRule.market, TaxRule.id)).all()  # type: ignore
    return ok({"items": [_tax_rule_out(r) for r in rules]})


@router.put("/tax-rules/{rule_id}")
def admin_update_tax_rule(rule_id: int, body: TaxRuleUpdate, request: Request,
                          session: Session = Depends(get_session),
                          admin: User = Depends(require_super_admin)):
    rule = session.get(TaxRule, rule_id)
    if rule is None:
        raise not_found()
    before = {"rate": rule.rate, "enabled": rule.enabled}
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(rule, k, v)
    rule.updated_at = now_str()
    _log(session, admin, request, "tax_rule.update", "tax_rule", rule.id,
         {"before": before, "after": {"rate": rule.rate, "enabled": rule.enabled}})
    session.commit()
    session.refresh(rule)
    out = _tax_rule_out(rule)
    out["note"] = "税率修改仅对新分红计算生效，不追溯历史分红"
    return ok(out)


# ---------- 11.4 系统配置（key-value，元数据驱动） ----------
@router.get("/config")
def admin_list_config(session: Session = Depends(get_session),
                      admin: User = Depends(get_admin_user)):
    """系统配置：admin 可读；敏感值脱敏（只回传 has_value/mask，不回传原文）。"""
    return ok({"groups": config_service.admin_view()})


@router.put("/config")
def admin_update_config(body: ConfigUpdateIn, request: Request,
                        session: Session = Depends(get_session),
                        admin: User = Depends(require_super_admin)):
    """批量保存系统配置：仅 super_admin；敏感项留空=不修改。即时生效并落操作日志。"""
    changed = config_service.set_values(session, body.items, admin_id=admin.id)
    # 日志只记配置键，不记值（避免密钥等敏感值落日志库）
    _log(session, admin, request, "config.update", "system_config", None,
         {"keys": changed})
    session.commit()
    return ok({"changed": changed, "groups": config_service.admin_view()})


@router.delete("/config/{key}")
def admin_reset_config(key: str, request: Request,
                       session: Session = Depends(get_session),
                       admin: User = Depends(require_super_admin)):
    """单项重置：删除 DB 覆盖，回退到环境变量/内置默认。"""
    config_service.reset_value(session, key, admin_id=admin.id)
    _log(session, admin, request, "config.reset", "system_config", None, {"key": key})
    session.commit()
    return ok({"groups": config_service.admin_view()})


# ---------- 11.5 公告 ----------
def _announcement_out(a: Announcement) -> dict:
    return {"id": a.id, "title": a.title, "content": a.content,
            "status": a.status, "published_at": a.published_at,
            "created_by": a.created_by, "created_at": a.created_at}


@router.post("/announcements")
def create_announcement(body: AnnouncementCreate, request: Request,
                        session: Session = Depends(get_session),
                        admin: User = Depends(get_admin_user)):
    a = Announcement(title=body.title, content=body.content.strip(),
                     created_by=admin.id,
                     status="published" if body.publish else "draft",
                     published_at=now_str() if body.publish else None)
    session.add(a)
    session.flush()
    _log(session, admin, request, "announcement.create", "announcement", a.id,
         {"title": a.title, "status": a.status})
    session.commit()
    session.refresh(a)
    return ok(_announcement_out(a))


def content_stripped(body: AnnouncementCreate) -> str:
    return body.content.strip()


@router.patch("/announcements/{aid}")
def update_announcement(aid: int, body: AnnouncementUpdate, request: Request,
                        session: Session = Depends(get_session),
                        admin: User = Depends(get_admin_user)):
    a = session.get(Announcement, aid)
    if a is None:
        raise not_found()
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(a, k, v)
    if a.status == "published" and not a.published_at:
        a.published_at = now_str()
    _log(session, admin, request, "announcement.update", "announcement", a.id,
         {"status": a.status, "fields": list(changes.keys())})
    session.commit()
    session.refresh(a)
    return ok(_announcement_out(a))


# ---------- 11.6 反馈 ----------
def _feedback_admin_out(session: Session, f: Feedback) -> dict:
    u = session.get(User, f.user_id)
    handler = session.get(User, f.handled_by) if f.handled_by else None
    return {"id": f.id, "user_id": f.user_id,
            "username": u.username if u else None,
            "content": f.content, "contact": f.contact, "status": f.status,
            "reply": f.reply,
            "handled_by_name": (handler.nickname or handler.username) if handler else None,
            "created_at": f.created_at}


@router.get("/feedback")
def admin_list_feedback(status: str | None = None, page: int = 1, page_size: int = 20,
                        session: Session = Depends(get_session),
                        admin: User = Depends(get_admin_user)):
    stmt = select(Feedback)
    if status:
        stmt = stmt.where(Feedback.status == status)
    rows = list(session.exec(
        stmt.order_by(Feedback.created_at.desc(), Feedback.id.desc())).all())  # type: ignore
    total = len(rows)
    start = (page - 1) * page_size
    return ok({"items": [_feedback_admin_out(session, f) for f in rows[start:start + page_size]],
               "total": total, "page": page, "page_size": page_size})


@router.patch("/feedback/{fid}")
def handle_feedback(fid: int, body: FeedbackHandleIn, request: Request,
                    session: Session = Depends(get_session),
                    admin: User = Depends(get_admin_user)):
    f = session.get(Feedback, fid)
    if f is None:
        raise not_found()
    f.status = body.status
    if body.reply is not None:
        f.reply = body.reply
    f.handled_by = admin.id
    _log(session, admin, request, "feedback.handle", "feedback", f.id,
         {"status": f.status, "reply": f.reply})
    session.commit()
    session.refresh(f)
    return ok(_feedback_admin_out(session, f))


# ---------- 11.7 操作日志（只读）----------
@router.get("/logs")
def admin_list_logs(admin_id: int | None = None, page: int = 1, page_size: int = 20,
                    session: Session = Depends(get_session),
                    admin: User = Depends(get_admin_user)):
    stmt = select(AdminOperationLog)
    if admin_id is not None:
        stmt = stmt.where(AdminOperationLog.admin_id == admin_id)
    rows = list(session.exec(
        stmt.order_by(AdminOperationLog.created_at.desc(),
                      AdminOperationLog.id.desc())).all())  # type: ignore
    total = len(rows)
    start = (page - 1) * page_size
    items = []
    for lg in rows[start:start + page_size]:
        try:
            detail = json.loads(lg.detail) if lg.detail else None
        except (TypeError, ValueError):
            detail = lg.detail
        operator = session.get(User, lg.admin_id)
        items.append({
            "id": lg.id, "admin_id": lg.admin_id,
            "admin_name": (operator.nickname or operator.username) if operator else None,
            "action": lg.action, "target_type": lg.target_type,
            "target_id": lg.target_id, "detail": detail, "ip": lg.ip,
            "created_at": lg.created_at,
        })
    return ok({"items": items, "total": total, "page": page, "page_size": page_size})
