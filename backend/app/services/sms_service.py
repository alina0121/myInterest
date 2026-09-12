"""短信服务：预留桩函数。sms_enabled=False 时抛错。

V2 再实现真实发送（阿里云/腾讯云 SDK）。
配置项已在 SPECS 中定义：sms_provider/sms_access_key/sms_secret/sms_sign/
sms_template_login/sms_template_reset。
"""
import logging

from ..utils.errors import AppError, Codes
from . import config_service

log = logging.getLogger("xi.sms")


def send_code(target: str, code: str, purpose: str) -> None:
    """发送验证码短信。sms_enabled=False 时抛错。

    V2 接入阿里云/腾讯云 SDK 后填充真实逻辑。
    """
    if not config_service.get_bool("sms_enabled"):
        raise AppError(Codes.VALIDATION, "短信服务未开启，请联系管理员",
                       status=503)
    # V2 在此接入真实短信 SDK
    provider = config_service.get_text("sms_provider")
    log.warning("sms send stub called: target=%s purpose=%s provider=%s (V2 待实现)",
                target, purpose, provider)
    raise AppError(Codes.SERVER_ERROR, "短信服务暂未实现，请使用邮箱验证码",
                   status=501)
