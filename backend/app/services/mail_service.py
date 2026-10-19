"""邮件服务：用 smtplib 发送验证码邮件。

设计要点：
- 配置全部从 SPECS 读取（mail_enabled/smtp_host/smtp_port/...）
- mail_enabled=False 或 SMTP 未配置完整时不报错，验证码降级打印到日志（开发期可直接取码登录）
- 通过 FastAPI BackgroundTasks 调用，失败仅 log.warning 不阻塞响应
- 邮件正文按 purpose 区分（login/bind）
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from . import config_service

log = logging.getLogger("xi.mail")

# 邮件主题与正文模板（按 purpose 区分）
_TEMPLATES = {
    "login": ("登录验证码", "您正在登录攒息，验证码：{code}，10 分钟内有效。"),
    "bind": ("绑定邮箱验证码", "您正在绑定邮箱，验证码：{code}，10 分钟内有效。"),
}


def send_code(target: str, code: str, purpose: str) -> None:
    """发送验证码邮件。mail_enabled=False / SMTP 未配置时降级打印日志。

    本函数同步执行（由 BackgroundTasks 包装异步调用），失败仅记日志。
    """
    if not config_service.get_bool("mail_enabled"):
        # 未开启邮件服务时不阻塞登录流程：验证码降级打印到日志（与 SMTP 未配置同款兜底）
        log.warning("[mail] 邮件服务未开启，验证码仅打印日志。to=%s purpose=%s code=%s",
                    target, purpose, code)
        return
    host = config_service.get_text("smtp_host").strip()
    port = config_service.get_int("smtp_port")
    user = config_service.get_text("smtp_user").strip()
    password = config_service.get_text("smtp_password")
    sender = config_service.get_text("smtp_sender").strip() or user
    use_ssl = config_service.get_bool("smtp_use_ssl")
    if not host or not user or not password:
        # 开发期降级：SMTP 未配置完整时验证码打印到日志（参考 eatWhat），
        # 生产环境配置完成后不会走到这里
        log.warning("[mail] SMTP 配置不完整，验证码仅打印日志。to=%s purpose=%s code=%s",
                    target, purpose, code)
        return

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
        # 发送失败仅日志（BackgroundTasks 中抛错会被吞），同时打印验证码兜底，
        # 避免码已入库却无人能拿到（本地开发/SMTP 故障时可从日志取码）
        log.warning("[mail] send failed to %s: %s（降级打印验证码 code=%s）",
                    target, e, code)


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
