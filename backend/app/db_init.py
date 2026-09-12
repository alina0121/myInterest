"""建库初始化：建表 + 种子数据（税率规则/汇率），schema 版本 PRAGMA user_version。"""
import logging

from sqlalchemy import text
from sqlmodel import Session, select

from .database import engine
from .models import ExchangeRate, TaxRule
from .services.fx_service import fetch_latest_rate
from .utils.timeutil import now_str

log = logging.getLogger("xi.db_init")

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

SCHEMA_VERSION = 6


def _table_columns(session: Session, table: str) -> set[str]:
    return {r[1] for r in session.execute(text(f"PRAGMA table_info({table})")).all()}


def drop_legacy_schedule_columns(session: Session) -> None:
    """v4：securities 分表后，旧库 dividend_schedules 遗留的 name/currency 列
    仍是 NOT NULL，而 ORM 新插入不再提供这两列 → NOT NULL constraint failed，
    爬虫/手工录入整批插入失败回滚（新库无这两列，函数空跑）。

    必须在 migrate_securities 反填 securities 之后执行（反填 SELECT 依赖旧列）。
    SQLite 3.35+（Python 3.9 自带版本起）支持 ALTER TABLE DROP COLUMN；
    这两列不在任何索引/唯一约束中，可直接删。幂等：列不存在即跳过。
    """
    cols = _table_columns(session, "dividend_schedules")
    dropped = []
    for col in ("name", "currency"):
        if col in cols:
            session.execute(text(f"ALTER TABLE dividend_schedules DROP COLUMN {col}"))
            dropped.append(col)
    if dropped:
        session.commit()
        log.info("dropped legacy columns from dividend_schedules: %s", dropped)


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


def migrate_crawl_enabled(session: Session) -> None:
    """v5：securities 表新增 crawl_enabled 字段（爬虫白名单标记）。

    新库 create_all 已带该列；旧库用 ALTER TABLE 补列，默认 0（不爬）。
    幂等：列已存在即跳过。
    """
    if "crawl_enabled" not in _table_columns(session, "securities"):
        session.exec(text("ALTER TABLE securities ADD COLUMN crawl_enabled INTEGER DEFAULT 0"))
        session.commit()
        log.info("added column crawl_enabled to securities")


def migrate_dashboard_metrics(session: Session) -> None:
    """v6：user_settings 表新增 dashboard_metrics 字段（首页指标偏好 JSON）。

    新库 create_all 已带该列；旧库用 ALTER TABLE 补列，默认 NULL。
    幂等：列已存在即跳过。
    """
    if "dashboard_metrics" not in _table_columns(session, "user_settings"):
        session.exec(text("ALTER TABLE user_settings ADD COLUMN dashboard_metrics TEXT"))
        session.commit()
        log.info("added column dashboard_metrics to user_settings")


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
        # v4：先反填后删列，顺序不可换（反填 SELECT 依赖旧 name/currency）
        drop_legacy_schedule_columns(session)
        # v5：securities 加 crawl_enabled 列（爬虫白名单）
        migrate_crawl_enabled(session)
        # v6：user_settings 加 dashboard_metrics 列（首页指标偏好）
        migrate_dashboard_metrics(session)
        # 升级库：按已有分红历史回填 securities.freq（新库为空，立即返回）
        from .services import security_service
        security_service.refresh_all_freq(session)
        seed_tax_rules(session)
        if seed_fx:
            seed_rates_if_empty(session)
