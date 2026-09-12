"""邮件服务：用 smtplib 发送验证码邮件。

设计要点：
- 配置全部从 SPECS 读取（mail_enabled/smtp_host/smtp_port/...）
- mail_enabled=False 时直接抛错，前端提示"邮件服务未开启"
- 通过 FastAPI BackgroundTasks 调用，失败仅 log.warning 不阻塞响应
- 邮件正文按 purpose 区分（login/register/reset/bind）
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ..utils.errors import AppError, Codes
from . import config_service

log = logging.getLogger("xi.mail")

# 邮件主题与正文模板（按 purpose 区分）
_TEMPLATES = {
    "login": ("登录验证码", "您正在登录攒息，验证码：{code}，10 分钟内有效。"),
    "register": ("注册验证码", "您正在注册攒息账号，验证码：{code}，10 分钟内有效。"),
    "reset": ("重置密码验证码", "您正在重置密码，验证码：{code}，10 分钟内有效。如非本人操作请忽略。"),
    "bind": ("绑定邮箱验证码", "您正在绑定邮箱，验证码：{code}，10 分钟内有效。"),
}


def send_code(target: str, code: str, purpose: str) -> None:
    """发送验证码邮件。mail_enabled=False 时抛错。

    本函数同步执行（由 BackgroundTasks 包装异步调用），失败仅记日志。
    """
    if not config_service.get_bool("mail_enabled"):
        raise AppError(Codes.VALIDATION, "邮件服务未开启，请联系管理员",
                       status=503)
    host = config_service.get_text("smtp_host").strip()
    port = config_service.get_int("smtp_port")
    user = config_service.get_text("smtp_user").strip()
    password = config_service.get_text("smtp_password")
    sender = config_service.get_text("smtp_sender").strip() or user
    use_ssl = config_service.get_bool("smtp_use_ssl")
    if not host or not user or not password:
        raise AppError(Codes.SERVER_ERROR, "邮件服务配置不完整", status=500)

    subject, body = _TEMPLATES.get(purpose, ("验证码", "您的验证码：{code}"))
    body = body.format(code=code)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = target
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=15) as s:
                s.login(user, password)
                s.sendmail(sender, [target], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls()
                s.login(user, password)
                s.sendmail(sender, [target], msg.as_string())
        log.info("mail sent to %s purpose=%s", target, purpose)
    except Exception as e:
        # 失败仅日志，不抛错（BackgroundTasks 中抛错会被吞，且不应影响用户响应）
        log.warning("mail send failed to %s: %s", target, e)


def send_test(target: str) -> tuple[bool, str]:
    """发送测试邮件，返回 (成功标志, 消息)。供后台 test-mail 接口使用。"""
    if not config_service.get_bool("mail_enabled"):
        return False, "邮件服务未开启"
    host = config_service.get_text("smtp_host").strip()
    port = config_service.get_int("smtp_port")
    user = config_service.get_text("smtp_user").strip()
    password = config_service.get_text("smtp_password")
    sender = config_service.get_text("smtp_sender").strip() or user
    use_ssl = config_service.get_bool("smtp_use_ssl")
    if not host or not user or not password:
        return False, "邮件服务配置不完整"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "攒息测试邮件"
    msg["From"] = sender
    msg["To"] = target
    msg.attach(MIMEText("这是一封来自攒息系统的测试邮件，收到即表示 SMTP 配置正常。",
                        "plain", "utf-8"))
    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=15) as s:
                s.login(user, password)
                s.sendmail(sender, [target], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls()
                s.login(user, password)
                s.sendmail(sender, [target], msg.as_string())
        return True, "发送成功"
    except Exception as e:
        return False, f"发送失败：{e}"
