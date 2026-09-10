"""时间与日期工具（统一本地时区字符串口径，见 docs/02 §约定）。"""
from datetime import date, datetime, timedelta


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return date.today().isoformat()


def add_days(date_iso: str, days: int) -> str:
    return (date.fromisoformat(date_iso) + timedelta(days=days)).isoformat()


def hold_days(from_date: str, to_date: str) -> int:
    """持有天数（自然日）= to_date - from_date。

    分红计税口径：from=批次买入日，to=股权登记日。
    例：买入 2026-01-01、登记日 2026-02-05 → 持有 35 天，落在 A股「1个月~1年」档（10%）。
    """
    return (date.fromisoformat(to_date) - date.fromisoformat(from_date)).days


def days_ago_iso(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()
