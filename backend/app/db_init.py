"""建库初始化：建表 + 种子数据（税率规则/汇率），schema 版本 PRAGMA user_version。"""
from sqlalchemy import text
from sqlmodel import Session, select

from .database import engine
from .models import ExchangeRate, TaxRule
from .services.fx_service import fetch_latest_rate

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

SCHEMA_VERSION = 1


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
        seed_tax_rules(session)
        if seed_fx:
            seed_rates_if_empty(session)
