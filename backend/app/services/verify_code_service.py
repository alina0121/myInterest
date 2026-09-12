"""验证码服务：生成、存储、校验。SQLite 持久化，跨进程一致，重启不丢。

设计要点：
- 6 位数字明文返回给调用方（用于邮件/短信发送），DB 只存 bcrypt 哈希
- 单次有效：校验通过立即填 consumed_at，再次使用必失败
- 10 分钟过期（取自 SPECS code_ttl_minutes）
- 同目标 60 秒内不可重发（取自 SPECS code_send_interval_sec），防止滥发
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from ..database import engine
from ..models import VerifyCode
from ..utils.errors import AppError, Codes
from ..utils.security import hash_password, verify_password
from ..utils.timeutil import now_str
from . import config_service


def _parse_dt(s: str) -> datetime:
    """字符串时间解析：兼容 'YYYY-MM-DD HH:MM:SS' 与 ISO 格式。"""
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.fromisoformat(s)


def generate_and_store(channel: str, target: str, purpose: str) -> str:
    """生成 6 位数字验证码，哈希后入库，返回明文 code。

    限流：同 (channel, target, purpose) 在 code_send_interval_sec 内不可重发。
    """
    ttl_min = config_service.get_int("code_ttl_minutes")
    interval_sec = config_service.get_int("code_send_interval_sec")

    with Session(engine) as session:
        # 频率限制：查最近一条同目标同用途的记录，未过间隔则拒绝
        latest = session.exec(
            select(VerifyCode)
            .where(VerifyCode.channel == channel,
                   VerifyCode.target == target,
                   VerifyCode.purpose == purpose)
            .order_by(VerifyCode.id.desc())  # type: ignore
        ).first()
        if latest and latest.consumed_at is None:
            age = (datetime.now() - _parse_dt(latest.created_at)).total_seconds()
            if age < interval_sec:
                raise AppError(Codes.VALIDATION,
                               f"请 {interval_sec - int(age)} 秒后再试",
                               status=429)

        # 生成 6 位数字（首位非 0，避免前导 0 看起来短一位）
        code = f"{secrets.randbelow(900000) + 100000}"
        expires_at = (datetime.now() + timedelta(minutes=ttl_min)).strftime("%Y-%m-%d %H:%M:%S")
        record = VerifyCode(
            channel=channel, target=target, purpose=purpose,
            code_hash=hash_password(code),
            expires_at=expires_at,
        )
        session.add(record)
        session.commit()
    return code


def verify(channel: str, target: str, code: str, purpose: str) -> bool:
    """校验验证码：查最新未消费且未过期的记录，bcrypt 校验，通过即标记已消费。

    返回 True 表示校验通过，False 或抛错表示失败。
    """
    now = now_str()
    with Session(engine) as session:
        # 查最新一条未消费的同目标同用途记录
        records = session.exec(
            select(VerifyCode)
            .where(VerifyCode.channel == channel,
                   VerifyCode.target == target,
                   VerifyCode.purpose == purpose,
                   VerifyCode.consumed_at.is_(None))  # type: ignore
            .order_by(VerifyCode.id.desc())  # type: ignore
        ).all()
        if not records:
            raise AppError(Codes.VALIDATION, "验证码不存在或已使用，请重新获取",
                           status=400)
        # 取最新一条
        latest = records[0]
        # 过期检查
        if latest.expires_at < now:
            raise AppError(Codes.VALIDATION, "验证码已过期，请重新获取",
                           status=400)
        # bcrypt 校验
        if not verify_password(code, latest.code_hash):
            raise AppError(Codes.VALIDATION, "验证码错误", status=400)
        # 标记已使用
        latest.consumed_at = now
        session.add(latest)
        session.commit()
    return True
