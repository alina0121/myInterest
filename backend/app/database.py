"""数据库引擎：SQLite WAL + 外键约束 + 写锁等待。"""
from sqlalchemy import event
from sqlmodel import Session, create_engine

from .config import DATABASE_URL, ensure_dirs

ensure_dirs()

_is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_conn, _record):  # pragma: no cover
    if _is_sqlite:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


def get_session():
    """FastAPI 依赖：每请求一个 Session。"""
    with Session(engine) as session:
        yield session
