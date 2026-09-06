/** API 模块：与 docs/04-接口文档.md 一一对应 */
import { get, post, patch, del, put } from '@/utils/request'

// ---------- 认证 ----------
export const apiLogin = (account, password) =>
  post('/api/auth/login', { account, password }, { auth: false })
export const apiRegister = (payload) => post('/api/auth/register', payload, { auth: false })
export const apiWxLogin = (code, nickname, avatar) =>
  post('/api/auth/wx-login', { code, nickname, avatar }, { auth: false })
export const apiMe = () => get('/api/auth/me')

// ---------- 持仓 ----------
export const apiHoldings = (params = {}) => get('/api/holdings', params)
export const apiHoldingDetail = (id) => get(`/api/holdings/${id}`)
export const apiCreateHolding = (payload) => post('/api/holdings', payload)
export const apiUpdateHolding = (id, payload) => patch(`/api/holdings/${id}`, payload)
export const apiDeleteHolding = (id) => del(`/api/holdings/${id}`)

// ---------- 批次 ----------
export const apiLots = (holdingId) => get(`/api/holdings/${holdingId}/lots`)
export const apiCreateLot = (holdingId, payload) =>
  post(`/api/holdings/${holdingId}/lots`, payload)
export const apiDeleteLot = (lotId) => del(`/api/lots/${lotId}`)

// ---------- 分红 ----------
export const apiDividends = (params = {}) => get('/api/dividends', params)
export const apiDividendDetail = (id) => get(`/api/dividends/${id}`)
export const apiCreateDividend = (payload) => post('/api/dividends', payload)
export const apiConfirmDividend = (id, actualNet) =>
  post(`/api/dividends/${id}/confirm`, { actual_net: actualNet })
export const apiDeleteDividend = (id) => del(`/api/dividends/${id}`)

// ---------- 统计 / 日历 / 设置 ----------
export const apiSummary = () => get('/api/stats/summary')
export const apiMonthlyTrend = (range = '12m') => get('/api/stats/monthly-trend', { range })
export const apiByMarket = () => get('/api/stats/by-market')
export const apiForecast = () => get('/api/stats/forecast')
export const apiTopHoldings = () => get('/api/stats/top-holdings')
export const apiYieldRanking = () => get('/api/stats/yield-ranking')
export const apiHoldingStats = (id) => get(`/api/stats/holdings/${id}`)
export const apiCalendar = (year, month) => get('/api/calendar', { year, month })
export const apiSettings = () => get('/api/settings')
export const apiSaveSettings = (payload) => put('/api/settings', payload)
export const apiRates = (date) => get('/api/rates', date ? { date } : {})
