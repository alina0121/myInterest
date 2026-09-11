"""建库初始化：建表 + 种子数据（税率规则/汇率），schema 版本 PRAGMA user_version。"""
from sqlalchemy import text
from sqlmodel import Session, select

from .database import engine
from .models import ExchangeRate, TaxRule
from .services.fx_service import fetch_latest_rate
from .utils.timeutil import now_str

TAX_RULE_SEEDS = [
    # (market, condition, rate, hold_min_days, hold_max_days, description)
    ("a_share", "持股 > 1 年", 0.00, 366, None, "长期持有免税（红利所得暂免）"),
    ("a_share", "持股 1 个月 ~ 1 年", 0.10, 31, 365, "派息时暂扣，卖出时补扣差额"),
    ("a_share", "持股 ≤ 1 个月", 0.20, 0, 30, "全额计税"),
    ("us_stock", "W-8BEN 中国居民", 0.10, None, None, "券商代扣预提税"),
    ("hk_stock", "港股通内地个人", 0.20, None, None, "H股 10% + 红利税 10%，中登代扣"),
    ("fund", "公募基金分红", 0.00, None, None, "个人投资者暂免征收"),
    ("bond", "债券利息", 0.00, None, None, "个人投资者暂免征收"),
]

SCHEMA_VERSION = 3


def migrate_securities(session: Session) -> None:
    """从旧 dividend_schedules 反填 securities 表，并补上 security_id 外键。

    兼容两种库：
    - 旧库：dividend_schedules 仍带 name/currency 列，用原始列反填 securities；
    - 新库：create_all 已建 securities，无需反填。
    """
    # 旧库补列（SQLite 不支持 IF NOT EXISTS ADD COLUMN，靠异常吞掉重复执行）
    try:
        session.exec(text("ALTER TABLE dividend_schedules ADD COLUMN security_id INTEGER"))
    except Exception:
        pass
    # 反填 securities：从 dividend_schedules 的旧列 name/currency 取（若存在）
    # 新库这两列不存在，SELECT 会失败 → 跳过反填（create_all 已建空 securities）
    try:
        rows = session.exec(text(
            "SELECT DISTINCT market, code, name, currency FROM dividend_schedules"
        )).all()
        for r in rows:
            m, c, n, cur = r[0], r[1], r[2], r[3] or "CNY"
            session.execute(text(
                "INSERT OR IGNORE INTO securities (market, code, name, currency, freq, created_at, updated_at) "
                "VALUES (:m, :c, :n, :cur, 'unknown', :ts, :ts)"
            ), {"m": m, "c": c, "n": n or c, "cur": cur, "ts": now_str()})
        # 回填 security_id
        session.exec(text(
            "UPDATE dividend_schedules SET security_id = ("
            "  SELECT id FROM securities WHERE securities.market = dividend_schedules.market"
            "  AND securities.code = dividend_schedules.code"
            ")"
        ))
        session.commit()
    except Exception:
        session.rollback()


def create_indexes(session: Session) -> None:
    """SQLModel 无法表达的部分唯一索引（docs/02 §6 已发布预案防重）。"""
    session.exec(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_sch_published "
        "ON dividend_schedules(market, code, ex_date) WHERE status = 'published'"))
    session.commit()


def seed_tax_rules(session: Session) -> None:
    if session.exec(select(TaxRule)).first() is None:
        for market, cond, rate, lo, hi, desc in TAX_RULE_SEEDS:
            session.add(TaxRule(market=market, condition=cond, rate=rate,
                                hold_min_days=lo, hold_max_days=hi, description=desc))
        session.commit()


def seed_rates_if_empty(session: Session) -> None:
    """离线或失败时静默跳过，运行时 fx_service 有兜底值。"""
    if session.exec(select(ExchangeRate)).first() is not None:
        return
    from datetime import date
    today = date.today().isoformat()
    for base in ("USD", "HKD"):
        rate = fetch_latest_rate(base)
        if rate:
            session.add(ExchangeRate(base=base, quote="CNY", rate=rate,
                                     rate_date=today, source="frankfurter"))
    session.commit()


def init_db(seed_fx: bool = True) -> None:
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.exec(text(f"PRAGMA user_version={SCHEMA_VERSION}"))
        session.commit()
        create_indexes(session)
        migrate_securities(session)
        # 升级库：按已有分红历史回填 securities.freq（新库为空，立即返回）
        from .services import security_service
        security_service.refresh_all_freq(session)
        seed_tax_rules(session)
        if seed_fx:
            seed_rates_if_empty(session)
