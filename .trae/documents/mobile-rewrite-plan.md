# 移动端重构计划：对齐 PC 端设计语言

## 背景

移动端（frontend/，uni-app）功能基本齐全但视觉效果与 PC 端差距大：配色不一致（移动 #1668dc vs PC #1e3a8a）、卡片阴影/圆角不统一、市场标签用实心色块而非 PC 的浅底深字风格、WebLayout 仍是侧边栏（PC 已改顶部导航）、缺少即将到账分红/市场占比/意见反馈等功能。

## 阶段一：设计基础层（所有页面依赖）

### 1.1 `App.vue` 全局样式
- 主色 `#1668dc` → `#1e3a8a`，背景 `#f3f6fb` → `#f8fafc`
- 卡片阴影：蓝色调 → 中性 `0 2rpx 6rpx rgba(0,0,0,0.06)`，圆角 `20rpx → 24rpx`
- 按钮渐变 → 纯色 `#1e3a8a`
- 市场标签：实心背景 → 浅底深字（`.tag-a/.tag-us/.tag-hk/.tag-fund`）
- 新增 `.text-amber`、`.badge-confirmed`、`.badge-pending` 工具类

### 1.2 `utils/constants.js`
- MARKETS 颜色对齐 PC（`#dc2626/#2563eb/#059669/#d97706`），新增 `pastel` 字段
- 新增 `badgeClass(market)` 辅助函数
- 新增 `fmtCNY(n)` 导出

### 1.3 `api/index.js` 补齐接口
- `apiUpcoming` → `GET /api/schedules/upcoming`
- `apiSecurities` → `GET /api/schedules/securities`
- `apiMyFeedback` / `apiCreateFeedback`
- `apiLogout`、`apiAnnouncements`

### 1.4 `WebLayout.vue` 侧边栏 → 顶部导航
- 品牌改为「攒息 · 时间的朋友」
- 布局从固定侧边栏改为 60px 吸顶白色导航栏
- 菜单水平排列，激活项 `#1e3a8a` 高亮
- 页面 padding 去掉左侧 224px

### 1.5 `pages.json`
- `tabBar.selectedColor` / `navigationBarBackgroundColor` → `#1e3a8a`

## 阶段二：逐页重写

### 2.1 总览看板 `index.vue`
- **视觉**：顶部渐变 → 纯色 `#1e3a8a`，卡片阴影中性化
- **新增**：即将到账分红列表（`apiUpcoming`，4 条卡片）
- **新增**：各市场分红占比（横向条形图，`apiByMarket`）
- 保留已有：统计卡片、趋势柱状图、派息节奏、最近到账

### 2.2 持仓列表 `holdings.vue`
- **视觉**：`#1668dc` → `#1e3a8a`，标签用 `badgeClass()`，阴影中性
- **新增**：本年分红 + 累计分红两个指标格
- 保留：搜索、市场筛选、卡片列表、FAB 新增按钮

### 2.3 持仓新增 `holdings/add.vue`
- **新增**：证券搜索选择（`apiSecurities`），选中后自动填充市场/代码/名称/币种
- **新增**：参考最新价提示
- MP-WEIXIN 用 `<picker>`，H5 用搜索输入 + 下拉

### 2.4 持仓详情 `holdings/detail.vue`
- **视觉**：hero 渐变 → `#1e3a8a`，tab 高亮色对齐
- **新增**：第三个 Tab「年度统计」（`apiHoldingStats`）
- **新增**：分红归属说明提示框
- **新增**：派息频率长按编辑（`apiUpdateHolding`）

### 2.5 分红列表 `dividends/list.vue`
- **视觉**：chip/tab 色对齐，状态徽章用 class
- **新增**：市场筛选 chip 行
- **新增**：分页（每页 20 条 + 上拉加载更多）

### 2.6 分红新增 `dividends/add.vue`
- 微调配色，保留现有逻辑（已与 PC 对齐）

### 2.7 日历 `calendar.vue`
- **视觉**：导航/高亮色对齐
- **新增**：本月分红流水时间线（所有日条目按日期排列）

### 2.8 统计 `stats.vue`
- **视觉**：条形图配色对齐，标签用 `badgeClass()`
- **新增**：CSS 圆环图（`conic-gradient`）展示市场占比
- **新增**：成本 vs 现价股息率双条对比
- 保留：年度趋势、Top10 排行、预测柱状图

### 2.9 我的 `mine.vue`
- **视觉**：profile 渐变 → `#1e3a8a`，switch 色对齐
- **新增**：统计分析入口（菜单行链接 `/pages/stats/stats`）
- **新增**：意见反馈区（textarea + 提交 + 历史列表）
- **新增**：角色显示、退出调 `apiLogout()`

### 2.10 登录 `login.vue`
- 配色微调：渐变/激活色 `#1668dc` → `#1e3a8a`

## 验证方式
1. `npm run dev:h5` 启动 H5，浏览器移动模拟器逐页检查
2. `npm run build:mp-weixin` 编译小程序，微信开发者工具预览
3. 核对点：配色一致、市场标签浅底深字、WebLayout 顶部导航、新功能数据正常加载
