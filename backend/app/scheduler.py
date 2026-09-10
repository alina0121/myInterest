"""轻量后台定时任务（docs/06 §3.2）：每日定点爬取预案 + 全体 auto-match。

用 asyncio 实现避免引入 APScheduler 依赖；执行时刻与开关在后台「系统配置」可调
（scheduler_hours / scheduler_enabled），XI_SCHEDULER=0 仍可由环境变量强制关闭。
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta

log = logging.getLogger("xi.scheduler")

_RUN_OFFSET_MIN = 5  # 整点后 5 分钟错峰


def _run_hours() -> tuple[int, ...]:
    """执行小时（后台配置 scheduler_hours，逗号分隔，已校验为 0-23）。"""
    from .services import config_service
    try:
        return tuple(int(h) for h in config_service.get_text("scheduler_hours").split(",") if h.strip())
    except Exception:  # 配置异常时退回默认，保证任务不断
        return (8, 18)


def _next_run() -> float:
    now = datetime.now()
    candidates = []
    for h in _run_hours():
        t = now.replace(hour=h, minute=_RUN_OFFSET_MIN, second=0, microsecond=0)
        if t <= now:
            t += timedelta(days=1)
        candidates.append(t)
    return max((min(candidates) - now).total_seconds(), 1.0)


def _run_job() -> None:
    from sqlmodel import Session
    from .database import engine
    from .services.schedule_service import run_daily_job
    with Session(engine) as session:
        run_daily_job_with_session(session)


def run_daily_job_with_session(session) -> None:
    from .services import crawler_service
    from .services.schedule_service import auto_match
    try:
        result = crawler_service.run_crawl(session)
        log.info("scheduled crawl: %s", result)
    except Exception:
        log.exception("scheduled crawl failed")
    try:
        result = auto_match(session)
        log.info("scheduled auto-match: matched=%s skipped=%s",
                 result["matched"], result["skipped"])
    except Exception:
        log.exception("scheduled auto-match failed")


async def _loop() -> None:  # pragma: no cover - 后台循环
    while True:
        await asyncio.sleep(_next_run())
        try:
            # 爬库/auto_match 全是同步 SQLAlchemy 代码，
            # 用 to_thread 丢到线程池跑，避免阻塞 FastAPI 的事件循环
            await asyncio.to_thread(_run_job)
        except Exception:
            log.exception("scheduled job failed")


def start() -> asyncio.Task | None:
    """在 lifespan 中调用；XI_SCHEDULER=0 或后台关闭 scheduler_enabled 时不启动。"""
    if os.getenv("XI_SCHEDULER", "1") == "0":
        return None
    try:
        from .services import config_service
        if not config_service.get_bool("scheduler_enabled"):
            log.info("scheduler disabled by system config")
            return None
    except Exception:
        log.exception("read scheduler_enabled failed, fallback to enabled")
    return asyncio.create_task(_loop(), name="xi-scheduler")
