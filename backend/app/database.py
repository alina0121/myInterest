"""数据库引擎：SQLite WAL + 外键约束 + 写锁等待。

SQLite 是文件级单库，靠下面三个 PRAGMA 兼顾轻量与并发：
- WAL：读写不互斥（看板查询不阻塞录入），崩溃也更安全
- foreign_keys=ON：SQLite 默认竟然不检查外键，必须每连接手动开
- busy_timeout=5000：别人正在写时最多等 5 秒而不是立刻报 database is locked
"""
from sqlalchemy import event
from sqlmodel import Session, create_engine

from .config import DATABASE_URL, ensure_dirs

ensure_dirs()

_is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    echo=False,
    # FastAPI 多线程共享同一连接池里的连接，需关掉 SQLite 的「同线程」限制
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_conn, _record):  # pragma: no cover
    """每个新连接建立时执行一次（PRAGMA 是连接级的，不持久化到库文件）。"""
    if _is_sqlite:
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


def get_session():
    """FastAPI 依赖：每请求一个 Session，请求结束自动关闭（with 管理事务边界）。"""
    with Session(engine) as session:
        yield session
