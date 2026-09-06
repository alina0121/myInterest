/** 字典常量：市场 / 币种 / 派息频率 / 方向 / 状态 的展示映射 */
export const MARKETS = [
  { value: 'a_share', label: 'A股', color: '#e5484d' },
  { value: 'us_stock', label: '美股', color: '#1668dc' },
  { value: 'hk_stock', label: '港股', color: '#7c3aed' },
  { value: 'fund', label: '基金', color: '#0891b2' },
  { value: 'bond', label: '债券', color: '#b45309' },
]

export const CURRENCIES = [
  { value: 'CNY', label: '人民币 ¥', symbol: '¥' },
  { value: 'USD', label: '美元 $', symbol: '$' },
  { value: 'HKD', label: '港币 HK$', symbol: 'HK$' },
]

export const FREQS = [
  { value: 'monthly', label: '每月' },
  { value: 'quarterly', label: '每季' },
  { value: 'semi_annual', label: '半年' },
  { value: 'annual', label: '每年' },
  { value: 'irregular', label: '不定期' },
  { value: 'unknown', label: '未知' },
]

export const DIRECTIONS = [
  { value: 'buy', label: '买入', color: '#e5484d' },
  { value: 'sell', label: '卖出', color: '#16a34a' },
  { value: 'bonus_share', label: '送转', color: '#b45309' },
]

export const marketMap = Object.fromEntries(MARKETS.map(m => [m.value, m]))
export const currencyMap = Object.fromEntries(CURRENCIES.map(c => [c.value, c]))
export const freqMap = Object.fromEntries(FREQS.map(f => [f.value, f.label]))
export const directionMap = Object.fromEntries(DIRECTIONS.map(d => [d.value, d]))

/** 金额格式化：¥1,676.00 */
export function fmtMoney(n, symbol = '') {
  if (n === null || n === undefined || isNaN(n)) return symbol + '0.00'
  const v = Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return symbol ? symbol + v : v
}

export function cny(n) {
  return '¥' + fmtMoney(n)
}

export function moneyWith(cur, n) {
  const s = currencyMap[cur]?.symbol || ''
  return fmtMoney(n, s)
}
