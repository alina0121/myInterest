# 认证体系 + 账户切换 + 币种筛选 综合改造方案

## Context

当前项目已有 JWT + bcrypt 认证、`/api/auth/wx-login`（小程序端 openId 登录）、`SPECS` 元数据驱动的 `system_configs` KV 表。但仍有 4 个空缺需要补齐：

1. **邮箱验证码登录/注册/找回密码** —— 个人版小程序无法用微信 `getPhoneNumber`，PC 网页端也无微信登录入口。邮箱验证码是替代方案，可用于跨端统一身份、找回密码、把微信账号与邮箱账号打通。
2. **登录相关配置可视化** —— 邮件 SMTP、短信 AK/SK 等敏感配置项要可后台管理，且手机验证码入口默认隐藏（个人版用不到）。
3. **持仓账户切换** —— `mine.vue` 已有 `/pages/accounts/accounts` 菜单入口但页面未实现，`holdings.account` 是字符串字段未做切换 UI。
4. **币种筛选** —— API 不支持 currency 过滤，前端无 UI，用户希望按 CNY/USD/HKD 选择性查看。

目标：用户做完功能后自己去后台 LoginMethods 页配置 SMTP/短信密钥即可启用邮箱验证码、找回密码等服务。

---

## 关键决策（用户已确认）

| 决策点 | 选择 |
|--------|------|
| 账户切换 | **轻量方案**：复用 `holdings.account` 字符串字段，`user_settings.accounts_meta` JSON 存元数据，不建 accounts 表 |
| 登录方式配置页 | **独立 `LoginMethods.vue`**，菜单单独入口 |
| 验证码存储 | **SQLite 表 `verify_codes`**（持久化、跨进程、重启不丢） |
| PC 端微信登录 | **不做**，PC 端只用密码 + 邮箱验证码登录 |
| 短信功能 | 配置先做好 SPECS 框架，`sms_enabled=False` 默认隐藏前端入口，用户自行配置后开启 |

---

## 模块1：openId 登录 + 邮箱验证码登录

### 1.1 数据模型

**新建表 `verify_codes`**（`backend/app/models/verify_code.py`）：
```python
class VerifyCode(SQLModel, table=True):
    __tablename__ = "verify_codes"
    id: Optional[int] = Field(default=None, primary_key=True)
    channel: str          # "email" / "sms"
    target: str           # 邮箱地址或手机号
    code_hash: str        # bcrypt 哈希后的 6 位数字
    purpose: str          # "login" / "register" / "reset" / "bind"
    expires_at: str       # ISO 时间字符串，10 分钟后过期
    consumed_at: Optional[str] = None  # 使用后填，单次有效
    created_at: str = Field(default_factory=now_str)
    # 索引：(channel, target, purpose, consumed_at) 用于查最新未用
```

**User 表无需新字段**（已有 `email`、`wx_openid`）。

`db_init.py` 加 `migrate_verify_codes()` 建表函数，`SCHEMA_VERSION` 7→8。

### 1.2 后端服务

**新建 `backend/app/services/verify_code_service.py`**：
- `generate_and_store(channel, target, purpose) -> str`：生成 6 位数字，bcrypt 哈希后存表，返回明文 code
- `verify(channel, target, code, purpose) -> bool`：查最新未消费且未过期的记录，bcrypt 校验，通过即 `consumed_at=now`，单次使用
- 复用 `backend/app/utils/security.py` 的 `hash_password`/`verify_password`

**新建 `backend/app/services/mail_service.py`**：
- `send_code(target, code, purpose) -> None`：用 `smtplib.SMTP_SSL`，配置取自 `config_service.get_text("smtp_host")` 等
- **通过 FastAPI `BackgroundTasks` 异步发**，失败仅 `log.warning`，不阻塞响应（参考现有 `auto_match_all_background` 模式）
- `mail_enabled=False` 时直接抛 `AppError("邮件服务未开启")`

**新建 `backend/app/services/sms_service.py`**：
- 桩函数 `send_code(target, code, purpose)`，`sms_enabled=False` 时抛 `AppError("短信服务未开启")`
- 真实实现 V2 再补（阿里云/腾讯云 SDK）

### 1.3 API 端点（`backend/app/api/auth.py`）

新增（都复用 `_rate_limit` 限流）：
- `POST /api/auth/send-code` body `{channel, target, purpose}` → 后台任务发信，返回 `{ok:true}`
- `POST /api/auth/email-login` body `{email, code}` → 校验 → 查 email → 返回 token pair；邮箱未注册返回 404 提示先注册
- `POST /api/auth/email-register` body `{email, code, nickname?, password?}` → 校验 → 建 User（username=email）
- `POST /api/auth/reset-password` body `{email, code, new_password}` → 校验 → 改 `password_hash`
- `POST /api/auth/bind-email` body `{email, code}`（需 `get_current_user`）→ 见下方合并流程

现有 `/wx-login` 不变；`/login` 保留密码登录。

### 1.4 邮箱绑定合并流程（关键 SQL 顺序）

用户 A（当前登录，微信账号）绑定邮箱 E，但 E 已被账号 B 使用：

1. 校验 E 的验证码
2. 查 B：`SELECT * FROM users WHERE email=E`
3. 若 B 不存在 → 直接 `UPDATE users SET email=E WHERE id=A.id`，返回成功
4. 若 B 存在 → 单事务合并（注意外键约束顺序）：
   - 处理同名持仓冲突：对每条 A 的 `holdings`，若 B 已有同 `(market, code)` 的持仓，先把 A 的 `lots` 和 `dividends` 迁到 B 的对应持仓下，再 `DELETE FROM holdings WHERE id=A.id`；否则直接 `UPDATE holdings SET user_id=B.id WHERE id=A.id`
   - `UPDATE lots SET user_id=B.id WHERE user_id=A.id`
   - `UPDATE dividends SET user_id=B.id WHERE user_id=A.id`（`dividend_allocations` 通过 `dividend_id` 关联，不动）
   - `UPDATE users SET wx_openid=NULL WHERE id=A.id`（先解绑，避免唯一约束冲突）
   - `UPDATE users SET wx_openid=A.wx_openid, wx_unionid=COALESCE(B.wx_unionid, A.wx_unionid) WHERE id=B.id`
   - `DELETE FROM user_settings WHERE user_id=A.id`（B 已有自己的设置）
   - `DELETE FROM users WHERE id=A.id`
   - commit
5. 返回 B 的新 token pair，前端 `clearAuth()` + `setAuth(new_token, new_user)` 切到 B

### 1.5 前端改造

**移动端 `frontend/src/pages/login/login.vue`**：
- tabs 从 `登录/注册` 改为 `密码 / 邮箱验证码 / 微信`（小程序端最后一项仍条件编译 `#ifdef MP-WEIXIN`）
- 邮箱 tab：邮箱输入框 + 验证码输入框 + "获取验证码"按钮（60 秒倒计时）+ 登录/注册切换
- 新增 `frontend/src/api/index.js` 中：`apiSendCode/apiEmailLogin/apiEmailRegister/apiResetPassword/apiBindEmail`

**PC 端 `frontend-pc/src/views/Login.vue`**：
- tabs 加"邮箱验证码登录"
- "忘记密码"改为弹窗：邮箱 + 验证码 + 新密码三步
- 注册表单的邮箱字段加"验证码"必填项

**移动端 mine.vue 加菜单项**：
- "绑定邮箱" → 弹窗（已绑定则展示，未绑定显示绑定表单）
- 调 `apiBindEmail`

---

## 模块2：邮箱/短信配置管理

### 2.1 SPECS 新增（`backend/app/services/config_service.py`）

**新建分组 "登录方式"**，把现有 `wx_appid`/`wx_secret` 的 `category` 从"安全"改为"登录方式"（仅元数据改动，admin UI 自动重排，无需迁库）。

新增 SPECS：
- `mail_enabled` (bool, False) — 邮件服务总开关
- `smtp_host` (str, "") — SMTP 服务器
- `smtp_port` (int, 465) — SMTP 端口
- `smtp_user` (str, "") — SMTP 用户名
- `smtp_password` (str, sensitive, "") — SMTP 密码
- `smtp_sender` (str, "") — 发件人地址
- `smtp_use_ssl` (bool, True) — 是否用 SSL
- `sms_enabled` (bool, False) — 短信服务总开关
- `sms_provider` (str, "aliyun") — 短信服务商
- `sms_access_key` (str, sensitive, "") — 短信 AK
- `sms_secret` (str, sensitive, "") — 短信 SK
- `sms_sign` (str, "") — 短信签名
- `sms_template_login` (str, "") — 登录验证码模板 ID
- `sms_template_reset` (str, "") — 重置密码模板 ID
- `code_ttl_minutes` (int, 10) — 验证码有效期
- `code_send_interval_sec` (int, 60) — 同目标发送间隔

### 2.2 后端管理 API

`backend/app/api/admin.py` 新增（super_admin only）：
- `POST /api/admin/test-mail` body `{to}` → 用当前 SMTP 配置发一封测试信，返回成功/失败信息

### 2.3 前端管理页

**新建 `frontend-pc/src/views/admin/LoginMethods.vue`**：
- 展示"登录方式"分组的所有 SPECS（复用 `Config.vue` 的渲染逻辑）
- 三个开关：密码登录 / 邮箱验证码 / 微信登录（最后一个是小程序端，PC 端仅展示状态）
- 测试发信按钮 → 调 `/api/admin/test-mail`
- 短信配置区块独立折叠面板，默认收起（强调"未启用"）

**路由注册**：
- `frontend-pc/src/router/index.js` 加 `/admin/login-methods` 路由
- `frontend-pc/src/layouts/AdminLayout.vue` 侧边栏加菜单项"登录方式"

---

## 模块3：账户切换（轻量方案）

### 3.1 数据模型

**`user_settings` 表加列 `accounts_meta TEXT`**（JSON 数组）：
```json
[{"name": "华泰证券", "broker": "华泰", "color": "#3b82f6", "sort": 0, "archived": false}]
```

`db_init.py` 加 `migrate_accounts_meta()` 幂等函数，`SCHEMA_VERSION` 同步到 8。

### 3.2 后端 API

**新建 `backend/app/api/accounts.py`**：
- `GET /api/accounts` → 返回 `[{name, broker, color, archived, holding_count}]`
  - 来源：`SELECT DISTINCT account FROM holdings WHERE user_id=? AND account IS NOT NULL` ∪ `user_settings.accounts_meta`
  - `holding_count` 子查询统计
- `PUT /api/accounts/meta` body `{accounts_meta: [...]}` → 保存到 `user_settings.accounts_meta`

**改造现有 API 加 `?account=xxx` 参数**：
- `backend/app/api/holdings.py` 的 `GET /api/holdings`：值 `__all__` 或具体字符串，SQL `WHERE account=?`
- `backend/app/api/dividends.py`：通过 `holding_id IN (SELECT id FROM holdings WHERE user_id=? AND account=?)` 内存过滤（沿用 dividends.py 现有内存过滤模式）
- `backend/app/services/stats_service.py` 的 `summary()`/`enhanced_summary()`/`by_market()`：加 `account` 参数，收窄 `select(Holding).where(user_id, account)` 后再算

### 3.3 前端

**新建 `frontend/src/pages/accounts/accounts.vue`**（mine.vue 已有入口）：
- 列出账户卡片（来自 `apiAccounts`）
- 支持改色/排序/归档/重命名（操作 `accounts_meta`，调 `apiAccountsMeta`）
- "添加账户"弹窗只填 name+broker+color（纯元数据，不建持仓；下次新建持仓时 account 字段填这个名字）

**`frontend/src/pages/holdings/holdings.vue`**：
- 顶部加横向滚动 tab 条：`全部 / 华泰 / 富途 / ...`
- 选中态切换 `account` 查询参数重新拉列表
- `frontend/src/store/user.js` 加 `currentAccount` 字段持久化到 `uni.setStorageSync`

**PC 端 `frontend-pc/src/views/Holdings.vue`** 同步加账户筛选下拉。

---

## 模块4：币种筛选

### 4.1 数据模型

**`user_settings` 表加列 `visible_currencies TEXT`**（JSON 数组，默认 `["CNY","USD","HKD"]`），`db_init.py` 加 `migrate_visible_currencies()`，`SCHEMA_VERSION` 同步 8。

### 4.2 后端 API

- `GET/PUT /api/settings` 扩展出/入参 `visible_currencies`（在 `SettingsUpdate` schema 加字段）
- `GET /api/holdings`/`dividends`/`stats/enhanced-summary` 加 `?currency=CNY,USD` 参数（逗号分隔），SQL `WHERE Holding.currency IN (...)` 过滤
- stats 收窄后所有金额仍按 `fx_service.to_cny` 折算，但只统计勾选币种的持仓

### 4.3 前端

- `frontend/src/pages/mine/mine.vue` 加菜单"显示币种设置" → 新建 `frontend/src/pages/settings/currency.vue`：
  - `CURRENCIES` 常量（`utils/constants.js` 已有）多选 checkbox
  - 保存调 `apiSaveSettings({visible_currencies})`
- `holdings.vue`/`dividends.vue`/`stats.vue` 加载时从 `apiSettings()` 取 `visible_currencies`，列表渲染前 `filter(h => visible.includes(h.currency))` 兜底
- `frontend/src/store/user.js` 加 `visibleCurrencies` 缓存，登录后预取
- PC 端 `Holdings.vue` 顶部加同样的币种筛选条

---

## 实施步骤（推荐顺序）

1. **后端基础**：新建 `verify_code` 模型 + `db_init` 迁移；新建 `verify_code_service.py`/`mail_service.py`/`sms_service.py`
2. **SPECS 扩展**：在 `config_service.py` 加 16 个新配置项，调整 `wx_appid`/`wx_secret` category
3. **认证 API**：在 `auth.py` 加 5 个新端点（send-code/email-login/email-register/reset-password/bind-email），实现合并流程
4. **账户/币种后端**：`accounts.py` 新建；`holdings.py`/`dividends.py`/`stats_service.py` 加 `account`/`currency` 参数；`user_settings` 迁移加两列
5. **前端移动端**：`login.vue` 改 tabs、`accounts.vue` 新建、`holdings.vue` 加切换条、`mine.vue` 加菜单、`settings/currency.vue` 新建、`store/user.js` 加状态
6. **前端 PC 端**：`Login.vue` 加邮箱验证码 tab + 找回密码弹窗、`LoginMethods.vue` 新建 + 路由注册 + 侧边栏菜单、`Holdings.vue` 加账户/币种筛选
7. **API 封装**：两端 `api/index.js` 加新接口

---

## 关键文件清单

### 后端
- [config_service.py](file:///d:/myProject/myInvestTools/backend/app/services/config_service.py) — SPECS 扩展
- [auth.py](file:///d:/myProject/myInvestTools/backend/app/api/auth.py) — 新增 5 端点
- [db_init.py](file:///d:/myProject/myInvestTools/backend/app/db_init.py) — 迁移到 SCHEMA_VERSION=8
- [holdings.py](file:///d:/myProject/myInvestTools/backend/app/api/holdings.py) — 加 account/currency 参数
- 新建 `backend/app/models/verify_code.py`
- 新建 `backend/app/services/verify_code_service.py`
- 新建 `backend/app/services/mail_service.py`
- 新建 `backend/app/services/sms_service.py`
- 新建 `backend/app/api/accounts.py`

### 前端（移动端）
- [login.vue](file:///d:/myProject/myInvestTools/frontend/src/pages/login/login.vue) — 改 tabs
- [holdings.vue](file:///d:/myProject/myInvestTools/frontend/src/pages/holdings/holdings.vue) — 加账户切换条
- [mine.vue](file:///d:/myProject/myInvestTools/frontend/src/pages/mine/mine.vue) — 加菜单项
- [store/user.js](file:///d:/myProject/myInvestTools/frontend/src/store/user.js) — 加 currentAccount/visibleCurrencies
- [api/index.js](file:///d:/myProject/myInvestTools/frontend/src/api/index.js) — 新增 9 个接口
- 新建 `frontend/src/pages/accounts/accounts.vue`
- 新建 `frontend/src/pages/settings/currency.vue`

### 前端（PC 端）
- [Login.vue](file:///d:/myProject/myInvestTools/frontend-pc/src/views/Login.vue) — 加邮箱验证码 tab + 找回密码弹窗
- 新建 `frontend-pc/src/views/admin/LoginMethods.vue`
- `frontend-pc/src/router/index.js` — 加路由
- `frontend-pc/src/layouts/AdminLayout.vue` — 加菜单
- `frontend-pc/src/views/Holdings.vue` — 加账户/币种筛选

---

## 验证清单

### 后端
- 启动后端，访问 `http://127.0.0.1:8000/docs` 确认新端点出现
- 不配置 SMTP 时调 `/api/auth/send-code` 应返回"邮件服务未开启"
- 后台 LoginMethods 页保存 SMTP 配置后，调 `/api/admin/test-mail` 发测试信
- 邮箱验证码登录：发码 → 登录 → 检查 `verify_codes` 表 `consumed_at` 已填
- 邮箱绑定合并：用 wx 账号 A 登录 → 绑定已被 B 使用的邮箱 → 验证 A 的 holdings 已迁到 B → A 用户已删除 → 用新 token 访问 me 接口
- 账户切换：创建不同 account 的持仓 → `GET /api/holdings?account=华泰` 只返回该账户
- 币种筛选：`PUT /api/settings` 设 `visible_currencies=["CNY"]` → `GET /api/holdings?currency=CNY` 只返回 CNY 持仓

### 前端
- 移动端 login.vue 三 tab 切换正常，邮箱验证码 60 秒倒计时
- 移动端 accounts.vue 增删改色排序
- 移动端 holdings.vue 顶部账户 tab 切换数据
- 移动端 settings/currency.vue 勾选币种后 holdings 列表过滤
- PC 端 LoginMethods.vue 配置 SMTP 后保存，测试发信成功
- PC 端 Holdings.vue 顶部账户/币种筛选联动
