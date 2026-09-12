/** 市场与币种常量（与 uni-app 端 constants 一致） */
export const MARKETS = [
  { value: 'a_share', label: 'A股', color: '#dc2626' },
  { value: 'us_stock', label: '美股', color: '#2563eb' },
  { value: 'hk_stock', label: '港股', color: '#059669' },
  { value: 'fund', label: '基金', color: '#d97706' },
]

export const marketMap = Object.fromEntries(MARKETS.map((m) => [m.value, m]))

/** 币种字典：数组形式（便于 settings/currency 页面 v-for 渲染） */
export const CURRENCIES = [
  { value: 'CNY', label: '人民币 ¥', symbol: '¥' },
  { value: 'USD', label: '美元 $', symbol: '$' },
  { value: 'HKD', label: '港币 HK$', symbol: 'HK$' },
]

export const currencyMap = Object.fromEntries(
  CURRENCIES.map((c) => [c.value, c]),
)

export const FREQS = [
  { value: 'unknown', label: '未知' },
  { value: 'monthly', label: '月派' },
  { value: 'quarterly', label: '季派' },
  { value: 'semi_annual', label: '半年派' },
  { value: 'annual', label: '年派' },
  { value: 'irregular', label: '不定期' },
]

export const freqMap = Object.fromEntries(FREQS.map((f) => [f.value, f.label]))

export function fmt(n, digits = 2) {
  return Number(n || 0).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function fmtCNY(n) {
  return '¥ ' + fmt(n)
}

/** v8：按显示币种带符号格式化金额
 * displayCurrency: 'CNY' / 'USD' / 'HKD' / 'ORIGINAL'
 * ORIGINAL 模式：金额是各市场原币种，需传 originalCurrency 决定符号
 * （聚合统计页后端已把 ORIGINAL 回落 CNY，所以只有单条分红/单持仓详情会走 ORIGINAL 分支）
 */
export function fmtDisplay(n, displayCurrency = 'CNY', originalCurrency = null) {
  if (n === null || n === undefined) return '—'
  const symbols = { CNY: '¥', USD: '$', HKD: 'HK$' }
  // ORIGINAL 模式：用单条记录的原币种符号
  if (displayCurrency === 'ORIGINAL' && originalCurrency) {
    return (symbols[originalCurrency] || '¥') + fmt(n)
  }
  const sym = symbols[displayCurrency] || '¥'
  return sym + fmt(n)
}

/** 按币种带符号格式化金额 */
export function moneyWith(currency, n) {
  const c = currencyMap[currency]
  if (!c) return fmt(n)
  return `${c.symbol}${fmt(n)}`
}
