/** 字典常量：市场 / 币种 / 派息频率 / 方向 / 状态 的展示映射（对齐 PC 端） */
export const MARKETS = [
  { value: 'a_share', label: 'A股', color: '#dc2626', pastel: '#fef2f2' },
  { value: 'us_stock', label: '美股', color: '#2563eb', pastel: '#eff6ff' },
  { value: 'hk_stock', label: '港股', color: '#059669', pastel: '#ecfdf5' },
  { value: 'fund', label: '基金', color: '#d97706', pastel: '#fffbeb' },
  { value: 'bond', label: '债券', color: '#7c3aed', pastel: '#f5f3ff' },
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
  { value: 'buy', label: '买入', color: '#dc2626' },
  { value: 'sell', label: '卖出', color: '#059669' },
  { value: 'bonus_share', label: '送转', color: '#d97706' },
]

export const marketMap = Object.fromEntries(MARKETS.map(m => [m.value, m]))
export const currencyMap = Object.fromEntries(CURRENCIES.map(c => [c.value, c]))
export const freqMap = Object.fromEntries(FREQS.map(f => [f.value, f.label]))
export const directionMap = Object.fromEntries(DIRECTIONS.map(d => [d.value, d]))

/** 市场徽章 class（浅底深字风格，对齐 PC global.css） */
export function badgeClass(market) {
  const map = {
    a_share: 'tag-a',
    us_stock: 'tag-us',
    hk_stock: 'tag-hk',
    fund: 'tag-fund',
    bond: 'tag-bond',
  }
  return map[market] || 'tag-a'
}

/** 金额格式化 */
export function fmt(n, digits = 2) {
  return Number(n || 0).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function fmtCNY(n) {
  return '¥ ' + fmt(n)
}

export function fmtMoney(n, symbol = '') {
  if (n === null || n === undefined || isNaN(n)) return symbol + '0.00'
  const v = Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return symbol ? symbol + v : v
}

export function cny(n) {
  return '¥' + fmt(n)
}

export function moneyWith(cur, n) {
  const s = currencyMap[cur]?.symbol || ''
  return fmtMoney(n, s)
}
