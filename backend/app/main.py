"""息计 API 入口（docs/04 §0）。开发模式：uvicorn app.main:app --reload --port 8000"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

# 启动时加载 backend/.env（无 python-dotenv 依赖，仅 KEY=VALUE 行）
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .db_init import init_db
from .scheduler import start as start_scheduler
from .utils.errors import AppError, Codes


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    task = start_scheduler()
    yield
    if task:
        task.cancel()


app = FastAPI(title="息计 API", version="0.1.0", lifespan=lifespan)

# H5 开发跨域
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])


# 统一响应包络：成功 {"code":0,...}，失败也走同一结构，前端只认 code 字段
def _envelope(code: int, msg: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"code": code, "msg": msg, "data": None})


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    """业务异常 → 统一包络（docs/04 §0.5 错误码表）。"""
    return _envelope(exc.code, exc.msg, exc.status)


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):  # pragma: no cover
    # 兜底：任何没料到的异常都不向前端吐堆栈，统一 500
    return _envelope(Codes.SERVER_ERROR, "服务器内部错误", 500)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_request: Request, exc: StarletteHTTPException):
    code = {401: Codes.UNAUTHORIZED, 403: Codes.FORBIDDEN,
            404: Codes.NOT_FOUND}.get(exc.status_code, Codes.SERVER_ERROR)
    return _envelope(code, str(exc.detail), exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError):
    data = [{"loc": ".".join(str(p) for p in e.get("loc", [])),
             "msg": e.get("msg", "")} for e in exc.errors()]
    return JSONResponse(status_code=422,
                        content={"code": Codes.VALIDATION, "msg": "参数校验失败",
                                 "data": data})


# ---------- 路由 ----------
from .api import (accounts, admin, auth, calendar, community, dividends, holdings, lots,  # noqa: E402
                  schedules, settings, stats, system)

app.include_router(auth.router)
app.include_router(holdings.router)
app.include_router(lots.router)
app.include_router(dividends.router)
app.include_router(schedules.router)
app.include_router(stats.router)
app.include_router(calendar.router)
app.include_router(settings.router)
app.include_router(accounts.router)
app.include_router(system.router)
app.include_router(community.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"code": 0, "msg": "ok", "data": {"status": "up", "service": "xi-api"}}
