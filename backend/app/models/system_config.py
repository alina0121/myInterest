"""system_configs 系统配置表：通用 key-value 存储。

设计要点（元数据驱动）：
- 表里只保存被管理员改过的【值】；配置项的名称、分组、类型、说明、默认值、
  取值范围等元数据统一定义在 services/config_service.py 的 SPECS 中。
- 好处：新增一个配置项只需在 SPECS 加一条，无需建表/迁库；未改过的配置
  永远走默认值（默认值还可以动态取自环境变量）。
- value 一律以字符串存：bool 存 "1"/"0"，int/float 存数字文本，
  列表（如美股白名单）存逗号分隔文本，由 config_service 负责类型转换与校验。
"""
from typing import Optional

from sqlmodel import Field, SQLModel

from ..utils.timeutil import now_str


class SystemConfig(SQLModel, table=True):
    __tablename__ = "system_configs"

    # 配置键，对应 config_service.SPECS 的 key，如 crawl_a_share_page_size
    config_key: str = Field(primary_key=True, max_length=64)
    config_value: Optional[str] = None   # 配置值（统一字符串口径）；NULL/删行=回退默认
    updated_at: str = Field(default_factory=now_str)        # 最后修改时间
    updated_by: Optional[int] = None     # 修改人 user_id（super_admin），便于审计
