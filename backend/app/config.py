"""应用配置：环境变量优先，默认值面向本地开发。

仅保留「必须启动期确定、或不宜后台编辑」的配置：
- DATABASE_URL / SECRET_KEY：签名与数据源，改则所有登录失效，保持环境变量（强约束）
- FX_API_BASE / FX_OFFLINE：汇率源，保留环境变量便于离线联调
其余可在后台「系统参数配置」维护的项（token 时长、微信凭证、爬虫白名单等）
一律走 config_service（DB → 环境变量 → 默认值），不在此处声明，避免双源误导。
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

# 数据目录与数据库
DATA_DIR = Path(os.getenv("XI_DATA_DIR", str(BASE_DIR / "data")))
DATABASE_URL = os.getenv("XI_DATABASE_URL", f"sqlite:///{DATA_DIR / 'xi.db'}")

# JWT 签名密钥
# 生产环境必须用 XI_SECRET_KEY 环境变量覆盖默认值，否则 token 可被伪造！
SECRET_KEY = os.getenv("XI_SECRET_KEY", "dev-secret-change-me-in-production")
# access_token 有效期 / refresh_token 有效期请到 config_service（DB → XI_ACCESS_TOKEN_MINUTES → 120）配置

# 汇率源（frankfurter 免费无 key，备用值见系统配置 fx_fallback_usd/hkd）
FX_API_BASE = os.getenv("XI_FX_API", "https://api.frankfurter.app")

# 置 1 时汇率服务离线（测试环境用）
FX_OFFLINE = os.getenv("XI_FX_OFFLINE", "") == "1"

# 微信小程序 AppID/Secret/Mock 请到 config_service（DB → XI_WX_* → 默认）配置


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
