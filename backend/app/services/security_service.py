"""股票基础信息服务（securities 表）。

提供 upsert（幂等写入）与批量查询，供 crawler / admin / user_submit / forecast
在创建 dividend_schedule 前先确保股票基础数据存在。
"""
from typing import Iterable

from sqlalchemy import text
from sqlmodel import Session, select

from ..models import Security
from ..utils.timeutil import now_str


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
    """批量按 (market, code) 查 securities，返回 dict 便于列表渲染时 O(1) 取 name/currency。"""
    keys = list(set(keys))
    if not keys:
        return {}
    clauses = []
    params: dict = {}
    for i, (m, c) in enumerate(keys):
        clauses.append(f"(market=:m{i} AND code=:c{i})")
        params[f"m{i}"] = m
        params[f"c{i}"] = c
    sql = "SELECT * FROM securities WHERE " + " OR ".join(clauses)
    rows = session.execute(text(sql), params).all()
    result: dict[tuple[str, str], Security] = {}
    for r in rows:
        sec = Security.model_validate(dict(r._mapping))
        result[(sec.market, sec.code)] = sec
    return result


def update_price(session: Session, market: str, code: str, price: float) -> None:
    """更新某只股票的最新价。"""
    session.execute(text(
        "UPDATE securities SET latest_price=:p, price_updated_at=:ts "
        "WHERE market=:m AND code=:c"
    ), {"p": price, "ts": now_str(), "m": market, "c": code})
