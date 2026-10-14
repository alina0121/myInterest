"""账户设置接口测试：个人资料（昵称/头像）、解绑邮箱、注销账户级联删除。"""
from conftest import auth, register

from conftest import ensure_security
from test_api import HOLDING, _setup_moutai


# ---------- 个人资料 ----------

def test_profile_update(client):
    token = register(client, "profile1")
    r = client.put("/api/auth/profile", headers=auth(token),
                   json={"nickname": "  攒友  ", "avatar": "💰"}).json()
    assert r["code"] == 0
    assert r["data"]["user"]["nickname"] == "攒友"  # trim
    assert r["data"]["user"]["avatar"] == "💰"
    me = client.get("/api/auth/me", headers=auth(token)).json()
    assert me["data"]["nickname"] == "攒友"


def test_profile_empty_rejected(client):
    token = register(client, "profile2")
    r = client.put("/api/auth/profile", headers=auth(token), json={})
    assert r.status_code == 400
    r = client.put("/api/auth/profile", headers=auth(token), json={"nickname": "   "})
    assert r.status_code == 400


# ---------- 解绑邮箱 ----------

def test_unbind_email(client):
    token = register(client, "unbind1")
    assert client.get("/api/auth/me", headers=auth(token)).json()["data"]["email"] == "unbind1@test.com"
    r = client.post("/api/auth/unbind-email", headers=auth(token)).json()
    assert r["code"] == 0 and r["data"]["user"]["email"] == ""
    # 未绑定再解绑 → 400
    r2 = client.post("/api/auth/unbind-email", headers=auth(token))
    assert r2.status_code == 400


# ---------- 注销账户 ----------

def test_delete_me_cascade(client):
    """注销：物理删除账号与名下持仓/批次/反馈/设置；旧 token 失效。"""
    from sqlmodel import Session, select
    from app.database import engine
    from app.models import Feedback, Holding, Lot, User, UserSetting

    token = register(client, "dave")
    hid = _setup_moutai(client, token)  # 1 持仓 + 2 批次
    client.post("/api/feedback", headers=auth(token), json={"content": "test"})

    r = client.delete("/api/auth/me", headers=auth(token))
    assert r.json()["code"] == 0
    assert r.json()["data"]["deleted"] == {"lots": 2, "holdings": 1, "feedbacks": 1}

    with Session(engine) as s:
        assert s.exec(select(User).where(User.username == "dave")).first() is None
        assert s.exec(select(Holding).where(Holding.id == hid)).first() is None
        assert s.exec(select(Lot).where(Lot.holding_id == hid)).first() is None
        assert s.exec(select(Feedback).where(Feedback.user_id == 4)).first() is None  # dave=第4个注册用户
    # 旧 token 失效
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401


def test_delete_me_admin_forbidden(client):
    from sqlmodel import Session, select
    from app.database import engine
    from app.models import User

    token = register(client, "boss")
    with Session(engine) as s:
        u = s.exec(select(User).where(User.username == "boss")).first()
        u.role = "admin"
        s.add(u)
        s.commit()
    r = client.delete("/api/auth/me", headers=auth(token))
    assert r.json()["code"] == 1004  # FORBIDDEN
