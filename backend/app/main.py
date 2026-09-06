"""息计 API 入口（docs/04 §0）。开发模式：uvicorn app.main:app --reload --port 8000"""
from contextlib import asynccontextmanager

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


def _envelope(code: int, msg: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"code": code, "msg": msg, "data": None})


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    """业务异常 → 统一包络（docs/04 §0.5 错误码表）。"""
    return _envelope(exc.code, exc.msg, exc.status)


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):  # pragma: no cover
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
from .api import (admin, auth, calendar, community, dividends, holdings, lots,  # noqa: E402
                  schedules, settings, stats, system)

app.include_router(auth.router)
app.include_router(holdings.router)
app.include_router(lots.router)
app.include_router(dividends.router)
app.include_router(schedules.router)
app.include_router(stats.router)
app.include_router(calendar.router)
app.include_router(settings.router)
app.include_router(system.router)
app.include_router(community.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"code": 0, "msg": "ok", "data": {"status": "up", "service": "xi-api"}}
