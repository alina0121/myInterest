"""微信小程序登录测试（docs/04 §1.5）。mock 模式下 code 直接当 openid。"""
from conftest import auth, register


def test_wx_login_creates_new_user(client):
    """首次微信登录 → 自动创建用户，返回 is_new_user=true。"""
    r = client.post("/api/auth/wx-login", json={"code": "mock_openid_001"}).json()
    assert r["code"] == 0
    assert r["data"]["is_new_user"] is True
    assert r["data"]["user"]["has_wx"] is True
    assert r["data"]["user"]["username"].startswith("wx_")
    assert "access_token" in r["data"]


def test_wx_login_existing_user(client):
    """同一 openid 再次登录 → 复用已有用户，is_new_user=false，不重复建号。"""
    r1 = client.post("/api/auth/wx-login", json={"code": "mock_openid_002"}).json()
    r2 = client.post("/api/auth/wx-login", json={"code": "mock_openid_002"}).json()
    assert r2["data"]["is_new_user"] is False
    assert r2["data"]["user"]["id"] == r1["data"]["user"]["id"]
    # 用 token 访问受保护接口
    me = client.get("/api/auth/me", headers=auth(r2["data"]["access_token"])).json()
    assert me["code"] == 0 and me["data"]["id"] == r1["data"]["user"]["id"]


def test_wx_login_with_profile(client):
    """携带昵称头像 → 写入用户资料。"""
    r = client.post("/api/auth/wx-login", json={
        "code": "mock_openid_003", "nickname": "测试用户", "avatar": "http://x/avatar.png"}).json()
    assert r["data"]["user"]["nickname"] == "测试用户"
    assert r["data"]["user"]["avatar"] == "http://x/avatar.png"


def test_wx_login_banned_user(client):
    """被封禁的微信用户登录 → 返回 1003（FORBIDDEN）。"""
    r = client.post("/api/auth/wx-login", json={"code": "mock_openid_004"}).json()
    uid = r["data"]["user"]["id"]
    # 直接在 DB 封禁
    from app.database import engine
    from app.models import User
    from sqlmodel import Session
    with Session(engine) as s:
        u = s.get(User, uid)
        u.status = "banned"
        s.add(u); s.commit()
    r2 = client.post("/api/auth/wx-login", json={"code": "mock_openid_004"})
    assert r2.json()["code"] == 1004


def test_wx_login_code_required(client):
    """空 code → 422 校验失败。"""
    r = client.post("/api/auth/wx-login", json={"code": ""})
    assert r.status_code == 422
