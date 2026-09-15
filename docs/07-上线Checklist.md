# 07 · 上线 Checklist

> 面向 2核2G 个人服务器 + 个人域名部署。覆盖主体合规、配置加固、部署资产、发布前自检四部分。
> 当前基线：v0.3（分红实时计算重构：PC/H5 独立端 + 美股/港股/基金爬虫 + 多市场行情）。
> 若从 v0.2.0 升级，注意查看 §7 的 v0.3 迁移说明（DROP 旧表 + 手动分红数据影响）。

---

## 0. 资源与定位结论（先看这一条）

| 维度 | 结论 |
|---|---|
| 2核2G 服务器 | ✅ 足够。FastAPI 常驻 ~80MB + SQLite ~5MB + Caddy ~20MB，余量充足；可承几百到上千日活 |
| 个人 ICP 备案 | ✅ 可办。备案定位必须写「个人记账工具 / 数据记录」，**禁止**出现「投资咨询/荐股/理财/收益承诺」字眼 |
| 微信小程序主体 | ⚠️ 个人主体类目受限，「记账理财」类通常需企业/个体户主体。建议注册个体工商户（成本几百元），或先只发 H5+App |
| 代码功能完整度 | ✅ P0+P1+v1.1 均已完成，达到上线标准 |
| HTTPS | ✅ 必须。小程序强制 HTTPS + 备案域名，用 Caddy 自动签发 Let's Encrypt |

---

## 1. 主体与备案（最先做，周期最长）

### 1.1 ICP 备案（7–20 工作日）
- [ ] 服务器购买（阿里云/腾讯云，2核2G，地域选国内）
- [ ] 域名注册（.com / .cn 均可，个人可注册）
- [ ] 提交 ICP 备案，主体类型选「个人」
- [ ] 网站名称/备注填「个人记账工具」「数据记录」类中性表述
- [ ] 备案通过，拿到 ICP 备案号
- [ ] 网站底部悬挂备案号 + 公安备案（如需）

### 1.2 微信小程序（如需发小程序端）
- [ ] 决定主体：个人 or 个体工商户（推荐后者）
- [ ] 注册小程序账号，拿 AppID
- [ ] 类目选择「工具 - 记账」（**禁止**「金融/投资/荐股」类目）
- [ ] 小程序后台「开发管理」配置 request 合法域名（API 域名，HTTPS）
- [ ] 内容合规自检：文案不出现「推荐买入/保证收益/内部消息」等，定位「个人记账」
- [ ] 提审前在开发者工具勾选「不校验域名」本地联调

### 1.3 应用市场（如需发 App 端）
- [ ] HBuilderX 云打包 APK（Android）
- [ ] 应用宝/华为/小米应用市场注册个人开发者
- [ ] 应用描述定位「记账工具」，不上架 iOS 个人（需企业 99 美元账号）可暂缓

---

## 2. 服务器初始化

- [ ] SSH 密钥登录，禁用 root 密码登录
- [ ] 防火墙：仅开放 22(SSH)/80(http)/443(https)
- [ ] 创建非 root 部署用户 `deploy`
- [ ] 安装基础环境：Python 3.11+、Node 18+、git、Caddy、ufw
- [ ] 配置 swap（2G 内存建议加 2G swap 防突发）
- [ ] 时区设为 `Asia/Shanghai`，NTP 同步（爬虫/定时任务依赖准确时间）

---

## 3. 代码与依赖部署

### 3.1 拉代码 + 虚拟环境
- [ ] `git clone` 项目到 `/opt/myinvesttools`
- [ ] `cd backend && python -m venv .venv && source .venv/bin/activate`
- [ ] `pip install -r requirements.txt`
- [ ] `cd frontend && npm install`
- [ ] `cd frontend-pc && npm install`

### 3.2 前端构建（非开发模式跑 dev）
- [ ] 移动端 H5：`npm run build:h5` → 产物在 `frontend/dist/build/h5/`
- [ ] PC 端：`npm run build` → 产物在 `frontend-pc/dist/`
- [ ] 微信小程序：HBuilderX 或 `npm run build:mp-weixin`，用微信开发者工具上传

### 3.3 后端环境变量（**关键，不可漏**）
创建 `backend/.env`（已 `.gitignore`），内容：

```bash
# JWT 密钥：32+ 位随机字符串，严禁用默认值
XI_SECRET_KEY=<openssl rand -hex 32 生成>

# 数据库路径（默认即 data/xi.db，可不改）
# XI_DATABASE_URL=sqlite:////opt/myinvesttools/backend/data/xi.db

# 微信小程序（不发小程序可留空）
XI_WX_APPID=<你的 AppID>
XI_WX_SECRET=<你的 Secret>
XI_WX_MOCK=0   # 上线必须设 0，开发态才用 1

# 美股数据源
XI_AV_API_KEY=<你的 Alpha Vantage Key>

# 汇率（默认 frankfurter 免费，可不改）
# XI_FX_API=https://api.frankfurter.app
# XI_FX_OFFLINE=
```

---

## 4. 配置加固（上线前必改项）

| 项 | 现状（开发态） | 上线要求 |
|---|---|---|
| `SECRET_KEY` | 默认 `dev-secret-change-me-in-production` | **必须**环境变量覆盖为随机32+字符 |
| CORS `allow_origins` | `["*"]` 全放开 | 改为具体域名白名单，如 `["https://你的域名.com"]` |
| `WX_MOCK` | 默认 `1` | **必须**设 `0`（配真实 AppID/Secret） |
| 邮件 SMTP | 后台可配 | 在「系统参数配置」填 SMTP host/port/user/pass |
| 短信服务 | 后台可配（默认隐藏） | 如启用，填短信平台密钥 |
| 汇率源 | frankfurter 免费 | 保持默认即可，无需 key |
| 爬虫白名单 | securities.crawl_enabled 字段控制 | 后台「证券管理」页勾选要爬的标的 |

**CORS 修改位置**：[main.py](file:///d:/myProject/myInvestTools/backend/app/main.py) 第 38-39 行

---

## 5. 反向代理与 HTTPS

### 5.1 Caddy 配置（推荐，自动证书）
`/etc/caddy/Caddyfile`：

```caddyfile
你的域名.com {
    # PC 端静态托管
    handle /pc/* {
        root * /opt/myinvesttools/frontend-pc/dist
        uri strip_prefix /pc
        file_server
        try_files {path} /index.html
    }

    # 移动端 H5 静态托管
    handle /m/* {
        root * /opt/myinvesttools/frontend/dist/build/h5
        uri strip_prefix /m
        file_server
        try_files {path} /index.html
    }

    # API 反代到后端
    handle /api/* {
        reverse_proxy 127.0.0.1:8000
    }

    # 后台（如用 sqladmin）
    handle /admin/* {
        reverse_proxy 127.0.0.1:8000
    }

    # 根路径默认到 PC 端
    handle {
        root * /opt/myinvesttools/frontend-pc/dist
        file_server
        try_files {path} /index.html
    }
}
```

- [ ] 替换 `你的域名.com` 为实际域名
- [ ] `caddy validate --config /etc/caddy/Caddyfile` 校验
- [ ] `systemctl restart caddy`
- [ ] 浏览器访问 `https://你的域名.com`，证书自动签发

### 5.2 前端 baseURL 调整
- [ ] `frontend/src/utils/config.js`：移动端 baseURL 改为 `https://你的域名.com/api`
- [ ] `frontend-pc/vite.config.js`：生产构建走同源 `/api`，无需改
- [ ] 微信小程序：后台「开发管理」配置 request 合法域名

---

## 6. 进程守护（systemd）

`/etc/systemd/system/myinvesttools.service`：

```ini
[Unit]
Description=MyInvestTools FastAPI
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/myinvesttools/backend
EnvironmentFile=/opt/myinvesttools/backend/.env
ExecStart=/opt/myinvesttools/backend/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> ⚠️ `--workers 1` 是硬约束：SQLite 单写者，多 worker 会写锁冲突。

- [ ] `systemctl daemon-reload`
- [ ] `systemctl enable --now myinvesttools`
- [ ] `systemctl status myinvesttools` 确认 active
- [ ] `curl http://127.0.0.1:8000/api/health` 返回 `{"code":0,...}`

---

## 7. 数据库与备份

- [ ] 首次启动后端自动 `init_db()` 建表
- [ ] 跑 `python scripts/seed_demo.py` 灌入演示数据（或直接用线上空库）
- [ ] 配置定时备份（crontab）：

```bash
# 每日凌晨 3 点备份 SQLite，保留 30 天
0 3 * * * cp /opt/myinvesttools/backend/data/xi.db \
    /opt/myinvesttools/backend/backups/xi-$(date +\%Y\%m\%d).db && \
    find /opt/myinvesttools/backend/backups -mtime +30 -delete
```

- [ ] 手动跑一次备份命令验证路径存在

### 迁移（v0.2.0 → v0.3.0，分红实时计算重构）
v0.3 删除了 `dividends` / `dividend_allocations` 两张落表，分红改为由 `dividend_schedules`(预案) + `lots`(批次) **实时派生**，不再落库。后端 `init_db()` 只调 `create_all`（不会 DROP 已存在表），因此旧表会残留，需手动清理：

```bash
# 在服务器后端目录执行（先停服务，防写锁）
sqlite3 data/xi.db "PRAGMA foreign_keys=OFF;
DROP TABLE IF EXISTS dividends;
DROP TABLE IF EXISTS dividend_allocations;
PRAGMA foreign_keys=ON;"
# 若系统未装 sqlite3 CLI，可用 python：
python - <<'PY'
import sqlite3; c = sqlite3.connect('data/xi.db')
c.execute('PRAGMA foreign_keys=OFF')
for t in ('dividends','dividend_allocations'):
    c.execute(f'DROP TABLE IF EXISTS {t}')
c.execute('PRAGMA user_version=9')  # 标记已迁移到 v0.3 schema
c.commit(); c.close()
PY
```

> ⚠️ 业务影响：旧库 `dividends` 表里已有的手动录入分红记录在 v0.3 下**不再被读取**。升级前如需保留，建议先到后台导出/备份该表数据；否则视为清洗重建（用户分红一律按预案+持仓实时算出，无丢失风险）。

---

## 8. 定时任务与爬虫

后端启动时 APScheduler 自动起（见 [scheduler.py](file:///d:/myProject/myInvestTools/backend/app/scheduler.py)），无需额外配置：

- [ ] 汇率每日更新（frankfurter）
- [ ] 爬虫调度（A 股东财、港股腾讯行情、基金天天基金、美股 Alpha Vantage）
- [ ] v0.3：已**移除**「分红预告自动匹配成 pending 分红」任务——分红全部按预案+持仓实时计算，无落表任务

> 美股爬虫需先在后台「系统参数配置」填入 `av_api_key`（Alpha Vantage），否则美股爬取直接跳过。见 [crawler_service.py](file:///d:/myProject/myInvestTools/backend/app/services/crawler_service.py) `crawl_us_stock`。

验证：
- [ ] 后端日志无 APScheduler 报错
- [ ] 后台「调度管理」页可手动触发各市场爬取
- [ ] 美股 `av_api_key` 已配置后可拉出精确历史分红（`DIVIDENDS` 接口）

---

## 9. 上线前功能自检（用 demo 账号）

访问 `https://你的域名.com`，用 `demo/demo123456` 登录，逐项验证：

### 9.1 用户端
- [ ] 登录/退出正常
- [ ] 概览页（Dashboard）：统计卡片有数据
- [ ] 持仓页：列表展示，可筛选市场/账户
- [ ] 持仓详情：多批次展示，成本/市值/浮动盈亏正确
- [ ] 分红页：列表 + 分页，可按年/市场筛选；（v0.3 只读）展开可见批次归属明细，**无**「记一笔分红/手动录入」按钮
- [ ] 日历页：分红日期正确标注
- [ ] 统计页：图表渲染，YoC/股息率正确
- [ ] 设置页：币种切换、账户管理、邮箱绑定

### 9.2 运营后台（用 `admin/password123`）
- [ ] 登录入口：头像 →「运营后台」
- [ ] 运营看板：指标卡有数据
- [ ] 证券管理：白名单 `crawl_enabled` 开关可切
- [ ] 调度管理：分市场爬取按钮可点，分页正常
- [ ] 系统参数配置：邮件/短信/微信三卡片
- [ ] 用户管理：只读访问用户数据
- [ ] 操作日志：写操作有记录

### 9.3 三端联通
- [ ] PC 端（`https://你的域名.com`）
- [ ] 移动端 H5（`https://你的域名.com/m/`）
- [ ] 微信小程序（如发布）：登录静默授权 + 昵称头像

### 9.4 权限与安全
- [ ] 未登录访问 `/api/holdings` 返回 401
- [ ] demo 用户访问 `/api/admin/*` 返回 403
- [ ] 越权访问他人 holding_id 返回 404（不暴露资源存在性）
- [ ] `XI_SECRET_KEY` 已改非默认值
- [ ] CORS 已收紧到具体域名

---

## 10. 监控与运维

- [ ] 配置日志轮转（systemd 自带 journal，或后端日志落文件 + logrotate）
- [ ] 简单监控：cron 每分钟 `curl /api/health`，失败发邮件/Server酱
- [ ] 磁盘告警：SQLite + 备份会增长，监控磁盘使用率 > 80%
- [ ] 内存告警：2G 机器关注 OOM，必要时加 swap 或升配

---

## 11. 上线日操作顺序

1. 域名解析 A 记录指向服务器 IP
2. `systemctl start caddy`（自动签发 HTTPS 证书）
3. `systemctl start myinvesttools`
4. `curl https://你的域名.com/api/health` 确认 200
5. 浏览器打开站点，用 demo 账号走一遍 §9 自检
6. 微信小程序后台配置 request 合法域名，提审
7. 备份 cron 生效，次日检查 `backups/` 有文件

---

## 12. 已知风险与应对

| 风险 | 概率 | 应对 |
|---|---|---|
| 微信小程序个人主体类目被拒 | 高 | 注册个体户主体，或先发 H5+App |
| 备案名称含「投资/理财」被驳回 | 中 | 严格用「个人记账工具」表述 |
| SQLite 写锁等待（用户上千后） | 低 | 监控 `busy_timeout` 日志，触发即迁 PostgreSQL（改连接串） |
| 爬虫被源站限流 | 中 | 后台调 `crawl_*_sleep`，降频；白名单精简 |
| Alpha Vantage 免费额度（500/天） | 中 | 美股白名单控制 ≤ 5 只，每日 1 次足够 |
| 2G 内存 OOM | 低 | 加 swap、限制爬虫并发、必要时升 2核4G |

---

## 13. 回滚预案

- [ ] 代码保留上一稳定版本 tag，可快速 `git checkout` 回滚
- [ ] 每日 SQLite 备份可单独启动旧代码 + 旧库
- [ ] 数据库 schema 变更必须有迁移脚本（见 02 文档），不可直接改表

---

## 附录：部署资产清单（需补齐）

当前项目**缺失**以下部署资产，建议上线前补齐：

| 资产 | 路径建议 | 用途 |
|---|---|---|
| Dockerfile | `backend/Dockerfile` | 容器化部署（可选） |
| docker-compose.yml | 根目录 | 一键起服务（可选） |
| Caddyfile 示例 | `deploy/Caddyfile` | 反代配置模板 |
| systemd service | `deploy/myinvesttools.service` | 进程守护 |
| 部署脚本 | `deploy/deploy.sh` | 一键部署/更新 |
| 备份脚本 | `deploy/backup.sh` | SQLite 定时备份 |

> 是否补齐这些资产，取决于你倾向哪种部署方式（裸机 systemd vs Docker）。确定后我可以直接生成对应文件。
