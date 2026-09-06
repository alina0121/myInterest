"""测试环境准备：隔离数据库 + 离线汇率 + 注入 backend 到 sys.path。

本 conftest 位于 backend 根目录，pytest 导入它时自动把 backend 加入 sys.path。
"""
import os
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# 必须在导入 app.* 之前设置环境变量
_TEST_DIR = tempfile.mkdtemp(prefix="xi_test_")
os.environ["XI_DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/xi_test.db"
os.environ["XI_FX_OFFLINE"] = "1"      # 测试不走在线汇率，用兜底值
os.environ["XI_CRAWL_OFFLINE"] = "1"   # 测试不触发真实爬虫
os.environ["XI_SCHEDULER"] = "0"       # 测试不启动后台定时任务

from fastapi.testclient import TestClient  # noqa: E402
import pytest  # noqa: E402

from app.db_init import init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    init_db(seed_fx=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """每个用例清空登录/注册限流计数，避免测试互相干扰。"""
    from app.api import auth as auth_api
    auth_api._hits.clear()
    yield


def register(client: TestClient, username: str, password: str = "password123") -> str:
    resp = client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@test.com", "password": password})
    assert resp.status_code == 200, resp.text
    assert resp.json()["code"] == 0
    return resp.json()["data"]["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
