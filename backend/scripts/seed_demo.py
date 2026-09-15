"""演示数据种子脚本（可重复运行）——v0.3 纯预案模式。

造数据流程：
1. 创建/复用 demo 用户（用户名 demo，密码 demo123456）
2. 10 只股票多市场持仓 + 多批次买入（A 股 5 + 美股 3 + 港股 1 + 基金 1）
3. 直接写 dividend_schedules（status=published），无需手动造 Dividend 记录
   —— v0.3 分红实时计算接口会自动从预案 + 持仓批次派生。

用法：
    cd backend
    python -m scripts.seed_demo            # 离线模式（不调用爬虫）
    python -m scripts.seed_demo --crawl   # 同时触发一次爬虫

幂等：重复运行前会清空 demo 用户的 holdings/lots 及相关预案，再重建。
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database import engine
from app.db_init import init_db
from app.models import DividendSchedule, Holding, Lot, User
from app.services.crawler_service import run_crawl
from app.services.security_service import upsert_security
from app.utils.security import hash_password

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123456"

PORTFOLIO = [
    {
        "market": "a_share", "code": "600519", "name": "贵州茅台",
        "currency": "CNY", "freq": "annual", "account": "华泰证券",
        "lots": [
            ("2022-03-15", "buy", 60, 1580.0, 5.0),
            ("2023-09-20", "buy", 40, 1600.0, 5.0),
        ],
        "schedules": [
            ("2024-06-19", "2024-06-18", "2024-06-20", 25.91, "2023 年度分红"),
            ("2025-06-19", "2025-06-18", "2025-06-20", 30.00, "2024 年度分红"),
        ],
    },
    {
        "market": "a_share", "code": "601398", "name": "工商银行",
        "currency": "CNY", "freq": "semi_annual", "account": "华泰证券",
        "lots": [
            ("2023-03-15", "buy", 3000, 4.50, 5.0),
            ("2024-01-10", "buy", 2000, 4.80, 5.0),
        ],
        "schedules": [
            ("2024-07-16", "2024-07-15", "2024-07-17", 0.3064, "2024 中期分红"),
            ("2025-07-16", "2025-07-15", "2025-07-17", 0.3334, "2025 中期分红"),
        ],
    },
    {
        "market": "a_share", "code": "601088", "name": "中国神华",
        "currency": "CNY", "freq": "annual", "account": "中信证券",
        "lots": [
            ("2023-05-10", "buy", 2000, 28.50, 5.0),
            ("2024-02-15", "buy", 1000, 32.00, 5.0),
        ],
        "schedules": [
            ("2025-06-28", "2025-06-27", "2025-06-30", 2.55, "2024 年度分红"),
        ],
    },
    {
        "market": "a_share", "code": "600036", "name": "招商银行",
        "currency": "CNY", "freq": "semi_annual", "account": "华泰证券",
        "lots": [
            ("2022-11-20", "buy", 1000, 42.00, 5.0),
            ("2024-03-10", "buy", 500, 38.50, 5.0),
        ],
        "schedules": [
            ("2024-07-12", "2024-07-11", "2024-07-12", 1.98, "2024 中期分红"),
            ("2025-07-12", "2025-07-11", "2025-07-12", 2.10, "2025 中期分红"),
        ],
    },
    {
        "market": "a_share", "code": "600900", "name": "长江电力",
        "currency": "CNY", "freq": "annual", "account": "中信证券",
        "lots": [
            ("2023-07-18", "buy", 3000, 22.00, 5.0),
        ],
        "schedules": [
            ("2025-07-18", "2025-07-17", "2025-07-18", 0.85, "2024 年度分红"),
        ],
    },
    {
        "market": "us_stock", "code": "AAPL", "name": "Apple",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛",
        "lots": [
            ("2022-08-15", "buy", 50, 165.0, 1.0),
            ("2023-04-10", "buy", 30, 165.0, 1.0),
        ],
        "schedules": [
            ("2024-08-12", "2024-08-12", "2024-08-15", 0.25, "Q3 季度分红"),
            ("2025-05-12", "2025-05-12", "2025-05-15", 0.26, "2025 Q2 分红"),
            ("2025-08-11", "2025-08-11", "2025-08-14", 0.26, "2025 Q3 分红"),
        ],
    },
    {
        "market": "us_stock", "code": "MSFT", "name": "Microsoft",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛",
        "lots": [
            ("2023-01-20", "buy", 30, 240.0, 1.0),
            ("2024-08-01", "buy", 20, 420.0, 1.0),
        ],
        "schedules": [
            ("2024-08-15", "2024-08-15", "2024-09-10", 0.75, "Q4 季度分红"),
            ("2025-05-15", "2025-05-15", "2025-06-10", 0.83, "2025 Q2 分红"),
            ("2025-08-14", "2025-08-14", "2025-09-10", 0.83, "2025 Q3 分红"),
        ],
    },
    {
        "market": "us_stock", "code": "KO", "name": "Coca-Cola",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛",
        "lots": [
            ("2022-06-10", "buy", 200, 60.0, 1.0),
            ("2024-01-15", "buy", 100, 58.0, 1.0),
        ],
        "schedules": [
            ("2024-06-28", "2024-06-28", "2024-07-01", 0.485, "2024 Q2 分红"),
            ("2025-06-13", "2025-06-13", "2025-06-16", 0.51, "2025 Q2 分红"),
        ],
    },
    {
        "market": "hk_stock", "code": "00700", "name": "腾讯控股",
        "currency": "HKD", "freq": "quarterly", "account": "富途牛牛",
        "lots": [
            ("2022-09-20", "buy", 200, 320.0, 50.0),
            ("2024-04-15", "buy", 100, 380.0, 50.0),
        ],
        "schedules": [
            ("2024-05-16", "2024-05-16", "2024-05-17", 3.40, "Q1 季度分红"),
            ("2025-05-16", "2025-05-16", "2025-05-17", 4.25, "2025 Q1 分红"),
        ],
    },
    {
        "market": "fund", "code": "005827", "name": "易方达蓝筹",
        "currency": "CNY", "freq": "annual", "account": "蚂蚁基金",
        "lots": [
            ("2023-02-10", "buy", 10000, 2.50, 0.0),
            ("2024-03-05", "buy", 5000, 2.20, 0.0),
        ],
        "schedules": [
            ("2024-08-20", "2024-08-20", "2024-08-21", 0.092, "2023 年度分红"),
            ("2025-08-20", "2025-08-20", "2025-08-21", 0.10, "2024 年度分红"),
        ],
    },
]

PENDING_SCHEDULES = [
    ("a_share", "601398", "工商银行", "2027-01-08", "2027-01-07", "2027-01-08",
     0.3800, "CNY", "crawler", 0.95, "2026 年末期分红预案"),
    ("a_share", "601088", "中国神华", "2027-06-28", "2027-06-27", "2027-06-30",
     2.80, "CNY", "crawler", 0.92, "2026 年度分红预案"),
    ("a_share", "600036", "招商银行", "2027-07-12", "2027-07-11", "2027-07-12",
     2.20, "CNY", "crawler", 0.90, "2026 中期分红预案"),
    ("a_share", "600900", "长江电力", "2027-07-18", "2027-07-17", "2027-07-18",
     0.95, "CNY", "manual", 0.60, "2026 年度分红预案（待公告）"),
    ("us_stock", "AAPL", "Apple", "2026-11-09", "2026-11-09", "2026-11-12",
     0.27, "USD", "crawler", 0.92, "2026 Q4 季度分红预案"),
    ("us_stock", "MSFT", "Microsoft", "2026-11-19", "2026-11-19", "2026-12-10",
     0.92, "USD", "crawler", 0.92, "2026 Q1 季度分红预案"),
    ("us_stock", "KO", "Coca-Cola", "2026-06-26", "2026-06-26", "2026-06-29",
     0.53, "USD", "crawler", 0.88, "2026 Q2 季度分红预案"),
    ("hk_stock", "00700", "腾讯控股", "2026-05-15", "2026-05-15", "2026-05-16",
     4.50, "HKD", "crawler", 0.90, "2026 Q1 季度分红预案"),
    ("fund", "005827", "易方达蓝筹", "2027-08-20", "2027-08-20", "2027-08-21",
     0.11, "CNY", "manual", 0.60, "2026 年度分红预案（待公告）"),
]


def get_or_create_demo_user(session: Session) -> User:
    u = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
    if u:
        return u
    u = User(username=DEMO_USERNAME, email="demo@xi.com",
             password_hash=hash_password(DEMO_PASSWORD), nickname="演示账户", role="user")
    session.add(u)
    session.commit()
    session.refresh(u)
    print(f"  ✓ 创建 demo 用户 (id={u.id})")
    return u


def clean_demo_data(session: Session, user: User) -> None:
    """清空 demo 用户已有的 holdings/lots，以及与之匹配的预案。"""
    h_ids = [h.id for h in session.exec(select(Holding)
                                         .where(Holding.user_id == user.id)).all()]
    if h_ids:
        # 反向删：lots → holdings
        for l in session.exec(select(Lot).where(Lot.holding_id.in_(h_ids))).all():
            session.delete(l)
        session.commit()
        for h in session.exec(select(Holding).where(Holding.id.in_(h_ids))).all():
            session.delete(h)
        session.commit()
        print(f"  ✓ 清理旧数据：{len(h_ids)} 个持仓")

    # 清空 demo 相关预案（market+code 匹配 PORTFOLIO 里的标的，status 允许任何）
    for spec in PORTFOLIO:
        for sch in session.exec(select(DividendSchedule).where(
            DividendSchedule.market == spec["market"],
            DividendSchedule.code == spec["code"],
        )).all():
            session.delete(sch)
    # 清空 PENDING_SCHEDULES 里的标的（无论归属）
    for m, c, *_ in PENDING_SCHEDULES:
        for sch in session.exec(select(DividendSchedule).where(
            DividendSchedule.market == m, DividendSchedule.code == c)).all():
            session.delete(sch)
    session.commit()


def create_holding_with_lots(session: Session, user: User, spec: dict) -> Holding:
    h = Holding(user_id=user.id, market=spec["market"], code=spec["code"],
                name=spec["name"], currency=spec["currency"],
                account=spec["account"], freq=spec["freq"], note=spec.get("note", ""))
    session.add(h)
    session.flush()
    for trade_date, direction, shares, price, fee in spec["lots"]:
        session.add(Lot(user_id=user.id, holding_id=h.id,
                        trade_date=trade_date, direction=direction,
                        shares=shares, price=price, fee=fee))
    session.commit()
    session.refresh(h)
    # 确保 securities 表里有这条（爬虫没跑时也能显示 name）
    upsert_security(session, h.market, h.code, h.name, h.currency)
    session.commit()
    return h


def create_published_schedules(session: Session, spec: dict) -> int:
    """为持仓造已发布预案（v0.3 纯预案模式，分红查询实时派生）。"""
    n = 0
    for ex_date, record_date, pay_date, dps, note in spec["schedules"]:
        # 幂等：同 (market, code, ex_date) 已存在则跳过
        exists = session.exec(select(DividendSchedule).where(
            DividendSchedule.market == spec["market"],
            DividendSchedule.code == spec["code"],
            DividendSchedule.ex_date == ex_date,
        )).first()
        if exists:
            continue
        session.add(DividendSchedule(
            market=spec["market"], code=spec["code"],
            ex_date=ex_date, record_date=record_date, pay_date=pay_date,
            dps=dps, currency=spec["currency"], div_type="cash",
            source="manual", confidence=1.0, status="published",
            raw_title=f"demo seed: {spec['name']} {note}",
        ))
        n += 1
    session.commit()
    return n


def create_pending_schedules(session: Session) -> int:
    n = 0
    for (market, code, name, ex_date, rec_date, pay_date, dps,
         currency, source, confidence, title) in PENDING_SCHEDULES:
        exists = session.exec(select(DividendSchedule).where(
            DividendSchedule.market == market,
            DividendSchedule.code == code,
            DividendSchedule.ex_date == ex_date,
        )).first()
        if exists:
            continue
        session.add(DividendSchedule(
            market=market, code=code, name=name,
            ex_date=ex_date, record_date=rec_date, pay_date=pay_date,
            dps=dps, currency=currency, div_type="cash",
            source=source, confidence=confidence,
            status="pending", raw_title=title,
        ))
        n += 1
    session.commit()
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="造演示数据")
    parser.add_argument("--crawl", action="store_true",
                        help="造完数据后立即触发一次爬虫")
    args = parser.parse_args()

    os.environ.setdefault("XI_CRAWL_OFFLINE", "1")

    print("=== 息计演示数据种子脚本（v0.3 纯预案模式）===")
    init_db(seed_fx=False)
    print("✓ 数据库初始化完成（税率规则已 seed）")

    with Session(engine) as session:
        user = get_or_create_demo_user(session)
        clean_demo_data(session, user)

        print(f"\n>>> 为 {user.username} 创建 10 只股票多市场持仓与预案...")
        total_h, total_l, total_s = 0, 0, 0
        for spec in PORTFOLIO:
            h = create_holding_with_lots(session, user, spec)
            total_h += 1
            total_l += len(spec["lots"])
            ns = create_published_schedules(session, spec)
            total_s += ns
            print(f"  ✓ {spec['market']:>9} {spec['code']:<8} {spec['name']:<12}"
                  f"  批次 {len(spec['lots'])} · 预案 {ns}")
        print(f"合计：持仓 {total_h} · 批次 {total_l} · 已发布预案 {total_s}")

        print("\n>>> 写入待确认预案（pending schedules）...")
        np = create_pending_schedules(session)
        print(f"  ✓ 新增 {np} 条 pending 预案")

    if args.crawl:
        os.environ.pop("XI_CRAWL_OFFLINE", None)
        print("\n>>> 触发爬虫...")
        with Session(engine) as session:
            r = run_crawl(session)
            print(f"  fetched={r.get('fetched')} new_pending={r.get('new_pending')}")

    print("\n✅ 完成。可用 demo / demo123456 登录，分红数据由预案 + 持仓实时派生。")


if __name__ == "__main__":
    main()
