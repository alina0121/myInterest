"""演示数据种子脚本（可重复运行）——v0.3 纯预案模式。

造数据流程：
1. 创建/复用 demo 用户（用户名 demo，密码登录已下线，登录走邮箱验证码 demo@xi.com）
2. 17 只多市场持仓 + 多批次买入（A 股 5 + 美股 5 + 港股 3 + 基金 3 + 债券 1），
   并写入 securities.latest_price 保证市值/盈亏有数
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
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select

from app.database import engine
from app.db_init import init_db
from app.models import DividendSchedule, Holding, Lot, Security, User
from app.services.crawler_service import run_crawl
from app.services.security_service import upsert_security
from app.utils.security import hash_password

DEMO_USERNAME = "demo"
# 密码登录体系已下线：password_hash 仅存随机占位值（与 wx-login 建号一致）


def _monthly(start=(2025, 4), end=(2026, 9), rate=(2025, 0.264), rate2=(2026, 0.268)):
    """ Realty Income 月度分红：ex=月初、pay=当月 15 日，按年分档 dps。"""
    rates = {rate[0]: rate[1], rate2[0]: rate2[1]}
    rows, y, m = [], start[0], start[1]
    while (y, m) <= end:
        rows.append((f"{y}-{m:02d}-01", f"{y}-{m:02d}-01", f"{y}-{m:02d}-15",
                     rates[y], f"{y} 年 {m} 月月度分红"))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return rows


PORTFOLIO = [
    {
        "market": "a_share", "code": "600519", "name": "贵州茅台",
        "currency": "CNY", "freq": "annual", "account": "华泰证券", "price": 1520.0,
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
        "currency": "CNY", "freq": "semi_annual", "account": "华泰证券", "price": 6.90,
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
        "currency": "CNY", "freq": "annual", "account": "中信证券", "price": 39.5,
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
        "currency": "CNY", "freq": "semi_annual", "account": "华泰证券", "price": 48.5,
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
        "currency": "CNY", "freq": "annual", "account": "中信证券", "price": 28.6,
        "lots": [
            ("2023-07-18", "buy", 3000, 22.00, 5.0),
        ],
        "schedules": [
            ("2025-07-18", "2025-07-17", "2025-07-18", 0.85, "2024 年度分红"),
        ],
    },
    {
        "market": "us_stock", "code": "AAPL", "name": "Apple",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛", "price": 255.0,
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
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛", "price": 505.0,
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
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛", "price": 70.5,
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
        "market": "us_stock", "code": "O", "name": "Realty Income",
        "currency": "USD", "freq": "monthly", "account": "长桥证券", "price": 58.6,
        "lots": [
            ("2024-09-10", "buy", 300, 57.0, 1.0),
        ],
        "schedules": _monthly(),  # 2025-04 ~ 2026-09 每月一派，月历"每月有点"效果
    },
    {
        "market": "us_stock", "code": "PG", "name": "P&G 宝洁",
        "currency": "USD", "freq": "quarterly", "account": "长桥证券", "price": 168.0,
        "lots": [
            ("2023-10-08", "buy", 60, 150.0, 1.0),
        ],
        "schedules": [
            ("2026-01-23", "2026-01-22", "2026-02-13", 1.0413, "2026 Q2 分红"),
            ("2026-04-24", "2026-04-23", "2026-05-15", 1.0568, "2026 Q3 分红"),
            ("2026-07-24", "2026-07-23", "2026-08-14", 1.0568, "2026 Q4 分红"),
        ],
    },
    {
        "market": "hk_stock", "code": "00700", "name": "腾讯控股",
        "currency": "HKD", "freq": "quarterly", "account": "富途牛牛", "price": 585.0,
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
        "market": "hk_stock", "code": "00005", "name": "汇丰控股",
        "currency": "HKD", "freq": "quarterly", "account": "富途牛牛", "price": 78.5,
        "lots": [
            ("2023-06-15", "buy", 400, 62.0, 50.0),
            ("2025-02-10", "buy", 200, 75.0, 50.0),
        ],
        "schedules": [
            ("2025-09-18", "2025-09-18", "2025-09-25", 0.31, "2025 第三次中期股息"),
            ("2026-03-19", "2026-03-19", "2026-03-26", 0.31, "2026 第一次中期股息"),
            ("2026-06-18", "2026-06-18", "2026-06-25", 0.31, "2026 第二次中期股息"),
        ],
    },
    {
        "market": "hk_stock", "code": "00883", "name": "中国海洋石油",
        "currency": "HKD", "freq": "semi_annual", "account": "富途牛牛", "price": 19.8,
        "lots": [
            ("2024-05-20", "buy", 2000, 17.5, 50.0),
        ],
        "schedules": [
            ("2025-09-04", "2025-09-03", "2025-09-11", 0.74, "2025 中期股息"),
            ("2026-05-27", "2026-05-26", "2026-06-25", 0.70, "2025 末期股息"),
            ("2026-09-10", "2026-09-09", "2026-09-26", 0.74, "2026 中期股息"),
        ],
    },
    {
        "market": "fund", "code": "005827", "name": "易方达蓝筹",
        "currency": "CNY", "freq": "annual", "account": "蚂蚁基金", "price": 2.85,
        "lots": [
            ("2023-02-10", "buy", 10000, 2.50, 0.0),
            ("2024-03-05", "buy", 5000, 2.20, 0.0),
        ],
        "schedules": [
            ("2024-08-20", "2024-08-20", "2024-08-21", 0.092, "2023 年度分红"),
            ("2025-08-20", "2025-08-20", "2025-08-21", 0.10, "2024 年度分红"),
        ],
    },
    {
        "market": "fund", "code": "110022", "name": "易方达消费行业",
        "currency": "CNY", "freq": "annual", "account": "蚂蚁基金", "price": 6.85,
        "lots": [
            ("2023-04-12", "buy", 5000, 5.20, 0.0),
        ],
        "schedules": [
            ("2026-01-15", "2026-01-15", "2026-01-16", 0.25, "2025 年度分红"),
        ],
    },
    {
        "market": "fund", "code": "270048", "name": "广发纯债债券C",
        "currency": "CNY", "freq": "quarterly", "account": "天天基金", "price": 1.12,
        "lots": [
            ("2024-06-18", "buy", 20000, 1.10, 0.0),
        ],
        "schedules": [
            ("2026-02-10", "2026-02-10", "2026-02-11", 0.035, "2025 四季度收益分配"),
            ("2026-05-12", "2026-05-12", "2026-05-13", 0.032, "2026 一季度收益分配"),
            ("2026-08-11", "2026-08-11", "2026-08-12", 0.033, "2026 二季度收益分配"),
        ],
    },
    {
        "market": "bond", "code": "019542", "name": "24国债12",
        "currency": "CNY", "freq": "annual", "account": "招商银行App", "price": 100.5,
        "lots": [
            ("2023-11-08", "buy", 1000, 100.2, 0.0),
        ],
        "schedules": [
            ("2026-03-20", "2026-03-19", "2026-03-21", 2.29, "2026 年度付息"),
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
    ("hk_stock", "00883", "中国海洋石油", "2027-05-26", "2027-05-25", "2027-06-24",
     0.72, "HKD", "crawler", 0.90, "2026 末期股息预案"),
    ("us_stock", "PG", "P&G 宝洁", "2027-01-22", "2027-01-21", "2027-02-12",
     1.09, "USD", "crawler", 0.90, "2027 Q2 季度分红预案"),
    ("fund", "110022", "易方达消费行业", "2027-01-15", "2027-01-15", "2027-01-16",
     0.28, "CNY", "manual", 0.60, "2026 年度分红预案（待公告）"),
    ("bond", "019542", "24国债12", "2027-03-20", "2027-03-19", "2027-03-21",
     2.29, "CNY", "manual", 0.60, "2027 年度付息预案（待公告）"),
]


# 已发布且「即将到账」的预案（相对 2026 年 10-11 月），让 upcoming/月度统计有内容；
# 另含 2 条 2026 年内已派发的，补当年已收分红
UPCOMING_PUBLISHED = [
    # (market, code, ex_date, record_date, pay_date, dps, note)
    ("a_share", "600036", "2026-10-23", "2026-10-22", "2026-10-28", 1.20, "2026 三季度分红"),
    ("a_share", "601088", "2026-11-06", "2026-11-05", "2026-11-13", 2.26, "2026 中期分红"),
    ("hk_stock", "00700", "2026-11-13", "2026-11-12", "2026-11-20", 4.50, "2026 三季度分红"),
    ("us_stock", "KO", "2026-12-04", "2026-12-04", "2026-12-15", 0.51, "2026 Q4 分红"),
    ("a_share", "600900", "2026-07-16", "2026-07-15", "2026-07-20", 0.85, "2025 年度分红"),
    ("a_share", "601398", "2026-05-12", "2026-05-11", "2026-05-15", 0.30, "2025 年度分红"),
    ("us_stock", "O", "2026-11-02", "2026-11-02", "2026-11-13", 0.274, "2026 年 11 月月度分红"),
    ("us_stock", "O", "2026-12-01", "2026-12-01", "2026-12-15", 0.274, "2026 年 12 月月度分红"),
    ("us_stock", "PG", "2026-10-23", "2026-10-23", "2026-11-16", 1.0719, "2026 Q4 季度分红"),
    ("hk_stock", "00005", "2026-11-20", "2026-11-20", "2026-11-27", 0.31, "2026 第三次中期股息"),
    ("fund", "270048", "2026-11-10", "2026-11-10", "2026-11-11", 0.031, "2026 三季度收益分配"),
]


def get_or_create_demo_user(session: Session) -> User:
    u = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
    if u:
        return u
    u = User(username=DEMO_USERNAME, email="demo@xi.com",
             password_hash=hash_password(secrets.token_urlsafe(16)),
             nickname="演示账户", role="user")
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
    # 确保 securities 表里有这条（爬虫没跑时也能显示 name），并写入演示现价
    sec = upsert_security(session, h.market, h.code, h.name, h.currency)
    if spec.get("price"):
        sec.latest_price = spec["price"]
        h.current_price = spec["price"]  # 持仓快照同步，避免依赖价格任务
    session.commit()
    session.refresh(h)
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


def create_upcoming_published(session: Session) -> int:
    """写入即将到账/当年已派的已发布预案（currency 按持仓本币）。"""
    n = 0
    for market, code, ex_date, rec_date, pay_date, dps, note in UPCOMING_PUBLISHED:
        exists = session.exec(select(DividendSchedule).where(
            DividendSchedule.market == market,
            DividendSchedule.code == code,
            DividendSchedule.ex_date == ex_date,
        )).first()
        if exists:
            continue
        spec = next(s for s in PORTFOLIO if s["market"] == market and s["code"] == code)
        session.add(DividendSchedule(
            market=market, code=code, name=spec["name"],
            ex_date=ex_date, record_date=rec_date, pay_date=pay_date,
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

        print(f"\n>>> 为 {user.username} 创建 {len(PORTFOLIO)} 只多市场持仓与预案...")
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

        print("\n>>> 写入即将到账/当年已派的已发布预案...")
        nu = create_upcoming_published(session)
        print(f"  ✓ 新增 {nu} 条（未来到账 + 当年已派）")

        print("\n>>> 写入待确认预案（pending schedules）...")
        np = create_pending_schedules(session)
        print(f"  ✓ 新增 {np} 条 pending 预案")

    if args.crawl:
        os.environ.pop("XI_CRAWL_OFFLINE", None)
        print("\n>>> 触发爬虫...")
        with Session(engine) as session:
            r = run_crawl(session)
            print(f"  fetched={r.get('fetched')} new_pending={r.get('new_pending')}")

    print("\n✅ 完成。用邮箱验证码登录（demo@xi.com，未配 SMTP 时验证码见后端日志），"
          "分红数据由预案 + 持仓实时派生。")


if __name__ == "__main__":
    main()
