/** 市场与币种常量（与 uni-app 端 constants 一致） */
export const MARKETS = [
  { value: 'a_share', label: 'A股', color: '#dc2626' },
  { value: 'us_stock', label: '美股', color: '#2563eb' },
  { value: 'hk_stock', label: '港股', color: '#059669' },
  { value: 'fund', label: '基金', color: '#d97706' },
]

export const marketMap = Object.fromEntries(MARKETS.map((m) => [m.value, m]))

export const CURRENCIES = {
  CNY: { symbol: '¥', label: '人民币' },
  USD: { symbol: '$', label: '美元' },
  HKD: { symbol: 'HK$', label: '港币' },
}

export const currencyMap = Object.fromEntries(
  Object.entries(CURRENCIES).map(([k, v]) => [k, v]),
)

export const FREQS = [
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
