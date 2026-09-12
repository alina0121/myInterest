import { get, post, put, httpPatch, del } from './http'

// ---------- 认证 ----------
// 登录页调用时本地无 token，HTTP 拦截器自动跳过 Authorization 头
export const apiLogin = (account, password) => post('/api/auth/login', { account, password })
export const apiRegister = (payload) => post('/api/auth/register', payload)
// 邮箱验证码：send-code/email-login/email-register/reset-password 为游客态调用；
// bind-email 需登录态（自动带 token）
export const apiSendCode = (channel, target, purpose) =>
  post('/api/auth/send-code', { channel, target, purpose })
export const apiEmailLogin = (email, code) =>
  post('/api/auth/email-login', { email, code })
export const apiEmailRegister = (payload) =>
  post('/api/auth/email-register', payload)
export const apiResetPassword = (email, code, newPassword) =>
  post('/api/auth/reset-password', { email, code, new_password: newPassword })
export const apiBindEmail = (email, code) =>
  post('/api/auth/bind-email', { email, code })
export const apiMe = () => get('/api/auth/me')
export const apiLogout = () => post('/api/auth/logout')

// ---------- 账户管理（v8：账户元数据 + 持仓聚合） ----------
export const apiAccounts = () => get('/api/accounts')
export const apiAccountsMeta = (accounts_meta) => put('/api/accounts/meta', { accounts_meta })

// ---------- 持仓 ----------
export const apiHoldings = (params) => get('/api/holdings', params)
export const apiCreateHolding = (payload) => post('/api/holdings', payload)
export const apiHolding = (id) => get(`/api/holdings/${id}`)
export const apiUpdateHolding = (id, payload) => httpPatch(`/api/holdings/${id}`, payload)
export const apiDeleteHolding = (id) => del(`/api/holdings/${id}`)
export const apiLots = (id) => get(`/api/holdings/${id}/lots`)
export const apiCreateLot = (id, payload) => post(`/api/holdings/${id}/lots`, payload)
export const apiCreateLotsBatch = (id, lots) => post(`/api/holdings/${id}/lots/batch`, { lots })
export const apiUpdateLot = (lotId, payload) => httpPatch(`/api/lots/${lotId}`, payload)
export const apiDeleteLot = (lotId) => del(`/api/lots/${lotId}`)

// ---------- 分红 ----------
export const apiDividends = (params) => get('/api/dividends', params)
export const apiCreateDividend = (payload) => post('/api/dividends', payload)
export const apiCreateDividendsBatch = (dividends) => post('/api/dividends/batch', { dividends })

// ---------- 统计 ----------
export const apiSummary = (params = {}) => get('/api/stats/summary', params)
export const apiEnhancedSummary = (params = {}) => get('/api/stats/enhanced-summary', params)
export const apiDashboardMetrics = () => get('/api/stats/dashboard-metrics')
export const apiSaveDashboardMetrics = (selected) => put('/api/stats/dashboard-metrics', { selected })
export const apiMonthlyTrend = (range = '12m', params = {}) => get('/api/stats/monthly-trend', { range, ...params })
export const apiByMarket = (params = {}) => get('/api/stats/by-market', params)
export const apiForecast = (params = {}) => get('/api/stats/forecast', params)
export const apiTopHoldings = (limit = 10, params = {}) => get('/api/stats/top-holdings', { limit, ...params })
export const apiYieldRanking = (params = {}) => get('/api/stats/yield-ranking', params)
export const apiHoldingStats = (id, params = {}) => get(`/api/stats/holdings/${id}`, params)

// ---------- 日历 ----------
export const apiCalendar = (year, month, params = {}) => get('/api/calendar', { year, month, ...params })

// ---------- 预案（用户端） ----------
export const apiUpcoming = () => get('/api/schedules/upcoming')
export const apiSchedules = (params) => get('/api/schedules', params)
export const apiSecurities = (params) => get('/api/schedules/securities', params)
export const apiSubmitSchedule = (payload) => post('/api/schedules', payload)

// ---------- 公告/反馈 ----------
export const apiAnnouncements = () => get('/api/announcements')
export const apiMyFeedback = () => get('/api/feedback/me')
export const apiCreateFeedback = (content) => post('/api/feedback', { content })

// ---------- 设置 ----------
export const apiRates = () => get('/api/rates')
export const apiSettings = () => get('/api/settings')
export const apiSaveSettings = (payload) => put('/api/settings', payload)

// ================= 管理后台 =================
export const apiAdminOverview = () => get('/api/admin/stats/overview')
export const apiAdminUsers = (params) => get('/api/admin/users', params)
export const apiAdminUserData = (id) => get(`/api/admin/users/${id}/data`)
export const apiAdminBanUser = (id) => post(`/api/admin/users/${id}/ban`)
export const apiAdminUnbanUser = (id) => post(`/api/admin/users/${id}/unban`)
export const apiAdminResetPwd = (id) => post(`/api/admin/users/${id}/reset-password`)
export const apiAdminSchedules = (params) => get('/api/admin/schedules', params)
export const apiAdminCreateSchedule = (payload) => post('/api/admin/schedules', payload)
export const apiAdminApproveSchedule = (id) => post(`/api/admin/schedules/${id}/approve`)
export const apiAdminRejectSchedule = (id, reason) => post(`/api/admin/schedules/${id}/reject`, { reason })
export const apiAdminBatchApprove = (ids, action, reason) =>
  post('/api/admin/schedules/batch-approve', { ids, action, reason })
export const apiAdminCrawl = (market) =>
  post(`/api/admin/schedules/crawl${market ? `?market=${market}` : ''}`)
// 证券管理（爬虫白名单）
export const apiAdminSecurities = (params) => get('/api/admin/securities', params)
export const apiAdminCreateSecurity = (payload) => post('/api/admin/securities', payload)
export const apiAdminToggleCrawlEnabled = (id, enabled) =>
  httpPatch(`/api/admin/securities/${id}/crawl-enabled?enabled=${enabled}`, {})
export const apiAdminRates = () => get('/api/admin/rates')
export const apiAdminCreateRate = (payload) => post('/api/admin/rates', payload)
export const apiAdminRefreshRates = () => post('/api/admin/rates/refresh')
export const apiAdminTaxRules = () => get('/api/admin/tax-rules')
export const apiAdminUpdateTaxRule = (id, payload) => put(`/api/admin/tax-rules/${id}`, payload)
export const apiAdminCreateAnnouncement = (payload) => post('/api/admin/announcements', payload)
export const apiAdminUpdateAnnouncement = (id, payload) => httpPatch(`/api/admin/announcements/${id}`, payload)
export const apiAdminFeedback = (params) => get('/api/admin/feedback', params)
export const apiAdminHandleFeedback = (id, payload) => httpPatch(`/api/admin/feedback/${id}`, payload)
export const apiAdminLogs = (params) => get('/api/admin/logs', params)

// ---------- 系统配置（仅 super_admin 可写，admin 只读） ----------
export const apiAdminConfig = () => get('/api/admin/config')
export const apiAdminUpdateConfig = (items) => put('/api/admin/config', { items })
export const apiAdminResetConfig = (key) => del(`/api/admin/config/${key}`)
