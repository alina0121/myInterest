"""系统配置接口测试（后台 GET/PUT/DELETE /api/admin/config）。

覆盖：
- 权限：普通用户不可见不可改；普通 admin 只读；仅 super_admin 可写
- 脱敏：敏感项（API Key/Secret）不回传原文，只给 has_value/mask
- 生效：保存后 config_service 立即读到新值（缓存失效），并标记 overridden
- 校验：非法小时/越界整数/未知 key 返回 422
- 敏感项空串 = 不修改；reset 回退默认
- 操作日志只记 key 不记 value
"""
import pytest
from sqlmodel import Session, select

from conftest import auth, register


def _make_role(client, username, role):
    """注册用户并直接在库里改角色，重新登录取 token（role 不进 JWT，走库校验）。"""
    register(client, username)
    from app.database import engine
    from app.models import User
    with Session(engine) as s:
        u = s.exec(select(User).where(User.username == username)).first()
        u.role = role
        s.add(u)
        s.commit()
    r = client.post("/api/auth/login", json={"account": username, "password": "password123"})
    assert r.json()["code"] == 0
    return r.json()["data"]["access_token"]


@pytest.fixture(autouse=True)
def _isolate_config():
    """每个用例前后清空 system_configs 覆盖层并失效缓存，避免污染共享测试库。"""
    from app.database import engine
    from app.models import SystemConfig
    from app.services import config_service

    def _clear():
        with Session(engine) as s:
            for row in s.exec(select(SystemConfig)).all():
                s.delete(row)
            s.commit()
        config_service.invalidate_cache()

    _clear()
    yield
    _clear()


def _find_item(groups, key):
    for g in groups:
        for item in g["items"]:
            if item["key"] == key:
                return item
    raise AssertionError(f"config item not found: {key}")


# ---------- 权限 ----------


def test_normal_user_cannot_read_or_write(client):
    token = register(client, "cfg_plain")
    r = client.get("/api/admin/config", headers=auth(token))
    assert r.status_code == 403
    r = client.put("/api/admin/config", headers=auth(token),
                   json={"items": {"scheduler_enabled": False}})
    assert r.status_code == 403


def test_admin_readonly(client):
    """普通 admin 可读不可写。"""
    token = _make_role(client, "cfg_admin", "admin")
    r = client.get("/api/admin/config", headers=auth(token))
    assert r.status_code == 200 and r.json()["code"] == 0
    groups = r.json()["data"]["groups"]
    assert any(g["category"] == "安全" for g in groups)
    r = client.put("/api/admin/config", headers=auth(token),
                   json={"items": {"scheduler_enabled": False}})
    assert r.status_code == 403
    r = client.delete("/api/admin/config/scheduler_enabled", headers=auth(token))
    assert r.status_code == 403


# ---------- 脱敏与元数据 ----------


def test_sensitive_values_masked(client, monkeypatch):
    # 排除部署机已配 XI_AV_API_KEY 的干扰，验证「未配置」与「已配置」两种脱敏形态
    monkeypatch.delenv("XI_AV_API_KEY", raising=False)
    token = _make_role(client, "cfg_super1", "super_admin")
    r = client.get("/api/admin/config", headers=auth(token)).json()
    item = _find_item(r["data"]["groups"], "av_api_key")
    # 未配置时：value 恒为 None，只有 has_value/mask 占位
    assert item["value"] is None and item["has_value"] is False and item["mask"] == ""

    # 写入密钥后再读：仍不回传原文，只露后 4 位
    client.put("/api/admin/config", headers=auth(token),
               json={"items": {"av_api_key": "ABCDEFG123456"}})
    r = client.get("/api/admin/config", headers=auth(token)).json()
    item = _find_item(r["data"]["groups"], "av_api_key")
    assert item["value"] is None and item["has_value"] is True
    assert item["mask"].endswith("3456") and "ABCDEFG" not in item["mask"]


# ---------- 保存生效 / 校验 / 重置 ----------


def test_update_takes_effect_immediately(client):
    from app.services import config_service
    token = _make_role(client, "cfg_super2", "super_admin")

    assert config_service.get_int("login_rate_limit_per_min") == 10
    r = client.put("/api/admin/config", headers=auth(token),
                   json={"items": {"login_rate_limit_per_min": 12}}).json()
    assert r["code"] == 0 and r["data"]["changed"] == ["login_rate_limit_per_min"]
    # 服务层立即读到新值（缓存已失效）
    assert config_service.get_int("login_rate_limit_per_min") == 12
    # 返回视图标记为「已自定义」
    item = _find_item(r["data"]["groups"], "login_rate_limit_per_min")
    assert item["overridden"] is True and item["value"] == 12

    # reset 后回默认，overridden 撤销
    r = client.delete("/api/admin/config/login_rate_limit_per_min",
                      headers=auth(token)).json()
    assert r["code"] == 0
    assert config_service.get_int("login_rate_limit_per_min") == 10
    assert _find_item(r["data"]["groups"], "login_rate_limit_per_min")["overridden"] is False


def test_bool_and_list_normalization(client):
    from app.services import config_service
    token = _make_role(client, "cfg_super3", "super_admin")
    # 布尔开关
    client.put("/api/admin/config", headers=auth(token),
               json={"items": {"scheduler_enabled": False}})
    assert config_service.get_bool("scheduler_enabled") is False
    # 白名单：小写+空格 → 服务端归一化为大写紧凑形式
    r = client.put("/api/admin/config", headers=auth(token),
                   json={"items": {"crawl_us_tickers": "aapl, msft ,ko"}}).json()
    assert config_service.get_list("crawl_us_tickers") == ["AAPL", "MSFT", "KO"]
    item = _find_item(r["data"]["groups"], "crawl_us_tickers")
    assert item["value"] == "AAPL,MSFT,KO"


@pytest.mark.parametrize("idx,key,bad_value", [
    (1, "scheduler_hours", "99"),          # 小时越界
    (2, "scheduler_hours", "8,25"),        # 含非法小时
    (3, "login_rate_limit_per_min", 999),  # 超出 max
    (4, "crawl_a_share_page_size", 1),     # 低于 min
    (5, "fx_fallback_usd", -1),            # float 必须 > 0
    (6, "unknown_config_key", "x"),        # 未注册的 key
])
def test_invalid_values_rejected(client, idx, key, bad_value):
    token = _make_role(client, f"cfg_bad_{idx}", "super_admin")
    r = client.put("/api/admin/config", headers=auth(token),
                   json={"items": {key: bad_value}})
    assert r.status_code == 422 and r.json()["code"] == 1001, r.text


def test_empty_sensitive_value_keeps_secret(client, monkeypatch):
    """敏感项提交空串 = 不修改；要清空请走 reset。"""
    monkeypatch.delenv("XI_WX_SECRET", raising=False)
    from app.services import config_service
    config_service.invalidate_cache()
    token = _make_role(client, "cfg_super4", "super_admin")
    client.put("/api/admin/config", headers=auth(token),
               json={"items": {"wx_secret": "TOPSECRET9999"}})
    assert config_service.get_text("wx_secret") == "TOPSECRET9999"
    # 再提交空串（页面保存时密钥框留空）→ 原值保留
    client.put("/api/admin/config", headers=auth(token),
               json={"items": {"wx_secret": "", "scheduler_hours": "9,20"}})
    assert config_service.get_text("wx_secret") == "TOPSECRET9999"
    # 空串也不出现在变更列表里
    r = client.put("/api/admin/config", headers=auth(token),
                   json={"items": {"wx_secret": ""}}).json()
    assert r["data"]["changed"] == []
    # reset 后回默认（空串）
    client.delete("/api/admin/config/wx_secret", headers=auth(token))
    assert config_service.get_text("wx_secret") == ""


def test_operation_log_omits_secret_value(client):
    """写配置落操作日志，且日志内容只含 key、不含密钥原文。"""
    token = _make_role(client, "cfg_super5", "super_admin")
    client.put("/api/admin/config", headers=auth(token),
               json={"items": {"av_api_key": "SENSITIVE_MAGIC_7777"}})
    logs = client.get("/api/admin/logs", headers=auth(token)).json()["data"]["items"]
    entries = [l for l in logs if l["action"] == "config.update"]
    assert entries, "config.update 应落操作日志"
    entry = entries[0]
    assert "av_api_key" in entry["detail"]["keys"]
    assert "SENSITIVE_MAGIC_7777" not in str(entry)
