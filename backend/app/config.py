"""应用配置：环境变量优先，默认值面向本地开发。"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

# 数据目录与数据库
DATA_DIR = Path(os.getenv("XI_DATA_DIR", str(BASE_DIR / "data")))
DATABASE_URL = os.getenv("XI_DATABASE_URL", f"sqlite:///{DATA_DIR / 'xi.db'}")

# JWT
# 生产环境必须用 XI_SECRET_KEY 环境变量覆盖默认值，否则 token 可被伪造！
SECRET_KEY = os.getenv("XI_SECRET_KEY", "dev-secret-change-me-in-production")
ACCESS_TOKEN_MINUTES = int(os.getenv("XI_ACCESS_TOKEN_MINUTES", "120"))  # 短期令牌 2 小时
REFRESH_TOKEN_DAYS = int(os.getenv("XI_REFRESH_TOKEN_DAYS", "30"))      # 刷新令牌 30 天

# 汇率源（frankfurter 免费无 key，备用值见系统配置 fx_fallback_usd/hkd）
FX_API_BASE = os.getenv("XI_FX_API", "https://api.frankfurter.app")

# 置 1 时汇率服务离线（测试环境用）
FX_OFFLINE = os.getenv("XI_FX_OFFLINE", "") == "1"

# 微信小程序登录：AppID/Secret 已支持后台「系统配置」管理，以下环境变量仍可作为部署期覆盖。
WX_APPID = os.getenv("XI_WX_APPID", "")
WX_SECRET = os.getenv("XI_WX_SECRET", "")
# 置 1 时跳过真实 code2session 调用，用 code 直接当 openid（开发/测试）
WX_MOCK = os.getenv("XI_WX_MOCK", "1" if not WX_APPID else "0") == "1"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
