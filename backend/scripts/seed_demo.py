"""演示数据种子脚本（可重复运行）。

造数据流程：
1. 创建/复用 demo 用户（用户名 demo，密码 demo123456）
2. 多市场持仓 + 多批次买入（A股/美股/港股/基金）
3. 调用 dividend_service.create_dividend 造已到账分红（自动生成批次归属明细）
4. 直接写 dividend_schedules 表造待确认 pending 预案（含美股 Yahoo 爬虫已支持）

用法：
    cd backend
    python -m scripts.seed_demo            # 离线模式（不调用爬虫）
    python -m scripts.seed_demo --crawl   # 同时触发一次爬虫

幂等：重复运行前会清空 demo 用户的 holdings/lots/dividends 及其 pending 预案，再重建。
"""
import argparse
import os
import sys
from pathlib import Path

# 让脚本能 import backend.app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app.database import engine  # noqa: E402
from app.db_init import init_db  # noqa: E402
from app.models import (  # noqa: E402
    Dividend, DividendAllocation, DividendSchedule, Holding, Lot, User,
)
from app.services.dividend_service import create_dividend  # noqa: E402
from app.services.crawler_service import run_crawl  # noqa: E402
from app.utils.security import hash_password  # noqa: E402
from app.utils.timeutil import now_str  # noqa: E402

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123456"

# ---------- 持仓 + 批次定义 ----------
# (market, code, name, currency, freq, account, note, lots[], dividends[])
# lots: [(trade_date, direction, shares, price, fee)]
# dividends: [(ex_date, record_date, pay_date, dps, status, note)]
PORTFOLIO = [
    # A 股：贵州茅台（年派）
    {
        "market": "a_share", "code": "600519", "name": "贵州茅台",
        "currency": "CNY", "freq": "annual", "account": "华泰证券",
        "lots": [
            ("2022-03-15", "buy", 60, 1580.0, 5.0),
            ("2023-09-20", "buy", 40, 1600.0, 5.0),
        ],
        "dividends": [
            ("2024-06-19", "2024-06-18", "2024-06-20", 25.91, "confirmed", "2023 年年度分红"),
        ],
    },
    # A 股：工商银行（半年派）
    {
        "market": "a_share", "code": "601398", "name": "工商银行",
        "currency": "CNY", "freq": "semi_annual", "account": "华泰证券",
        "lots": [
            ("2023-03-15", "buy", 3000, 4.50, 5.0),
        ],
        "dividends": [
            ("2024-07-16", "2024-07-15", "2024-07-17", 0.3064, "confirmed", "2024 中期分红"),
        ],
    },
    # 美股：Apple（季派）
    {
        "market": "us_stock", "code": "AAPL", "name": "Apple",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛",
        "lots": [
            ("2022-08-15", "buy", 50, 165.0, 1.0),
            ("2023-04-10", "buy", 30, 165.0, 1.0),
        ],
        "dividends": [
            ("2024-08-12", "2024-08-12", "2024-08-15", 0.25, "confirmed", "Q3 季度分红"),
        ],
    },
    # 美股：Microsoft（季派）
    {
        "market": "us_stock", "code": "MSFT", "name": "Microsoft",
        "currency": "USD", "freq": "quarterly", "account": "富途牛牛",
        "lots": [
            ("2023-01-20", "buy", 30, 240.0, 1.0),
        ],
        "dividends": [
            ("2024-08-15", "2024-08-15", "2024-09-10", 0.75, "confirmed", "Q4 季度分红"),
        ],
    },
    # 港股：腾讯控股（季派）
    {
        "market": "hk_stock", "code": "00700", "name": "腾讯控股",
        "currency": "HKD", "freq": "quarterly", "account": "富途牛牛",
        "lots": [
            ("2022-09-20", "buy", 200, 320.0, 50.0),
        ],
        "dividends": [
            ("2024-05-16", "2024-05-16", "2024-05-17", 3.40, "confirmed", "Q1 季度分红"),
        ],
    },
    # 基金：易方达蓝筹（年派）
    {
        "market": "fund", "code": "005827", "name": "易方达蓝筹",
        "currency": "CNY", "freq": "annual", "account": "蚂蚁基金",
        "lots": [
            ("2023-02-10", "buy", 10000, 2.50, 0.0),
        ],
        "dividends": [
            ("2024-08-20", "2024-08-20", "2024-08-21", 0.092, "confirmed", "2023 年度分红"),
        ],
    },
]

# ---------- 待确认预案（dividend_schedules, status=pending） ----------
PENDING_SCHEDULES = [
    # A 股
    ("a_share", "601398", "工商银行", "2025-01-08", "2025-01-07", "2025-01-08",
     0.3064, "CNY", "crawler", 0.95, "2024 年末期分红预案"),
    # 美股
    ("us_stock", "AAPL", "Apple", "2024-11-11", "2024-11-11", "2024-11-14",
     0.25, "USD", "crawler", 0.92, "Q4 季度分红预案"),
    ("us_stock", "MSFT", "Microsoft", "2024-11-20", "2024-11-20", "2024-12-10",
     0.83, "USD", "crawler", 0.92, "Q1 季度分红预案"),
    # 港股
    ("hk_stock", "00700", "腾讯控股", "2024-08-16", "2024-08-16", "2024-08-17",
     3.40, "HKD", "crawler", 0.90, "Q2 季度分红预案"),
    # 基金
    ("fund", "005827", "易方达蓝筹", "2025-08-20", "2025-08-20", "2025-08-21",
     0.092, "CNY", "manual", 0.60, "2024 年度分红预案（待公告）"),
]


def get_or_create_demo_user(session: Session) -> User:
    """获取或创建 demo 用户（幂等）。"""
    u = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
    if u:
        return u
    u = User(
        username=DEMO_USERNAME,
        email="demo@xi.com",
        password_hash=hash_password(DEMO_PASSWORD),
        nickname="演示账户",
        role="user",
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    print(f"  ✓ 创建 demo 用户 (id={u.id})")
    return u


def clean_demo_data(session: Session, user: User) -> None:
    """清空 demo 用户已有的业务数据（避免重复运行时唯一索引冲突）。

    严格按依赖反向顺序删除：allocations → dividends → lots → holdings。
    每步独立 commit，规避 SQLAlchemy autoflush 引发的级联 FK 报错。
    """
    h_ids = [h.id for h in session.exec(select(Holding)
                                         .where(Holding.user_id == user.id)).all()]
    if h_ids:
        # 1) 查所有相关 dividends 的 id
        d_ids = [d.id for d in session.exec(select(Dividend)
                                              .where(Dividend.holding_id.in_(h_ids))).all()]
        if d_ids:
            # 2) 删 allocations
            for a in session.exec(select(DividendAllocation)
                                   .where(DividendAllocation.dividend_id.in_(d_ids))).all():
                session.delete(a)
            session.commit()
            # 3) 删 dividends
            for d in session.exec(select(Dividend)
                                   .where(Dividend.id.in_(d_ids))).all():
                session.delete(d)
            session.commit()
        # 4) 删 lots
        for l in session.exec(select(Lot).where(Lot.holding_id.in_(h_ids))).all():
            session.delete(l)
        session.commit()
        # 5) 删 holdings
        for h in session.exec(select(Holding).where(Holding.id.in_(h_ids))).all():
            session.delete(h)
        session.commit()
        print(f"  ✓ 清理旧数据：{len(h_ids)} 个持仓")

    # 清空 pending 预案（保留 published/rejected 的历史）
    pendings = session.exec(select(DividendSchedule)
                            .where(DividendSchedule.status == "pending")).all()
    for s in pendings:
        session.delete(s)
    session.commit()


def create_holding_with_lots(session: Session, user: User, spec: dict) -> Holding:
    """按 spec 创建持仓 + 批次。"""
    h = Holding(
        user_id=user.id,
        market=spec["market"], code=spec["code"], name=spec["name"],
        currency=spec["currency"], account=spec["account"], freq=spec["freq"],
        note=spec.get("note", ""),
    )
    session.add(h)
    session.flush()
    for trade_date, direction, shares, price, fee in spec["lots"]:
        session.add(Lot(
            user_id=user.id, holding_id=h.id,
            trade_date=trade_date, direction=direction,
            shares=shares, price=price, fee=fee,
        ))
    session.commit()
    session.refresh(h)
    return h


def create_dividends_for(session: Session, user: User, holding: Holding, spec: dict) -> int:
    """为持仓造已到账分红，调用 create_dividend 自动生成批次归属。"""
    n = 0
    for ex_date, record_date, pay_date, dps, status, note in spec["dividends"]:
        create_dividend(
            session, user.id, holding,
            ex_date=ex_date, pay_date=pay_date, dps=dps,
            record_date=record_date,
            status=status, source="manual", note=note,
        )
        n += 1
    return n


def create_pending_schedules(session: Session) -> int:
    """写入待确认预案（幂等：跳过已存在的 market+code+ex_date）。"""
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
                        help="造完数据后立即触发一次爬虫（A 股 + 美股）")
    args = parser.parse_args()

    # 离线模式默认开启，避免 init_db 联网拉汇率
    os.environ.setdefault("XI_CRAWL_OFFLINE", "1")

    print("=== 息计演示数据种子脚本 ===")
    init_db(seed_fx=False)
    print("✓ 数据库初始化完成（税率规则已 seed）")

    with Session(engine) as session:
        user = get_or_create_demo_user(session)
        clean_demo_data(session, user)

        print(f"\n>>> 为 {user.username} 创建多市场持仓与分红...")
        total_h, total_l, total_d = 0, 0, 0
        for spec in PORTFOLIO:
            h = create_holding_with_lots(session, user, spec)
            total_h += 1
            total_l += len(spec["lots"])
            nd = create_dividends_for(session, user, h, spec)
            total_d += nd
            print(f"  ✓ {spec['market']:>9} {spec['code']:<8} {spec['name']:<10}"
                  f"  批次 {len(spec['lots'])} · 分红 {nd}")
        print(f"合计：持仓 {total_h} · 批次 {total_l} · 已到账分红 {total_d}")

        print("\n>>> 写入待确认预案（pending schedules）...")
        ns = create_pending_schedules(session)
        print(f"  ✓ 新增 {ns} 条 pending 预案（A 股/美股/港股/基金）")

    # 可选：触发真实爬虫（联网）
    if args.crawl:
        os.environ.pop("XI_CRAWL_OFFLINE", None)
        print("\n>>> 触发爬虫（A 股 + 美股 Yahoo Finance）...")
        with Session(engine) as session:
            r = run_crawl(session)
            print(f"  fetched={r.get('fetched')} new_pending={r.get('new_pending')}"
                  f" message={r.get('message')}")

    print("\n✅ 完成。可用 demo / demo123456 登录前端查看效果。")


if __name__ == "__main__":
    main()
