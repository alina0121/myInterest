"""时间与日期工具（统一本地时区字符串口径，见 docs/02 §约定）。"""
from datetime import date, datetime, timedelta


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return date.today().isoformat()


def add_days(date_iso: str, days: int) -> str:
    return (date.fromisoformat(date_iso) + timedelta(days=days)).isoformat()


def hold_days(from_date: str, to_date: str) -> int:
    return (date.fromisoformat(to_date) - date.fromisoformat(from_date)).days


def days_ago_iso(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()
