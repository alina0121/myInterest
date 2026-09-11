"""P1 测试：分红预案 + 运营后台（docs/04 §五/十一、docs/06）。

覆盖：预案审核流、auto-match 幂等、upcoming 预估、公告/反馈、
后台用户管理（封禁/重置密码）、汇率税率、操作日志、权限隔离。
"""
import pytest

from conftest import auth, register

ADMIN = {"username": "admin01", "password": "password123"}
USER = {"username": "normal_user", "password": "password123"}


def _make_admin(client, username="admin01"):
    """直接注册一个用户并提升为 super_admin（测试库无外预置）。"""
    token = register(client, username)
    from app.database import engine
    from app.models import User
    from sqlmodel import Session, select
    with Session(engine) as s:
        u = s.exec(select(User).where(User.username == username)).first()
        u.role = "super_admin"
        s.add(u)
        s.commit()
    # 重新登录拿新 token（role 不进 token，token 仍有效）
    r = client.post("/api/auth/login", json={"account": username, "password": "password123"})
    assert r.json()["code"] == 0
    return r.json()["data"]["access_token"]


def _create_holding_with_lot(client, token, **kw):
    body = {"market": "a_share", "code": "601398", "name": "工商银行",
            "currency": "CNY", "freq": "annual",
            "first_lot": {"trade_date": "2023-06-01", "shares": 3000, "price": 5.0}}
    body.update(kw)
    # 持仓创建要求标的已有分红数据（securities 表），测试里直接插一条
    from app.database import engine
    from app.models import Security
    from app.services import security_service
    from sqlmodel import Session
    with Session(engine) as s:
        security_service.upsert_security(s, body["market"], body["code"], body["name"], body["currency"])
        s.commit()
    r = client.post("/api/holdings", headers=auth(token), json=body)
    assert r.json()["code"] == 0, r.text
    return r.json()["data"]["id"]


# ---------- 权限隔离 ----------


def test_normal_user_forbidden_from_admin(client):
    token = register(client, "plain_user")
    r = client.get("/api/admin/stats/overview", headers=auth(token))
    assert r.status_code == 403 and r.json()["code"] == 1004


def test_unauthenticated_admin_rejected(client):
    r = client.get("/api/admin/stats/overview")
    assert r.status_code == 401 and r.json()["code"] == 1002


# ---------- 看板 ----------


def test_admin_overview(client):
    admin_token = _make_admin(client)
    r = client.get("/api/admin/stats/overview", headers=auth(admin_token)).json()
    assert r["code"] == 0
    d = r["data"]
    assert d["user_total"] >= 1
    assert "schedule_pending" in d
    assert len(d["new_users_30d"]) == 30


# ---------- 预案审核流 ----------


def test_schedule_approve_and_auto_match(client):
    """管理员录入预案 → 发布 → 全体用户 auto-match 生成 pending 分红。"""
    admin_token = _make_admin(client, "admin_sch")
    user_token = register(client, "user_sch")
    hid = _create_holding_with_lot(client, user_token)

    # 管理员录入预案（pending）
    r = client.post("/api/admin/schedules", headers=auth(admin_token), json={
        "market": "a_share", "code": "601398", "name": "工商银行",
        "ex_date": "2026-09-10", "record_date": "2026-09-09",
        "pay_date": "2026-09-10", "dps": 0.42}).json()
    assert r["code"] == 0
    sid = r["data"]["id"]
    assert r["data"]["status"] == "pending"

    # 发布 → 后台 auto-match 已为该用户生成 pending 分红
    r = client.post(f"/api/admin/schedules/{sid}/approve", headers=auth(admin_token)).json()
    assert r["code"] == 0 and r["data"]["status"] == "published"

    # 手动触发 auto-match 应为幂等（已存在 → matched=0）
    r = client.post("/api/dividends/auto-match", headers=auth(user_token)).json()
    assert r["code"] == 0
    assert r["data"]["matched"] == 0

    # 分红列表应存在 status=pending 的记录（由后台 auto-match 生成）
    divs = client.get("/api/dividends?status=pending", headers=auth(user_token)).json()
    assert divs["data"]["total"] >= 1
    pending = [d for d in divs["data"]["items"] if d["schedule_id"] is not None]
    assert len(pending) == 1
    assert pending[0]["shares"] == 3000
    assert pending[0]["source"] == "auto_schedule"


def test_schedule_reject(client):
    admin_token = _make_admin(client, "admin_rej")
    r = client.post("/api/admin/schedules", headers=auth(admin_token), json={
        "market": "a_share", "code": "600000", "name": "浦发银行",
        "ex_date": "2026-09-15", "dps": 0.30}).json()
    sid = r["data"]["id"]
    r = client.post(f"/api/admin/schedules/{sid}/reject", headers=auth(admin_token),
                    json={"reason": "dps 与公告原文不符"}).json()
    assert r["code"] == 0 and r["data"]["status"] == "rejected"
    assert r["data"]["reject_reason"] == "dps 与公告原文不符"


def test_schedule_duplicate_publish_blocked(client):
    """同一标的同一除权日不可重复发布（docs/04 错误码 5001）。"""
    admin_token = _make_admin(client, "admin_dup")
    # 第一条发布
    r1 = client.post("/api/admin/schedules", headers=auth(admin_token), json={
        "market": "a_share", "code": "600036", "name": "招商银行",
        "ex_date": "2026-07-10", "dps": 1.50}).json()
    client.post(f"/api/admin/schedules/{r1['data']['id']}/approve", headers=auth(admin_token))
    # 第二条同除权日 → 发布时拦截
    r2 = client.post("/api/admin/schedules", headers=auth(admin_token), json={
        "market": "a_share", "code": "600036", "name": "招商银行",
        "ex_date": "2026-07-10", "dps": 1.55}).json()
    r3 = client.post(f"/api/admin/schedules/{r2['data']['id']}/approve",
                     headers=auth(admin_token))
    assert r3.json()["code"] == 5001


def test_schedule_list_filters(client):
    admin_token = _make_admin(client, "admin_filter")
    client.post("/api/admin/schedules", headers=auth(admin_token), json={
        "market": "us_stock", "code": "AAPL", "name": "Apple",
        "ex_date": "2026-08-15", "dps": 0.25, "currency": "USD"})
    r = client.get("/api/admin/schedules?market=us_stock", headers=auth(admin_token)).json()
    assert r["data"]["total"] >= 1
    assert r["data"]["status_counts"]["pending"] >= 1


# ---------- upcoming 即将到账 ----------


def test_upcoming_returns_holdings_only(client):
    admin_token = _make_admin(client, "admin_up")
    user_token = register(client, "user_up")
    _create_holding_with_lot(client, user_token)
    # 发布一条 AAPL（用户未持有）+ 一条 601398（持有）
    # 用远期日期，避免测试因当天日期推进而被「已过期」过滤掉
    future = "2099-06-01"
    for code, name in (("AAPL", "Apple"), ("601398", "工商银行")):
        r = client.post("/api/admin/schedules", headers=auth(admin_token), json={
            "market": "a_share" if code == "601398" else "us_stock",
            "code": code, "name": name,
            "ex_date": future, "pay_date": future, "dps": 0.42,
            "currency": "CNY" if code == "601398" else "USD"}).json()
        client.post(f"/api/admin/schedules/{r['data']['id']}/approve", headers=auth(admin_token))

    r = client.get("/api/schedules/upcoming", headers=auth(user_token)).json()
    assert r["code"] == 0
    items = r["data"]["items"]
    codes = {i["code"] for i in items}
    assert "601398" in codes and "AAPL" not in codes
    icbc = next(i for i in items if i["code"] == "601398")
    assert icbc["my_shares"] == 3000
    assert icbc["est_gross"] == 3000 * 0.42


# ---------- 公告与反馈 ----------


def test_announcement_lifecycle(client):
    admin_token = _make_admin(client, "admin_ann")
    # 创建草稿
    r = client.post("/api/admin/announcements", headers=auth(admin_token),
                    json={"title": "版本更新", "content": "支持港股通"}).json()
    assert r["data"]["status"] == "draft"
    aid = r["data"]["id"]
    # 用户端看不到草稿
    r = client.get("/api/announcements")
    assert r.json()["data"]["items"] == []
    # 发布
    client.patch(f"/api/admin/announcements/{aid}", headers=auth(admin_token),
                 json={"status": "published"}).json()
    r = client.get("/api/announcements").json()
    assert len(r["data"]["items"]) == 1 and r["data"]["items"][0]["title"] == "版本更新"


def test_feedback_submit_and_handle(client):
    admin_token = _make_admin(client, "admin_fb")
    user_token = register(client, "user_fb")
    # 用户提交反馈
    r = client.post("/api/feedback", headers=auth(user_token),
                    json={"content": "建议支持港股通", "contact": "wx_xxx"}).json()
    assert r["code"] == 0 and r["data"]["status"] == "pending"
    fid = r["data"]["id"]
    # 我的反馈可见
    mine = client.get("/api/feedback/me", headers=auth(user_token)).json()
    assert mine["data"]["items"][0]["id"] == fid
    # 管理员处理
    r = client.patch(f"/api/admin/feedback/{fid}", headers=auth(admin_token),
                     json={"status": "adopted", "reply": "下个版本支持"}).json()
    assert r["code"] == 0 and r["data"]["status"] == "adopted"


# ---------- 后台用户管理 ----------


def test_admin_user_management(client):
    admin_token = _make_admin(client, "admin_um")
    user_token = register(client, "target_user")
    me = client.get("/api/auth/me", headers=auth(user_token)).json()["data"]
    uid = me["id"]

    # 列表
    r = client.get("/api/admin/users?keyword=target", headers=auth(admin_token)).json()
    assert r["data"]["total"] == 1
    assert r["data"]["items"][0]["email"] is not None  # 脱敏后非空

    # 只读数据
    r = client.get(f"/api/admin/users/{uid}/data", headers=auth(admin_token)).json()
    assert r["code"] == 0 and r["data"]["user"]["id"] == uid

    # 重置密码
    r = client.post(f"/api/admin/users/{uid}/reset-password",
                    headers=auth(admin_token)).json()
    assert "temp_password" in r["data"]
    temp = r["data"]["temp_password"]
    login = client.post("/api/auth/login", json={"account": "target_user", "password": temp})
    assert login.json()["code"] == 0

    # 封禁 → 登录被拒
    client.post(f"/api/admin/users/{uid}/ban", headers=auth(admin_token))
    banned_login = client.post("/api/auth/login",
                               json={"account": "target_user", "password": temp})
    assert banned_login.json()["code"] == 1004
    # 解封
    client.post(f"/api/admin/users/{uid}/unban", headers=auth(admin_token))
    ok_login = client.post("/api/auth/login",
                           json={"account": "target_user", "password": temp})
    assert ok_login.json()["code"] == 0


def test_admin_cannot_ban_self(client):
    admin_token = _make_admin(client, "admin_self")
    me = client.get("/api/auth/me", headers=auth(admin_token)).json()["data"]
    r = client.post(f"/api/admin/users/{me['id']}/ban", headers=auth(admin_token))
    assert r.json()["code"] == 1001  # 422 校验失败


# ---------- 汇率与税率 ----------


def test_admin_rates_crud(client):
    admin_token = _make_admin(client, "admin_rate")
    r = client.post("/api/admin/rates", headers=auth(admin_token),
                    json={"base": "USD", "rate": 7.1500, "rate_date": "2026-09-06"}).json()
    assert r["code"] == 0 and r["data"]["source"] == "manual"
    # 列表
    r = client.get("/api/admin/rates?base=USD", headers=auth(admin_token)).json()
    assert r["data"]["total"] >= 1


def test_admin_tax_rules_list_and_update(client):
    admin_token = _make_admin(client, "admin_tax")
    r = client.get("/api/admin/tax-rules", headers=auth(admin_token)).json()
    assert r["code"] == 0 and len(r["data"]["items"]) >= 5
    rule_id = r["data"]["items"][0]["id"]
    # 禁用
    r = client.put(f"/api/admin/tax-rules/{rule_id}", headers=auth(admin_token),
                   json={"enabled": 0}).json()
    assert r["code"] == 0 and r["data"]["enabled"] == 0


def test_normal_rate_uses_admin_rate(client):
    """管理员录入汇率后，用户端 /api/rates 能查到。"""
    admin_token = _make_admin(client, "admin_rate2")
    client.post("/api/admin/rates", headers=auth(admin_token),
                json={"base": "USD", "rate": 7.2000, "rate_date": "2026-09-06"})
    user_token = register(client, "user_rate")
    r = client.get("/api/rates?date=2026-09-06", headers=auth(user_token)).json()
    assert r["code"] == 0
    assert abs(r["data"]["rates"]["USD"] - 7.2) < 0.01


# ---------- 操作日志 ----------


def test_admin_logs_recorded(client):
    admin_token = _make_admin(client, "admin_log")
    client.post("/api/admin/users/99999/reset-password", headers=auth(admin_token))
    client.post("/api/admin/schedules", headers=auth(admin_token), json={
        "market": "a_share", "code": "600519", "name": "贵州茅台",
        "ex_date": "2026-06-30", "dps": 25.80})
    r = client.get("/api/admin/logs", headers=auth(admin_token)).json()
    actions = {i["action"] for i in r["data"]["items"]}
    assert "schedule.create" in actions


# ---------- 爬虫（离线模式）----------


def test_crawl_offline_returns_zero(client):
    admin_token = _make_admin(client, "admin_crawl")
    r = client.post("/api/admin/schedules/crawl", headers=auth(admin_token)).json()
    assert r["code"] == 0
    assert r["data"]["fetched"] == 0
    assert "离线" in r["data"]["message"]


# ---------- 系统配置开关生效验证 ----------


def test_user_submit_config_gate(client):
    """user_submit 关闭时用户提交预案返回 403；开启后可提交 pending。"""
    from app.services import config_service
    user_token = register(client, "usr_submit")

    # 关闭：403
    config_service.set_values(_session(), {"user_submit": False}, admin_id=1)
    r = client.post("/api/schedules", headers=auth(user_token), json={
        "market": "a_share", "code": "600000", "name": "浦发银行", "dps": 0.3})
    assert r.status_code == 403

    # 开启：创建 pending，source=user_submit
    config_service.set_values(_session(), {"user_submit": True}, admin_id=1)
    r = client.post("/api/schedules", headers=auth(user_token), json={
        "market": "a_share", "code": "600000", "name": "浦发银行", "dps": 0.3}).json()
    assert r["code"] == 0 and r["data"]["status"] == "pending"

    # 清理
    config_service.reset_value(_session(), "user_submit", admin_id=1)


def test_forecast_freq_gate(client):
    """forecast_freq 关闭时不生成推算预案；开启后为季派/月派持仓生成。"""
    from app.database import engine
    from app.models import Dividend, DividendSchedule, Holding, Lot
    from app.services import config_service, schedule_service
    from sqlmodel import Session, select

    user_token = register(client, "usr_fc")
    # 建一个季派持仓 + 一笔历史已确认分红
    hid = client.post("/api/holdings", headers=auth(user_token), json={
        "market": "a_share", "code": "601398", "name": "工商银行",
        "currency": "CNY", "freq": "quarterly",
        "first_lot": {"trade_date": "2024-01-01", "shares": 1000, "price": 5.0}}).json()["data"]["id"]
    from datetime import date, timedelta
    pay = (date.today() - timedelta(days=80)).isoformat()
    with Session(engine) as s:
        s.add(Dividend(user_id=_uid(client, user_token), holding_id=hid,
                       ex_date=pay, record_date=pay, pay_date=pay, dps=0.26,
                       status="confirmed", currency="CNY"))
        s.commit()

    # 关闭：0 条
    config_service.set_values(_session(), {"forecast_freq": False}, admin_id=1)
    assert schedule_service.generate_forecast_schedules(_session()) == 0

    # 开启：生成 1 条推算预案（90 天后）
    config_service.set_values(_session(), {"forecast_freq": True}, admin_id=1)
    n = schedule_service.generate_forecast_schedules(_session())
    assert n == 1
    with Session(engine) as s:
        sch = s.exec(select(DividendSchedule).where(
            DividendSchedule.code == "601398",
            DividendSchedule.source == "forecast")).first()
        assert sch and sch.status == "pending"

    # 幂等：再跑一次不重复
    assert schedule_service.generate_forecast_schedules(_session()) == 0
    config_service.reset_value(_session(), "forecast_freq", admin_id=1)


def test_remind_3d_gate(client):
    """remind_3d 关闭时不触发提醒；开启时正常返回提醒用户数（>=0）。"""
    from app.services import config_service, schedule_service
    config_service.set_values(_session(), {"remind_3d": False}, admin_id=1)
    assert schedule_service.check_dividend_reminders(_session()) == 0
    # 开启时返回非负整数（共享库可能有符合条件的预案）
    config_service.set_values(_session(), {"remind_3d": True}, admin_id=1)
    assert schedule_service.check_dividend_reminders(_session()) >= 0
    config_service.reset_value(_session(), "remind_3d", admin_id=1)


def _session():
    from app.database import engine
    from sqlmodel import Session
    return Session(engine)


def _uid(client, token):
    return client.get("/api/auth/me", headers=auth(token)).json()["data"]["id"]


# ---------- securities.freq 按分红历史自动推断 ----------


def _seed_yearly_schedules(code, per_year, years=(2023, 2024), source="manual",
                           status="pending"):
    """每个历史年份插 per_year 条预案（月份/日期取模保证 ex_date 不重复）。"""
    from app.database import engine
    from app.models import DividendSchedule
    from app.services import security_service
    from sqlmodel import Session
    with Session(engine) as s:
        security_service.upsert_security(s, "a_share", code, f"测试{code}")
        for y in years:
            for i in range(per_year):
                month = (i * 12 // per_year) + 1
                day = (i % 27) + 1
                d = f"{y}-{month:02d}-{day:02d}"
                s.add(DividendSchedule(
                    market="a_share", code=code, ex_date=d, pay_date=d, dps=0.1,
                    source=source, status=status))
        s.commit()


def test_infer_freq_buckets(client):
    """年度派息次数中位数落桶：1→年派，2→半年派，4→季派，12→月派。"""
    from app.database import engine
    from app.services import security_service
    from sqlmodel import Session

    cases = {"TANNUAL": (1, "annual"), "TSEMI": (2, "semi_annual"),
             "TQTR": (4, "quarterly"), "TMONTH": (12, "monthly")}
    for code, (n, _expected) in cases.items():
        _seed_yearly_schedules(code, n)

    with Session(engine) as s:
        for code, (_n, expected) in cases.items():
            assert security_service.infer_freq(s, "a_share", code) == expected, code
            changed = security_service.refresh_security_freq(s, "a_share", code)
            assert changed is True
            sec = security_service.get_security(s, "a_share", code)
            assert sec.freq == expected
        # 再刷一次幂等：无变化返回 False
        assert security_service.refresh_security_freq(s, "a_share", "TQTR") is False


def test_infer_freq_ignores_forecast_rejected_and_partial_year(client):
    """推算/驳回预案不作证据；只有当年（不完整）数据时按当年计数推断。"""
    from app.database import engine
    from app.models import DividendSchedule
    from app.services import security_service
    from sqlmodel import Session

    # 4 条 forecast + rejected：无有效证据 → None（保持 unknown）
    _seed_yearly_schedules("TNOEV", 4, source="forecast")
    with Session(engine) as s:
        # _seed 已插了 forecast；再补 4 条 rejected
        for i in range(4):
            d = f"2024-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}"
            s.add(DividendSchedule(market="a_share", code="TNOEV",
                                   ex_date=d, dps=0.1, source="manual",
                                   status="rejected"))
        s.commit()
        assert security_service.infer_freq(s, "a_share", "TNOEV") is None

    # 只有当年数据（4 条）→ 无历史年可剔除，直接按当年计数 → 季派
    with Session(engine) as s:
        security_service.upsert_security(s, "a_share", "TCUR", "测试当年")
        for i in range(4):
            d = f"2026-{(i * 3) + 1:02d}-15"
            s.add(DividendSchedule(market="a_share", code="TCUR",
                                   ex_date=d, dps=0.1, source="manual",
                                   status="published"))
        s.commit()
        assert security_service.infer_freq(s, "a_share", "TCUR") == "quarterly"


def test_securities_endpoint_returns_freq(client):
    """下拉接口带出推断出的 freq，供前端创建持仓时自动回填。"""
    _seed_yearly_schedules("TAPIQ", 4)
    from app.database import engine
    from app.services import security_service
    from sqlmodel import Session
    with Session(engine) as s:
        security_service.refresh_security_freq(s, "a_share", "TAPIQ")

    token = register(client, "usr_freq_api")
    r = client.get("/api/schedules/securities?keyword=TAPIQ", headers=auth(token))
    items = r.json()["data"]["items"]
    hit = [x for x in items if x["code"] == "TAPIQ"]
    assert hit and hit[0]["freq"] == "quarterly"


def test_holding_freq_override_and_auto_reset(client):
    """持仓 freq 可手动覆盖；详情/列表带 system_freq；freq=auto 恢复系统推断值。"""
    _seed_yearly_schedules("TAUTO", 4)
    from app.database import engine
    from app.services import security_service
    from sqlmodel import Session
    with Session(engine) as s:
        security_service.refresh_security_freq(s, "a_share", "TAUTO")

    token = register(client, "usr_auto_freq")
    r = client.post("/api/holdings", headers=auth(token), json={
        "market": "a_share", "code": "TAUTO", "name": "测试TAUTO",
        "currency": "CNY", "freq": "annual",  # 手动覆盖系统推断的季派
        "first_lot": {"trade_date": "2024-06-01", "shares": 100, "price": 10.0}})
    assert r.json()["code"] == 0, r.text
    hid = r.json()["data"]["id"]
    assert r.json()["data"]["system_freq"] == "quarterly"

    d = client.get(f"/api/holdings/{hid}", headers=auth(token)).json()["data"]
    assert d["freq"] == "annual" and d["system_freq"] == "quarterly"

    # 非法频率值被入参校验拒绝
    assert client.patch(f"/api/holdings/{hid}", headers=auth(token),
                        json={"freq": "bad"}).status_code == 422

    # 恢复系统推断：freq 解析为季派
    p = client.patch(f"/api/holdings/{hid}", headers=auth(token),
                     json={"freq": "auto"}).json()["data"]
    assert p["freq"] == "quarterly" and p["system_freq"] == "quarterly"

    # 列表也带 system_freq
    lst = client.get("/api/holdings", headers=auth(token)).json()["data"]["items"]
    row = [x for x in lst if x["code"] == "TAUTO"][0]
    assert row["freq"] == "quarterly" and row["system_freq"] == "quarterly"


def test_security_map_handles_over_1000_keys(client):
    """回归：key 数 >1000 时旧 OR 拼接触发 'Expression tree is too large'；
    row-value IN 分批后必须正常返回（key 不存在也必须能查，不报错）。"""
    from app.database import engine
    from app.services import security_service
    from sqlmodel import Session

    keys = [("a_share", f"{i:06d}") for i in range(1200)]
    with Session(engine) as s:
        result = security_service.security_map(s, keys)
        assert isinstance(result, dict)
        # 不报错即通过；返回的键必须都在请求集合内（测试库可能已有 000858 等真实代码）
        assert set(result.keys()) <= set(keys)
