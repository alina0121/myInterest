"""API 集成测试：认证 → 持仓多批次 → 分红归属 → 税费分档 → 统计/日历 → 数据隔离。"""
from conftest import auth, ensure_security, register

# ---------- 认证 ----------


def test_register_login_me(client):
    token = register(client, "alice")
    assert token
    me = client.get("/api/auth/me", headers=auth(token)).json()
    assert me["code"] == 0 and me["data"]["username"] == "alice"
    # 未登录
    r = client.get("/api/auth/me")
    assert r.status_code == 401 and r.json()["code"] == 1002
    # 登录（含错误密码）
    bad = client.post("/api/auth/login", json={"account": "alice", "password": "wrong-pass"})
    assert bad.json()["code"] == 2001
    good = client.post("/api/auth/login", json={"account": "alice", "password": "password123"})
    assert good.json()["code"] == 0 and "refresh_token" in good.json()["data"]


# ---------- 持仓多批次 ----------

HOLDING = {"market": "a_share", "code": "600519", "name": "贵州茅台", "currency": "CNY",
           "freq": "annual"}


def _setup_moutai(client, token):
    ensure_security(HOLDING["market"], HOLDING["code"], HOLDING["name"], HOLDING["currency"])
    r = client.post("/api/holdings", headers=auth(token),
                    json={**HOLDING, "first_lot": {"trade_date": "2022-03-15",
                                                   "shares": 60, "price": 1580}}).json()
    holding_id = r["data"]["id"]
    client.post(f"/api/holdings/{holding_id}/lots", headers=auth(token),
                json={"trade_date": "2023-09-20", "direction": "buy",
                      "shares": 40, "price": 1600})
    return holding_id


def test_holding_multi_batch_aggregation(client):
    token = register(client, "bobby")
    hid = _setup_moutai(client, token)
    h = client.get(f"/api/holdings/{hid}", headers=auth(token)).json()["data"]
    assert h["shares_now"] == 100
    assert h["lot_count"] == 2
    # 加权平均成本 (60*1580 + 40*1600) / 100 = 1588
    assert abs(h["avg_cost"] - 1588.0) < 0.01
    assert h["cost_total"] == 158800.0
    # 卖出后：数量减少，成本不冲减
    r = client.post(f"/api/holdings/{hid}/lots", headers=auth(token),
                    json={"trade_date": "2024-01-10", "direction": "sell",
                          "shares": 50, "price": 1700})
    assert r.json()["code"] == 0
    h2 = client.get(f"/api/holdings/{hid}", headers=auth(token)).json()["data"]
    assert h2["shares_now"] == 50 and h2["cost_total"] == 158800.0
    # 超卖被拒绝
    r = client.post(f"/api/holdings/{hid}/lots", headers=auth(token),
                    json={"trade_date": "2024-02-10", "direction": "sell",
                          "shares": 60, "price": 1700})
    assert r.json()["code"] == 4001


def test_duplicate_holding_rejected(client):
    token = register(client, "carol")
    ensure_security(HOLDING["market"], HOLDING["code"], HOLDING["name"], HOLDING["currency"])
    client.post("/api/holdings", headers=auth(token), json={**HOLDING})
    r = client.post("/api/holdings", headers=auth(token), json={**HOLDING})
    assert r.json()["code"] == 3001


# ---------- 分红归属与税费 ----------


def test_dividend_allocation_skips_future_batch(client):
    """2023-06-28 派息：第二批次（2023-09-20 买入）尚未持有，只算 60 股。"""
    token = register(client, "dave")
    hid = _setup_moutai(client, token)
    r = client.post("/api/dividends", headers=auth(token), json={
        "holding_id": hid, "ex_date": "2023-06-28", "pay_date": "2023-06-29",
        "dps": 25.91}).json()
    d = r["data"]
    assert d["record_date_auto"] is True  # A股自动取除权日前一日
    assert d["shares"] == 60
    assert d["allocations"][0]["lot_id"] is not None
    assert d["gross_amount"] == 1554.60  # 60 × 25.91
    # 批次持有 > 1 年 → 税率 0
    assert d["tax"] == 0.0 and d["net_amount"] == 1554.60
    assert len(d["allocations"]) == 1


def test_dividend_allocation_both_batches_and_tax(client):
    """2024 派息：两个批次都参与；批次二持有 281 天 → 10% 税。"""
    token = register(client, "erin")
    hid = _setup_moutai(client, token)
    r = client.post("/api/dividends", headers=auth(token), json={
        "holding_id": hid, "ex_date": "2024-06-28", "pay_date": "2024-06-28",
        "dps": 27.628}).json()
    d = r["data"]
    assert d["shares"] == 100
    # 批次1: 60 股，持有 > 1年，免税 → 1657.68
    # 批次2: 40 股，持有 281 天，10% → gross 1105.12, tax 110.51, net 994.61
    allocs = {a["shares"]: a for a in d["allocations"]}
    assert allocs[60]["tax"] == 0.0 and allocs[60]["net"] == 1657.68
    assert allocs[40]["tax"] == 110.51 and allocs[40]["net"] == 994.61
    assert d["gross_amount"] == 2762.80  # 100 × 27.628
    assert d["tax"] == 110.51
    assert d["net_amount"] == 2652.29  # 2762.80 - 110.51


def test_tax_tier_short_holding(client):
    """持股 ≤ 1 个月 → 20% 税。"""
    token = register(client, "frank")
    ensure_security("a_share", "000858", "五粮液")
    r = client.post("/api/holdings", headers=auth(token), json={
        "market": "a_share", "code": "000858", "name": "五粮液", "currency": "CNY",
        "first_lot": {"trade_date": "2026-01-01", "shares": 100, "price": 10}}).json()
    hid = r["data"]["id"]
    d = client.post("/api/dividends", headers=auth(token), json={
        "holding_id": hid, "ex_date": "2026-01-15", "pay_date": "2026-01-16",
        "dps": 0.50}).json()["data"]
    assert d["gross_amount"] == 50.0
    assert d["tax"] == 10.0  # 50 × 20%
    assert d["net_amount"] == 40.0


def test_pending_confirm_with_actual_net(client):
    token = register(client, "grace")
    ensure_security("fund", "000001", "华夏成长")
    r = client.post("/api/holdings", headers=auth(token), json={
        "market": "fund", "code": "000001", "name": "华夏成长", "currency": "CNY",
        "first_lot": {"trade_date": "2025-01-01", "shares": 1000, "price": 1.5}}).json()
    hid = r["data"]["id"]
    d = client.post("/api/dividends", headers=auth(token), json={
        "holding_id": hid, "ex_date": "2026-03-01", "pay_date": "2026-03-05",
        "dps": 0.05, "status": "pending"}).json()["data"]
    assert d["status"] == "pending" and d["gross_amount"] == 50.0
    c = client.post(f"/api/dividends/{d['id']}/confirm", headers=auth(token),
                    json={"actual_net": 51.0}).json()["data"]
    assert c["status"] == "confirmed"
    assert c["net_amount"] == 51.0
    assert c["tax"] == -1.0  # gross - actual_net，基金实收可能略高于估算
    assert c["tax_overridden"] is True


def test_recalc_after_adding_batch(client):
    """补录早于登记日的批次 → 已有分红自动重算参与股数。"""
    token = register(client, "henry")
    hid = _setup_moutai(client, token)
    d = client.post("/api/dividends", headers=auth(token), json={
        "holding_id": hid, "ex_date": "2024-06-28", "pay_date": "2024-06-28",
        "dps": 27.628}).json()["data"]
    assert d["shares"] == 100
    # 删除批次二 → 分红只剩 60 股参与
    lots = client.get(f"/api/holdings/{hid}/lots", headers=auth(token)).json()["data"]["items"]
    lot2 = next(l for l in lots if l["trade_date"] == "2023-09-20")
    r = client.delete(f"/api/lots/{lot2['id']}", headers=auth(token))
    assert r.json()["code"] == 0
    d2 = client.get(f"/api/dividends/{d['id']}", headers=auth(token)).json()["data"]
    assert d2["shares"] == 60
    assert d2["gross_amount"] == 1657.68
    assert d2["tax"] == 0.0


# ---------- 统计 / 日历 / 设置 ----------


def test_stats_and_calendar(client):
    token = register(client, "iris")
    hid = _setup_moutai(client, token)
    client.post("/api/dividends", headers=auth(token), json={
        "holding_id": hid, "ex_date": "2024-06-28", "pay_date": "2024-06-28",
        "dps": 27.628})
    s = client.get("/api/stats/summary", headers=auth(token)).json()["data"]
    assert s["holding_count"] == 1
    assert s["total_dividend_cny"] == 2652.29
    t = client.get("/api/stats/monthly-trend", headers=auth(token),
                   params={"range": "12m"}).json()["data"]
    assert len(t["months"]) == 12 and "amounts_cny" in t
    cal = client.get("/api/calendar", headers=auth(token),
                     params={"year": 2024, "month": 6}).json()["data"]
    assert "28" in cal["days"]
    assert cal["month_confirmed_cny"] == 2652.29
    fc = client.get("/api/stats/forecast", headers=auth(token)).json()["data"]
    assert len(fc["months"]) == 12 and fc["published"] == [0] * 12


def test_settings_get_put(client):
    token = register(client, "jack")
    s = client.get("/api/settings", headers=auth(token)).json()["data"]
    assert s["remind_before_days"] == 3
    u = client.put("/api/settings", headers=auth(token),
                   json={"remind_before_days": 7, "push_enabled": False}).json()["data"]
    assert u["remind_before_days"] == 7 and u["push_enabled"] is False


# ---------- 多用户数据隔离 ----------


def test_user_data_isolation(client):
    token_a = register(client, "user_a")
    token_b = register(client, "user_b")
    hid = _setup_moutai(client, token_a)
    # B 看不到 A 的持仓/分红
    r = client.get(f"/api/holdings/{hid}", headers=auth(token_b))
    assert r.status_code == 404 and r.json()["code"] == 1005
    div = client.post("/api/dividends", headers=auth(token_a), json={
        "holding_id": hid, "ex_date": "2024-06-28", "pay_date": "2024-06-28",
        "dps": 27.628}).json()["data"]
    r = client.get(f"/api/dividends/{div['id']}", headers=auth(token_b))
    assert r.status_code == 404
    # B 的持仓列表为空
    assert client.get("/api/holdings", headers=auth(token_b)).json()["data"]["total"] == 0
    # B 用 A 的 holding_id 记分红 → 404
    r = client.post("/api/dividends", headers=auth(token_b), json={
        "holding_id": hid, "ex_date": "2024-06-28", "pay_date": "2024-06-28",
        "dps": 1.0})
    assert r.status_code == 404
