"""账户管理接口：轻量方案，复用 holdings.account 字符串字段。

不建独立 accounts 表，账户列表来自两处：
1. holdings 表 DISTINCT account（实际有持仓的账户）
2. user_settings.accounts_meta JSON（用户自定义的元数据：颜色/排序/归档）

两者并集即为账户列表。元数据保存到 user_settings.accounts_meta。
"""
import json

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..database import get_session
from ..models import Holding, User, UserSetting
from ..utils.errors import AppError, Codes, ok
from ..utils.timeutil import now_str
from .deps import get_current_user
from .settings import _get_or_create

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

# 默认颜色池：用户添加账户时若未指定颜色，按顺序循环分配
_DEFAULT_COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b",
                   "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"]


def _load_meta(s: UserSetting) -> list[dict]:
    """解析 accounts_meta JSON；空或异常返回 []。"""
    if not s.accounts_meta:
        return []
    try:
        meta = json.loads(s.accounts_meta)
        return meta if isinstance(meta, list) else []
    except (ValueError, TypeError):
        return []


def _dump_meta(meta: list[dict]) -> str:
    """序列化 accounts_meta 为 JSON 字符串。"""
    return json.dumps(meta, ensure_ascii=False)


@router.get("")
def list_accounts(session: Session = Depends(get_session),
                  user: User = Depends(get_current_user)):
    """列出账户：holdings 表 DISTINCT account ∪ user_settings.accounts_meta。

    返回 [{name, broker, color, archived, holding_count}]。
    holding_count 为该账户下的持仓数（来自 holdings 表）。
    archived=True 的账户表示用户已归档，但仍有持仓时仍会显示。
    """
    s = _get_or_create(session, user.id)
    meta = _load_meta(s)

    # 持仓表中实际存在的账户及计数
    holdings = session.exec(
        select(Holding).where(Holding.user_id == user.id)
    ).all()
    account_counts: dict[str, int] = {}
    for h in holdings:
        if h.account:  # account 可空（未分账户的持仓）
            account_counts[h.account] = account_counts.get(h.account, 0) + 1

    # 合并：meta 中的账户 + 持仓表中存在但 meta 中没有的账户
    meta_names = {m.get("name") for m in meta}
    items = []
    for m in meta:
        name = m.get("name")
        if not name:
            continue
        items.append({
            "name": name,
            "broker": m.get("broker", ""),
            "color": m.get("color") or "#94a3b8",
            "sort": m.get("sort", 0),
            "archived": bool(m.get("archived", False)),
            "holding_count": account_counts.get(name, 0),
        })
    # 持仓表有但 meta 没有的账户，追加到末尾
    for name, cnt in account_counts.items():
        if name not in meta_names:
            items.append({
                "name": name,
                "broker": "",
                "color": "#94a3b8",
                "sort": 999,
                "archived": False,
                "holding_count": cnt,
            })
    # 排序：未归档在前，按 sort 升序
    items.sort(key=lambda x: (x["archived"], x["sort"], x["name"]))
    return ok({"items": items, "total": len(items)})


@router.put("/meta")
def update_meta(body: dict, session: Session = Depends(get_session),
                user: User = Depends(get_current_user)):
    """保存账户元数据：[{name, broker, color, sort, archived}]。

    仅更新 meta，不影响 holdings 表的 account 字段。
    """
    s = _get_or_create(session, user.id)
    meta = body.get("accounts_meta")
    if not isinstance(meta, list):
        raise AppError(Codes.VALIDATION, "accounts_meta 必须是数组", status=422)
    # 校验每条
    cleaned = []
    names = set()
    for i, item in enumerate(meta):
        if not isinstance(item, dict):
            raise AppError(Codes.VALIDATION,
                           f"第 {i+1} 条不是对象", status=422)
        name = (item.get("name") or "").strip()
        if not name:
            raise AppError(Codes.VALIDATION,
                           f"第 {i+1} 条 name 不能为空", status=422)
        if name in names:
            raise AppError(Codes.VALIDATION,
                           f"账户名「{name}」重复", status=422)
        names.add(name)
        cleaned.append({
            "name": name,
            "broker": (item.get("broker") or "").strip(),
            "color": (item.get("color") or _DEFAULT_COLORS[i % len(_DEFAULT_COLORS)]),
            "sort": int(item.get("sort", i)),
            "archived": bool(item.get("archived", False)),
        })
    s.accounts_meta = _dump_meta(cleaned)
    s.updated_at = now_str()
    session.add(s)
    session.commit()
    return ok({"saved": len(cleaned)})
