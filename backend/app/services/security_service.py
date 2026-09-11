"""股票基础信息服务（securities 表）。

提供 upsert（幂等写入）与批量查询，供 crawler / admin / user_submit / forecast
在创建 dividend_schedule 前先确保股票基础数据存在。

派息频率 freq 不由用户在标的上维护，而是按历年分红预案次数自动推断
（infer_freq / refresh_*），用户创建持仓时仅可在此默认值上手动覆盖。
"""
from typing import Iterable

from sqlalchemy import text
from sqlmodel import Session, select

from ..models import Security
from ..utils.timeutil import now_str, today_str


def upsert_security(session: Session, market: str, code: str, name: str,
                    currency: str = "CNY") -> Security:
    """幂等写入股票基础信息：同 (market, code) 已存在则更新 name/currency，
    不存在则插入。返回对应 Security（id 不变）。

    使用 SQLite INSERT ... ON CONFLICT 原子语义，避免先查再插的竞态。
    """
    session.execute(text(
        "INSERT INTO securities (market, code, name, currency, freq, created_at, updated_at) "
        "VALUES (:m, :c, :n, :cur, 'unknown', :ts, :ts) "
        "ON CONFLICT(market, code) DO UPDATE SET "
        "name=excluded.name, currency=excluded.currency, updated_at=excluded.updated_at"
    ), {"m": market, "c": code, "n": name, "cur": currency, "ts": now_str()})
    session.flush()
    sec = session.exec(select(Security).where(
        Security.market == market, Security.code == code)).first()
    assert sec is not None
    return sec


def get_security(session: Session, market: str, code: str) -> Security | None:
    return session.exec(select(Security).where(
        Security.market == market, Security.code == code)).first()


def security_map(session: Session, keys: Iterable[tuple[str, str]]
                 ) -> dict[tuple[str, str], Security]:
    """批量按 (market, code) 查 securities，返回 dict 便于列表渲染时 O(1) 取 name/currency。

    用 row-value IN（平面表达式，SQLite 3.15+）而非 N 个 OR 子句——
    OR 拼出的左深表达式树在 key 数 >1000 时会触发
    'Expression tree is too large (maximum depth 1000)'（爬虫全量补抓后必现）。
    分批查询同时规避老版本 SQLite 999 变量上限。
    """
    keys = list(set(keys))
    if not keys:
        return {}
    result: dict[tuple[str, str], Security] = {}
    batch_size = 400
    for start in range(0, len(keys), batch_size):
        batch = keys[start:start + batch_size]
        placeholders = ",".join(f"(:m{i},:c{i})" for i in range(len(batch)))
        params: dict = {}
        for i, (m, c) in enumerate(batch):
            params[f"m{i}"] = m
            params[f"c{i}"] = c
        sql = f"SELECT * FROM securities WHERE (market, code) IN ({placeholders})"
        for r in session.execute(text(sql), params).all():
            sec = Security.model_validate(dict(r._mapping))
            result[(sec.market, sec.code)] = sec
    return result


def update_price(session: Session, market: str, code: str, price: float) -> None:
    """更新某只股票的最新价。"""
    session.execute(text(
        "UPDATE securities SET latest_price=:p, price_updated_at=:ts "
        "WHERE market=:m AND code=:c"
    ), {"p": price, "ts": now_str(), "m": market, "c": code})


# ──────────────────────── 派息频率推断 ────────────────────────

# 典型年度分红次数 → 频率（取各完整年份次数的中位数后落桶）
# monthly REIT/基金 ~12 次；季派 ~4；半年派 ~2；年派 1
def infer_freq(session: Session, market: str, code: str) -> str | None:
    """按历年分红预案次数推断派息频率。

    统计口径：非 rejected、非 forecast（推算预案不能反过来作为推断证据）、
    且派息日/除权日/登记日至少有一个的预案，按年份分组计数。
    当前年份数据不完整，若存在历史完整年份则剔除当前年；取年份计数的中位数。

    返回 monthly/quarterly/semi_annual/annual；无可参考日期数据时返回 None
    （调用方保持原值 unknown）。
    """
    rows = session.execute(text(
        "SELECT substr(COALESCE(pay_date, ex_date, record_date), 1, 4) AS yr, COUNT(*) "
        "FROM dividend_schedules "
        "WHERE market=:m AND code=:c "
        "AND status != 'rejected' AND source != 'forecast' "
        "AND COALESCE(pay_date, ex_date, record_date) IS NOT NULL "
        "GROUP BY yr"
    ), {"m": market, "c": code}).all()
    if not rows:
        return None
    cur_year = today_str()[:4]
    counts = [int(r[1]) for r in rows if r[0] != cur_year]
    if not counts:  # 只有当年数据，无法剔除，直接用
        counts = [int(r[1]) for r in rows]
    counts.sort()
    median = counts[len(counts) // 2]
    if median >= 9:
        return "monthly"
    if median >= 4:
        return "quarterly"
    if median >= 2:
        return "semi_annual"
    return "annual"


def refresh_security_freq(session: Session, market: str, code: str,
                          commit: bool = True) -> bool:
    """重新推断单只标的的 freq 并在变化时写回。返回是否发生更新。"""
    freq = infer_freq(session, market, code)
    if freq is None:
        return False
    sec = get_security(session, market, code)
    if sec is None or sec.freq == freq:
        return False
    session.execute(text(
        "UPDATE securities SET freq=:f, updated_at=:ts "
        "WHERE market=:m AND code=:c"
    ), {"f": freq, "ts": now_str(), "m": market, "c": code})
    if commit:
        session.commit()
    return True


def refresh_all_freq(session: Session, commit: bool = True) -> int:
    """全量重算所有标的的派息频率，返回更新条数。标的表规模小（仅有分红数据的股票），
    在爬虫批处理结束 / 启动迁移后调用一次即可。"""
    securities = session.exec(select(Security)).all()
    updated = 0
    for sec in securities:
        if refresh_security_freq(session, sec.market, sec.code, commit=False):
            updated += 1
    if updated and commit:
        session.commit()
    return updated
