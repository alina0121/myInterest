import { get, post, put, httpPatch, del } from './http'

// ---------- 认证 ----------
export const apiLogin = (account, password) => post('/api/auth/login', { account, password })
export const apiRegister = (payload) => post('/api/auth/register', payload)
export const apiMe = () => get('/api/auth/me')
export const apiLogout = () => post('/api/auth/logout')

// ---------- 持仓 ----------
export const apiHoldings = (params) => get('/api/holdings', params)
export const apiCreateHolding = (payload) => post('/api/holdings', payload)
export const apiHolding = (id) => get(`/api/holdings/${id}`)
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
export const apiSummary = () => get('/api/stats/summary')
export const apiMonthlyTrend = (range = '12m') => get('/api/stats/monthly-trend', { range })
export const apiByMarket = () => get('/api/stats/by-market')
export const apiForecast = () => get('/api/stats/forecast')
export const apiTopHoldings = (limit = 10) => get('/api/stats/top-holdings', { limit })
export const apiYieldRanking = () => get('/api/stats/yield-ranking')
export const apiHoldingStats = (id) => get(`/api/stats/holdings/${id}`)

// ---------- 日历 ----------
export const apiCalendar = (year, month) => get('/api/calendar', { year, month })

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
export const apiAdminCrawl = () => post('/api/admin/schedules/crawl')
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
