"""系统配置服务：元数据驱动的 key-value 配置中心。

三层取值优先级（任意一层取到即用）：
  ① system_configs 表（管理员在后台改过的值）
  ② 环境变量（spec.env_key，如 XI_AV_API_KEY；部署期运维配置）
  ③ spec.default 内置默认值

性能：进程内全量缓存（_cache），TTL 60s 兜底 + 保存即失效（invalidate_cache），
业务代码读配置基本不碰数据库；多进程部署时各进程最多 60 秒后自动收敛。

新增配置项：只需在下面 SPECS 加一条，后台页面与读取接口自动生效，无需建表迁库。
"""
import logging
import os
import threading
import time
from decimal import Decimal, InvalidOperation

from sqlmodel import Session, select

from ..database import engine
from ..models import SystemConfig
from ..utils.errors import AppError, Codes

log = logging.getLogger("xi.config")

# 支持的值类型
_INT = "int"
_FLOAT = "float"
_BOOL = "bool"
_STR = "str"

# SPECS：配置项元数据（唯一事实来源）
#   type      值类型；default 内置默认；env_key 可取自的环境变量
#   category 后台分组；sensitive 敏感值（API Key/Secret，读接口脱敏）
#   min/max   数值范围；help 页面展示的说明
SPECS: dict[str, dict] = {
    # ── 采集（爬虫） ────────────────────────────────────────────
    "crawl_a_share_page_size": {
        "category": "采集", "type": _INT, "default": 100, "min": 10, "max": 500,
        "label": "A股每次采集条数", "help": "东方财富接口每页条数（最新公告按日期倒序），日常增量 100 条足够。"},
    "crawl_us_tickers": {
        "category": "采集", "type": _STR, "default": "AAPL,MSFT,JNJ,KO,PG",
        "widget": "tags",
        "label": "美股采集白名单", "help": "逐个输入美股代码（如 VOO、SCHD、AAPL），回车添加；免费 Key 限 25 次/天，建议不超过 10 只。"},
    "crawl_hk_tickers": {
        "category": "采集", "type": _STR, "default": "00700,09988,03690,01810,00941",
        "widget": "tags",
        "label": "港股采集白名单", "help": "逐个输入港股 5 位数字代码（如 00700、09988），回车添加；建议不超过 20 只。"},
    "crawl_hk_rate_sleep": {
        "category": "采集", "type": _INT, "default": 1, "min": 0, "max": 10,
        "label": "港股采集间隔(秒)", "help": "东方财富 F10 接口无公开限流，串行拉取时每只之间的等待秒数，默认 1 秒。"},
    "crawl_fund_page_size": {
        "category": "采集", "type": _INT, "default": 100, "min": 10, "max": 200,
        "label": "基金每页采集条数", "help": "天天基金分红列表接口每页条数，按登记日倒序增量抓取。"},
    "crawl_fund_max_pages": {
        "category": "采集", "type": _INT, "default": 10, "min": 1, "max": 50,
        "label": "基金最大采集页数", "help": "单次最多翻页数，防止接口异常时无限翻页；正常增量遇到整页已入库即停止。"},
    "crawl_us_rate_sleep": {
        "category": "采集", "type": _INT, "default": 12, "min": 0, "max": 60,
        "label": "美股采集间隔(秒)", "help": "Alpha Vantage 免费层限 5 次/分钟，串行拉取时每只之间的等待秒数。"},
    "av_api_key": {
        "category": "采集", "type": _STR, "default": "", "env_key": "XI_AV_API_KEY",
        "sensitive": True, "label": "Alpha Vantage API Key",
        "help": "美股分红数据源密钥，免费申请：https://www.alphavantage.co/support/#api-key；留空则跳过美股采集。"},

    # ── 定时任务 ────────────────────────────────────────────────
    "scheduler_enabled": {
        "category": "定时任务", "type": _BOOL, "default": True,
        "label": "启用定时采集", "help": "开启后每天在指定时刻自动采集预案并匹配持仓；环境变量 XI_SCHEDULER=0 可强制关闭。"},
    "scheduler_hours": {
        "category": "定时任务", "type": _STR, "default": "8,18",
        "label": "每日执行时刻", "help": "逗号分隔的小时（0-23），实际在该小时 05 分执行以错峰，如 8,18 表示 8:05 与 18:05。"},

    # ── 汇率 ────────────────────────────────────────────────────
    "fx_fallback_usd": {
        "category": "汇率", "type": _FLOAT, "default": 7.12, "min": 0.01, "max": 100,
        "label": "美元兜底汇率", "help": "断网且库中无任何美元汇率时的兜底值（1 USD = ? CNY），保证离线也能出统计。"},
    "fx_fallback_hkd": {
        "category": "汇率", "type": _FLOAT, "default": 0.9128, "min": 0.01, "max": 100,
        "label": "港币兜底汇率", "help": "断网且库中无任何港币汇率时的兜底值（1 HKD = ? CNY）。"},

    # ── 安全 ────────────────────────────────────────────────────
    "login_rate_limit_per_min": {
        "category": "安全", "type": _INT, "default": 10, "min": 1, "max": 120,
        "label": "登录限流(次/分钟/IP)", "help": "同一 IP 登录/注册/微信登录每分钟最大次数，超出返回 429。"},
    "access_token_minutes": {
        "category": "安全", "type": _INT, "default": 120, "min": 5, "max": 1440,
        "env_key": "XI_ACCESS_TOKEN_MINUTES",
        "label": "访问令牌有效期(分钟)", "help": "access token 有效期；修改对【新签发】的令牌立即生效，已签发的到期前不变。"},
    "refresh_token_days": {
        "category": "安全", "type": _INT, "default": 30, "min": 1, "max": 365,
        "env_key": "XI_REFRESH_TOKEN_DAYS",
        "label": "刷新令牌有效期(天)", "help": "refresh token 有效期；修改对新签发的令牌立即生效。"},
    "wx_appid": {
        "category": "安全", "type": _STR, "default": "", "env_key": "XI_WX_APPID",
        "label": "微信小程序 AppID", "help": "小程序登录用；AppID 与 Secret 都配置后自动启用真实微信登录，否则为 mock 模式。"},
    "wx_secret": {
        "category": "安全", "type": _STR, "default": "", "env_key": "XI_WX_SECRET",
        "sensitive": True, "label": "微信小程序 Secret", "help": "小程序登录密钥；页面脱敏显示，留空保存表示不修改。"},

    # ── 统计预测 ────────────────────────────────────────────────
    "forecast_by_history": {
        "category": "统计预测", "type": _BOOL, "default": True,
        "label": "按历史节奏预测分红", "help": "看板未来 12 个月预测开关：开启时按近 3 年同月每股分红均值×当前持仓估算，关闭则只展示已公告预案。"},
    "forecast_freq": {
        "category": "统计预测", "type": _BOOL, "default": True,
        "label": "季派/月派自动生成推算预告", "help": "开启后定时任务为季派/月派持仓按历史派息节奏自动生成 pending 推算预案（需人工审核）；关闭则仅靠公告与爬虫来源。"},

    # ── 通知与提醒 ──────────────────────────────────────────────
    "auto_push": {
        "category": "通知与提醒", "type": _BOOL, "default": True,
        "label": "预案发布后自动匹配持仓", "help": "审核通过预案后，自动为持仓用户生成 pending 分红记录并触发推送；关闭则需用户手动在「即将到账」生成。"},
    "remind_3d": {
        "category": "通知与提醒", "type": _BOOL, "default": True,
        "label": "派息日前 3 天提醒", "help": "全局提醒总开关：开启后每日检查派息日在 3 天内及当天的预案，对开启了提醒的持仓用户发送提醒；关闭则全站不发送派息提醒。"},

    # ── 用户提交 ────────────────────────────────────────────────
    "user_submit": {
        "category": "用户提交", "type": _BOOL, "default": False,
        "label": "允许用户提交预案", "help": "开启后用户可在前端提交分红预案（进入待审核队列，由管理员审核）；关闭则用户端提交入口返回 403。"},
}

# ── 进程内缓存 ─────────────────────────────────────────────────
_CACHE_TTL = 60.0
_lock = threading.Lock()
_cache: dict[str, str] | None = None      # key → 文本值（仅 DB 覆盖层）
_cache_at = 0.0


def invalidate_cache() -> None:
    """配置写入后调用：清空缓存，下次读取重新加载（保证同进程立即生效）。"""
    global _cache, _cache_at
    with _lock:
        _cache = None
        _cache_at = 0.0


def _load_db_overrides() -> dict[str, str]:
    """加载 DB 覆盖层（带 TTL 的全量缓存）。"""
    global _cache, _cache_at
    now = time.time()
    if _cache is not None and now - _cache_at < _CACHE_TTL:
        return _cache
    with _lock:  # 双检，避免多线程并发时重复查库
        if _cache is not None and now - _cache_at < _CACHE_TTL:
            return _cache
        with Session(engine) as session:
            rows = session.exec(select(SystemConfig)).all()
            _cache = {r.config_key: (r.config_value if r.config_value is not None else "")
                      for r in rows}
        _cache_at = time.time()
        return _cache


# ── 类型转换与校验 ─────────────────────────────────────────────
def _to_text(spec: dict, value) -> str:
    """把前端提交的 Python 值按类型转成存储文本。"""
    t = spec["type"]
    if t == _BOOL:
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, str) and value.strip().lower() in ("1", "true", "on", "yes"):
            return "1"
        if isinstance(value, (int, float)) and value:
            return "1"
        return "0"
    return str(value).strip()


def validate_and_store_text(key: str, value) -> str:
    """校验一个提交值，返回可入库的文本；非法抛 VALIDATION。"""
    spec = SPECS.get(key)
    if spec is None:
        raise AppError(Codes.VALIDATION, f"未知配置项：{key}", status=422)
    text = _to_text(spec, value)
    t, label = spec["type"], spec["label"]

    if t == _INT:
        try:
            n = int(text)
        except ValueError:
            raise AppError(Codes.VALIDATION, f"「{label}」必须是整数", status=422)
        if "min" in spec and n < spec["min"] or "max" in spec and n > spec["max"]:
            raise AppError(Codes.VALIDATION,
                           f"「{label}」需在 {spec.get('min')}~{spec.get('max')} 之间",
                           status=422)
    elif t == _FLOAT:
        try:
            n = Decimal(text)  # 用 Decimal 校验，挡住 NaN/Inf
            if not n.is_finite() or n <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            raise AppError(Codes.VALIDATION, f"「{label}」必须是大于 0 的数字", status=422)
        if "min" in spec and float(n) < spec["min"] or "max" in spec and float(n) > spec["max"]:
            raise AppError(Codes.VALIDATION,
                           f"「{label}」需在 {spec.get('min')}~{spec.get('max')} 之间",
                           status=422)
    elif t == _STR:
        if key == "crawl_us_tickers" and text:
            parts = [p.strip().upper() for p in text.split(",") if p.strip()]
            if not all(p.isalnum() and 1 <= len(p) <= 8 for p in parts):
                raise AppError(Codes.VALIDATION,
                               "「美股采集白名单」需为逗号分隔的代码，如 AAPL,MSFT",
                               status=422)
            text = ",".join(parts)  # 归一化：去空格、转大写
        elif key == "crawl_hk_tickers" and text:
            # 港股代码为 5 位数字（如 00700）
            parts = [p.strip() for p in text.split(",") if p.strip()]
            if not all(p.isdigit() and len(p) == 5 for p in parts):
                raise AppError(Codes.VALIDATION,
                               "「港股采集白名单」需为逗号分隔的 5 位数字代码，如 00700,09988",
                               status=422)
            text = ",".join(parts)
        elif key == "scheduler_hours":
            try:
                hours = [int(h) for h in text.split(",") if h.strip()]
                assert hours and all(0 <= h <= 23 for h in hours)
            except (ValueError, AssertionError):
                raise AppError(Codes.VALIDATION,
                               "「每日执行时刻」需为逗号分隔的 0-23 小时，如 8,18",
                               status=422)
            text = ",".join(str(h) for h in sorted(set(hours)))  # 归一化：去重排序
    return text


# ── 读取接口（业务代码用） ─────────────────────────────────────
def get_text(key: str) -> str:
    """取配置的原始文本：DB 覆盖 → 环境变量 → 默认值。key 未注册直接报错（编程错误）。"""
    spec = SPECS[key]
    overrides = _load_db_overrides()
    if key in overrides:
        return overrides[key]
    if spec.get("env_key"):
        env_val = os.getenv(spec["env_key"])
        if env_val is not None and env_val != "":
            return env_val
    return str(spec["default"])


def get_int(key: str) -> int:
    return int(get_text(key))


def get_float(key: str) -> Decimal:
    return Decimal(get_text(key))


def get_bool(key: str) -> bool:
    return get_text(key) in ("1", "true", "True", "yes")


def get_list(key: str) -> list[str]:
    """逗号分隔文本 → 列表（空串返回空列表）。"""
    return [p.strip() for p in get_text(key).split(",") if p.strip()]


def is_default_or_env(key: str) -> bool:
    """该配置当前是否未被 DB 覆盖（即走环境变量/默认值）。"""
    return key not in _load_db_overrides()


# ── 后台展示/写入 ─────────────────────────────────────────────
def _mask(text: str) -> str:
    """敏感值脱敏：只露后 4 位。"""
    if not text:
        return ""
    return ("*" * max(len(text) - 4, 4)) + text[-4:] if len(text) > 4 else "****"


def admin_view() -> list[dict]:
    """后台配置页数据：按 category 分组，敏感值不回传原文。"""
    groups: dict[str, list[dict]] = {}
    for key, spec in SPECS.items():
        raw = get_text(key)  # DB → env → 默认（敏感项据此判断是否已配置）
        sensitive = bool(spec.get("sensitive"))
        overridden = not is_default_or_env(key)
        item = {
            "key": key, "label": spec["label"], "help": spec["help"],
            "type": spec["type"], "category": spec["category"],
            "min": spec.get("min"), "max": spec.get("max"),
            "widget": spec.get("widget"),  # 可选渲染控件：tags=标签式多选
            "overridden": overridden,  # 是否被管理员改过（DB 有覆盖行）
        }
        if sensitive:
            item.update({"value": None, "has_value": bool(raw),
                         "mask": _mask(raw) if raw else ""})
        elif spec["type"] == _BOOL:
            item["value"] = raw in ("1", "true", "True", "yes")
        elif spec["type"] == _INT:
            item["value"] = int(raw)
        elif spec["type"] == _FLOAT:
            item["value"] = float(raw)
        else:
            item["value"] = raw
        groups.setdefault(spec["category"], []).append(item)
    # 保持 SPECS 的首次出现顺序作为分组顺序
    order: list[str] = []
    for spec in SPECS.values():
        if spec["category"] not in order:
            order.append(spec["category"])
    return [{"category": c, "items": groups[c]} for c in order]


def set_values(session: Session, items: dict[str, str], admin_id: int) -> list[str]:
    """批量保存配置。

    敏感项约定：提交空串/None = 不修改（避免页面保存时把密钥冲掉）；
    要清空密钥请用 reset_value 恢复默认。返回实际变更的 key 列表。
    """
    changed: list[str] = []
    for key, value in items.items():
        spec = SPECS.get(key)
        if spec is None:
            raise AppError(Codes.VALIDATION, f"未知配置项：{key}", status=422)
        if spec.get("sensitive") and (value is None or str(value).strip() == ""):
            continue  # 敏感项留空 = 保持原值
        text = validate_and_store_text(key, value)
        row = session.get(SystemConfig, key)
        if row is None:
            row = SystemConfig(config_key=key, config_value=text, updated_by=admin_id)
        else:
            row.config_value = text
            row.updated_by = admin_id
        session.add(row)
        changed.append(key)
    if changed:
        session.commit()
        invalidate_cache()
        log.info("system config updated by admin=%s: %s", admin_id, changed)
    return changed


def reset_value(session: Session, key: str, admin_id: int) -> None:
    """删除 DB 覆盖行，使该配置回退到环境变量/默认值。"""
    if key not in SPECS:
        raise AppError(Codes.VALIDATION, f"未知配置项：{key}", status=422)
    row = session.get(SystemConfig, key)
    if row is not None:
        session.delete(row)
        session.commit()
        invalidate_cache()
        log.info("system config reset by admin=%s: %s", admin_id, key)
