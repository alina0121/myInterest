"""建库/迁移测试：用独立的临时 sqlite 库模拟旧版本 schema。

不复用 conftest 的测试库（它总是最新 schema），迁移逻辑必须在「旧形状」的库上验证。
"""
import pytest
from sqlalchemy import create_engine, text
from sqlmodel import Session

from app.db_init import drop_legacy_schedule_columns


def test_drop_legacy_schedule_columns(tmp_path):
    """v3→v4：旧库 dividend_schedules 上遗留的 name/currency NOT NULL 列必须被删除，
    使无 name 列的 ORM 风格 INSERT 能成功；函数幂等。"""
    engine = create_engine(f"sqlite:///{tmp_path}/legacy.db")
    with Session(engine) as s:
        # 模拟分表前的旧表：name/currency NOT NULL
        s.exec(text(
            "CREATE TABLE dividend_schedules ("
            "id INTEGER PRIMARY KEY, market VARCHAR NOT NULL, code VARCHAR NOT NULL, "
            "name VARCHAR NOT NULL, ex_date VARCHAR, record_date VARCHAR, pay_date VARCHAR, "
            "dps FLOAT, currency VARCHAR NOT NULL, div_type VARCHAR NOT NULL, "
            "source VARCHAR NOT NULL, confidence FLOAT NOT NULL, status VARCHAR NOT NULL, "
            "submitted_by INTEGER, reviewed_by INTEGER, reviewed_at VARCHAR, "
            "reject_reason VARCHAR, raw_title VARCHAR, created_at VARCHAR NOT NULL)"))
        s.exec(text(
            "INSERT INTO dividend_schedules "
            "(market, code, name, ex_date, dps, currency, div_type, source, confidence, "
            " status, created_at) VALUES "
            "('a_share','600000','浦发银行','2024-06-01',0.32,'CNY','cash','manual',1.0,"
            " 'published','2024-01-01 00:00:00')"))
        s.commit()

        drop_legacy_schedule_columns(s)

        cols = {r[1] for r in s.execute(text("PRAGMA table_info(dividend_schedules)")).all()}
        assert "name" not in cols
        assert "currency" not in cols
        assert {"market", "code", "ex_date", "dps", "status"} <= cols
        # 旧数据保留
        n = s.execute(text("SELECT COUNT(*) FROM dividend_schedules")).scalar_one()
        assert n == 1
        # ORM 新插入（不带 name/currency）不再被 NOT NULL 拦截
        s.execute(text(
            "INSERT INTO dividend_schedules "
            "(market, code, ex_date, dps, div_type, source, confidence, status, created_at) "
            "VALUES ('a_share','600000','2025-06-01',0.35,'cash','crawler',0.9,'pending',"
            "'2025-01-01 00:00:00')"))
        s.commit()

        # 幂等：新 schema 再跑一次不报错、不改动
        drop_legacy_schedule_columns(s)


def test_drop_legacy_columns_noop_on_new_schema(tmp_path):
    """新库（本就没有 name/currency）上函数安全空跑。"""
    engine = create_engine(f"sqlite:///{tmp_path}/fresh.db")
    with Session(engine) as s:
        s.exec(text(
            "CREATE TABLE dividend_schedules ("
            "id INTEGER PRIMARY KEY, market VARCHAR NOT NULL, code VARCHAR NOT NULL, "
            "ex_date VARCHAR, dps FLOAT)"))
        s.commit()
        drop_legacy_schedule_columns(s)  # 不抛异常即通过
        cols = {r[1] for r in s.execute(text("PRAGMA table_info(dividend_schedules)")).all()}
        assert cols == {"id", "market", "code", "ex_date", "dps"}
