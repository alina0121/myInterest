"""轻量后台定时任务（docs/06 §3.2）：每日 8:05 / 18:05 爬取预案 + 全体 auto-match。

用 asyncio 实现避免引入 APScheduler 依赖；XI_SCHEDULER=0 关闭（测试环境）。
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta

log = logging.getLogger("xi.scheduler")

RUN_HOURS = (8, 18)
_RUN_OFFSET_MIN = 5  # 整点后 5 分钟错峰


def _next_run() -> float:
    now = datetime.now()
    candidates = []
    for h in RUN_HOURS:
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
            await asyncio.to_thread(_run_job)
        except Exception:
            log.exception("scheduled job failed")


def start() -> asyncio.Task | None:
    """在 lifespan 中调用；XI_SCHEDULER=0 时不启动。"""
    if os.getenv("XI_SCHEDULER", "1") == "0":
        return None
    return asyncio.create_task(_loop(), name="xi-scheduler")
