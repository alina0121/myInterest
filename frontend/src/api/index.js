/** API 模块：与 PC 端 api/index.js 对齐 */
import { get, post, patch, del, put } from '@/utils/request'

// ---------- 认证 ----------
export const apiLogin = (account, password) =>
  post('/api/auth/login', { account, password }, { auth: false })
export const apiRegister = (payload) => post('/api/auth/register', payload, { auth: false })
export const apiWxLogin = (code, nickname, avatar) =>
  post('/api/auth/wx-login', { code, nickname, avatar }, { auth: false })
export const apiMe = () => get('/api/auth/me')
export const apiLogout = () => post('/api/auth/logout')

// ---------- 持仓 ----------
export const apiHoldings = (params = {}) => get('/api/holdings', params)
export const apiHoldingDetail = (id) => get(`/api/holdings/${id}`)
export const apiHolding = (id) => get(`/api/holdings/${id}`)
export const apiCreateHolding = (payload) => post('/api/holdings', payload)
export const apiUpdateHolding = (id, payload) => patch(`/api/holdings/${id}`, payload)
export const apiDeleteHolding = (id) => del(`/api/holdings/${id}`)

// ---------- 批次 ----------
export const apiLots = (holdingId) => get(`/api/holdings/${holdingId}/lots`)
export const apiCreateLot = (holdingId, payload) =>
  post(`/api/holdings/${holdingId}/lots`, payload)
export const apiCreateLotsBatch = (holdingId, lots) =>
  post(`/api/holdings/${holdingId}/lots/batch`, { lots })
export const apiUpdateLot = (lotId, payload) => patch(`/api/lots/${lotId}`, payload)
export const apiDeleteLot = (lotId) => del(`/api/lots/${lotId}`)

// ---------- 分红 ----------
export const apiDividends = (params = {}) => get('/api/dividends', params)
export const apiDividendDetail = (id) => get(`/api/dividends/${id}`)
export const apiCreateDividend = (payload) => post('/api/dividends', payload)
export const apiCreateDividendsBatch = (dividends) => post('/api/dividends/batch', { dividends })
export const apiConfirmDividend = (id, actualNet) =>
  post(`/api/dividends/${id}/confirm`, { actual_net: actualNet })
export const apiDeleteDividend = (id) => del(`/api/dividends/${id}`)

// ---------- 统计 / 日历 / 设置 ----------
export const apiSummary = () => get('/api/stats/summary')
export const apiMonthlyTrend = (range = '12m') => get('/api/stats/monthly-trend', { range })
export const apiByMarket = () => get('/api/stats/by-market')
export const apiForecast = () => get('/api/stats/forecast')
export const apiTopHoldings = (limit = 10) => get('/api/stats/top-holdings', { limit })
export const apiYieldRanking = () => get('/api/stats/yield-ranking')
export const apiHoldingStats = (id) => get(`/api/stats/holdings/${id}`)
export const apiCalendar = (year, month) => get('/api/calendar', { year, month })

// ---------- 预案（用户端） ----------
export const apiUpcoming = () => get('/api/schedules/upcoming')
export const apiSchedules = (params) => get('/api/schedules', params)
export const apiSecurities = (params) => get('/api/schedules/securities', params)
export const apiSubmitSchedule = (payload) => post('/api/schedules', payload)

// ---------- 公告 / 反馈 ----------
export const apiAnnouncements = () => get('/api/announcements')
export const apiMyFeedback = () => get('/api/feedback/me')
export const apiCreateFeedback = (content) => post('/api/feedback', { content })

// ---------- 设置 ----------
export const apiSettings = () => get('/api/settings')
export const apiSaveSettings = (payload) => put('/api/settings', payload)
export const apiRates = (date) => get('/api/rates', date ? { date } : {})
