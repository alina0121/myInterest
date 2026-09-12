<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="统计分析" subtitle="看清分红结构与收益水平" /><!-- #endif -->

    <!-- 未来 12 个月预测 -->
    <view class="card">
      <view class="card-title">未来 12 个月分红预测</view>
      <view class="forecast-bars">
        <view class="fb-col" v-for="(m, i) in forecast.months" :key="i">
          <view class="fb-wrap">
            <view class="fb-bar" :style="{ height: fbHeight(forecast.amounts_cny[i]) + 'rpx' }"></view>
          </view>
          <view class="fb-label">{{ m.slice(5) }}</view>
        </view>
      </view>
      <view class="text-muted" style="font-size:22rpx;margin-top:16rpx">已公告预案 + 近 12 个月派息推算</view>
    </view>

    <!-- 市场分红占比：圆环 + 条形 -->
    <view class="card">
      <view class="card-title">各市场累计分红</view>
      <view v-if="!marketList.length" class="empty" style="padding:40rpx 0">暂无市场分布数据</view>
      <view v-else class="mkt-overview">
        <view class="donut-wrap">
          <view class="donut" :style="{ background: donutGradient }">
            <view class="donut-hole">
              <view class="donut-total">¥{{ fmt(marketTotal) }}</view>
              <view class="donut-sub">累计分红</view>
            </view>
          </view>
        </view>
        <view class="mkt-legend">
          <view class="mkt-row" v-for="m in marketList" :key="m.market">
            <view class="mkt-name">
              <text :class="['tag', badgeClass(m.market)]">{{ marketMap[m.market]?.label }}</text>
            </view>
            <view class="mkt-bar">
              <view class="mkt-fill"
                    :style="{ width: mktPct(m.amount_cny) + '%', background: marketColor(m.market) }"></view>
            </view>
            <view class="mkt-amt">¥{{ fmt(m.amount_cny) }}</view>
          </view>
        </view>
      </view>
    </view>

    <!-- 年度分红趋势 -->
    <view class="card">
      <view class="card-title">年度分红总额</view>
      <view class="year-bars">
        <view class="yb-col" v-for="y in yearList" :key="y.year">
          <view class="yb-val">¥{{ fmt(y.total_cny) }}</view>
          <view class="yb-wrap"><view class="yb-bar" :style="{ height: ybHeight(y.total_cny) + 'rpx' }"></view></view>
          <view class="yb-label">{{ y.year }}</view>
        </view>
      </view>
    </view>

    <!-- 持仓分红贡献 Top -->
    <view class="card">
      <view class="card-title">持仓分红贡献排行</view>
      <view class="top-row" v-for="(h, i) in topList" :key="h.holding_id">
        <view class="top-rank" :class="i < 3 ? 'rank-top' : ''">{{ i + 1 }}</view>
        <view class="top-name">
          <view class="tn-main">{{ h.name }}</view>
        </view>
        <view class="top-bar"><view class="top-fill" :style="{ width: topPct(h.amount_cny) + '%' }"></view></view>
        <view class="top-amt text-emerald">¥{{ fmt(h.amount_cny) }}</view>
      </view>
    </view>

    <!-- 股息率对比（双条形：成本 vs 现价） -->
    <view class="card">
      <view class="card-title">股息率对比 · 成本 vs 现价</view>
      <view v-if="!yieldTop5.length" class="empty" style="padding:30rpx 0">暂无可对比的持仓</view>
      <view v-else>
        <view class="legend-row">
          <view class="legend-item">
            <view class="legend-dot" style="background:#3b82f6"></view>
            <text class="legend-text">成本股息率</text>
          </view>
          <view class="legend-item">
            <view class="legend-dot" style="background:#059669"></view>
            <text class="legend-text">现价股息率</text>
          </view>
        </view>
        <view class="yc-row" v-for="h in yieldTop5" :key="h.holding_id">
          <view class="yc-name">
            <text :class="['tag', badgeClass(h.market)]">{{ marketMap[h.market]?.label }}</text>
            <text class="yc-hname">{{ h.name }}</text>
          </view>
          <view class="yc-bars">
            <view class="yc-bar-line">
              <view class="yc-bar-track">
                <view class="yc-bar yc-cost"
                      :style="{ width: yocPct(h.yoc_ttm) + '%' }"></view>
              </view>
              <view class="yc-val text-emerald">{{ (h.yoc_ttm * 100).toFixed(2) }}%</view>
            </view>
            <view class="yc-bar-line">
              <view class="yc-bar-track">
                <view class="yc-bar yc-price"
                      :style="{ width: yocPct(h.yield_price) + '%' }"></view>
              </view>
              <view class="yc-val">{{ h.yield_price ? (h.yield_price * 100).toFixed(2) + '%' : '—' }}</view>
            </view>
          </view>
        </view>
      </view>
    </view>

    <!-- 股息率排行（TTM 成本） -->
    <view class="card">
      <view class="card-title">股息率排行（TTM 成本）</view>
      <view class="tbl">
        <view class="tr th">
          <view class="td">持仓</view><view class="td ar">本年分红</view>
          <view class="td ar">成本股息率</view><view class="td ar">现价股息率</view>
        </view>
        <view class="tr" v-for="h in yieldList" :key="h.holding_id">
          <view class="td">{{ h.name }}</view>
          <view class="td ar">¥{{ fmt(h.year_dividend_cny) }}</view>
          <view class="td ar text-emerald">{{ (h.yoc_ttm * 100).toFixed(2) }}%</view>
          <view class="td ar">{{ h.yield_price ? (h.yield_price * 100).toFixed(2) + '%' : '—' }}</view>
        </view>
      </view>
    </view>

    <view style="height: 60rpx"></view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiByMarket, apiTopHoldings, apiYieldRanking, apiMonthlyTrend, apiForecast } from '@/api'
import { MARKETS, marketMap, currencyMap, badgeClass } from '@/utils/constants'
import WebLayout from '@/components/WebLayout.vue'

const marketList = ref([])
const yearList = ref([])
const topList = ref([])
const yieldList = ref([])
const forecast = ref({ months: [], amounts_cny: [] })

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }
function ybHeight(v) {
  const max = Math.max(...yearList.value.map(y => y.total_cny || 0), 1)
  return Math.max(8, Math.round((v / max) * 200))
}
function topPct(v) {
  const max = topList.value[0]?.amount_cny || 1
  return Math.round((v / max) * 100)
}
function mktPct(v) {
  const max = Math.max(...marketList.value.map(m => m.amount_cny || 0), 1)
  return Math.round((v / max) * 100)
}
function fbHeight(v) {
  const max = Math.max(...(forecast.value.amounts_cny || [0]), 1)
  return Math.max(6, Math.round((v / max) * 200))
}
function marketColor(market) {
  return marketMap[market]?.color || '#3b82f6'
}

const marketTotal = computed(() =>
  marketList.value.reduce((s, m) => s + Number(m.amount_cny || 0), 0)
)

const donutGradient = computed(() => {
  const total = marketTotal.value
  if (!total || !marketList.value.length) return '#f1f5f9'
  let acc = 0
  const segs = []
  marketList.value.forEach(m => {
    const pct = (Number(m.amount_cny || 0) / total) * 100
    if (pct <= 0) return
    const color = marketColor(m.market)
    segs.push(`${color} ${acc.toFixed(2)}% ${(acc + pct).toFixed(2)}%`)
    acc += pct
  })
  if (!segs.length) return '#f1f5f9'
  // 收尾到 100% 防止浮点误差留缝
  segs[segs.length - 1] = segs[segs.length - 1].replace(
    / [\d.]+%$/, ' 100%'
  )
  return `conic-gradient(${segs.join(', ')})`
})

const yieldTop5 = computed(() => (yieldList.value || []).slice(0, 5))
const yieldMax = computed(() => {
  const vals = yieldTop5.value.flatMap(h => [h.yoc_ttm || 0, h.yield_price || 0])
  return Math.max(...vals, 0.0001)
})
function yocPct(v) {
  if (!v) return 0
  return Math.max(4, Math.round((v / yieldMax.value) * 100))
}

onShow(async () => {
  try {
    const [m, top, yld, trend, fc] = await Promise.all([
      apiByMarket(), apiTopHoldings(), apiYieldRanking(), apiMonthlyTrend('12m'), apiForecast(),
    ])
    marketList.value = m.items || []
    topList.value = (top.items || []).slice(0, 10)
    yieldList.value = (yld.items || []).slice(0, 10)
    // 从月度趋势聚合年度数据
    const yearMap = {}
    trend.months?.forEach((mo, i) => {
      const y = mo.slice(0, 4)
      yearMap[y] = (yearMap[y] || 0) + (trend.amounts_cny?.[i] || 0)
    })
    yearList.value = Object.entries(yearMap).map(([year, total_cny]) => ({ year, total_cny }))
    forecast.value = fc
  } catch (e) { /* toast 已统一 */ }
})
</script>

<style scoped>
.page { padding-bottom: 40rpx; }
.card-title { font-size: 30rpx; font-weight: 600; margin-bottom: 24rpx; color: #1e293b; }

/* 预测柱状：纯色 #10b981 */
.forecast-bars { display: flex; align-items: flex-end; height: 260rpx; padding-top: 10rpx; }
.fb-col { flex: 1; display: flex; flex-direction: column; align-items: center; }
.fb-wrap { height: 220rpx; display: flex; align-items: flex-end; width: 100%; justify-content: center; }
.fb-bar { width: 28rpx; background: #10b981; border-radius: 8rpx 8rpx 0 0; min-height: 6rpx; }
.fb-label { font-size: 20rpx; color: #94a3b8; margin-top: 10rpx; }

/* 市场占比：圆环 + 图例 */
.mkt-overview { display: flex; gap: 30rpx; align-items: center; }
.donut-wrap { width: 240rpx; height: 240rpx; flex-shrink: 0; position: relative; }
.donut {
  width: 100%; height: 100%; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.donut-hole {
  width: 60%; height: 60%; background: #fff; border-radius: 50%;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.donut-total { font-size: 26rpx; font-weight: 700; color: #1e293b; }
.donut-sub { font-size: 20rpx; color: #94a3b8; margin-top: 4rpx; }
.mkt-legend { flex: 1; min-width: 0; }
.mkt-row { display: flex; align-items: center; gap: 12rpx; padding: 10rpx 0; }
.mkt-name { width: 80rpx; flex-shrink: 0; }
.mkt-bar { flex: 1; height: 22rpx; background: #f1f5f9; border-radius: 11rpx; overflow: hidden; }
.mkt-fill { height: 100%; border-radius: 11rpx; }
.mkt-amt { width: 130rpx; text-align: right; font-size: 24rpx; font-weight: 600; }

/* 年度柱状：纯色 #3b82f6 */
.year-bars { display: flex; align-items: flex-end; height: 300rpx; gap: 20rpx; }
.yb-col { flex: 1; display: flex; flex-direction: column; align-items: center; }
.yb-val { font-size: 20rpx; color: #475569; margin-bottom: 8rpx; }
.yb-wrap { height: 220rpx; display: flex; align-items: flex-end; width: 100%; justify-content: center; }
.yb-bar { width: 50rpx; background: #3b82f6; border-radius: 8rpx 8rpx 0 0; }
.yb-label { font-size: 22rpx; color: #94a3b8; margin-top: 10rpx; }

/* Top 排行：纯色 #10b981 */
.top-row { display: flex; align-items: center; gap: 16rpx; padding: 18rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.top-row:last-child { border-bottom: none; }
.top-rank { width: 48rpx; height: 48rpx; border-radius: 50%; background: #f1f5f9; color: #64748b; display: flex; align-items: center; justify-content: center; font-size: 24rpx; font-weight: 600; flex-shrink: 0; }
.top-rank.rank-top { background: #f59e0b; color: #fff; }
.top-name { width: 200rpx; flex-shrink: 0; }
.tn-main { font-size: 28rpx; font-weight: 500; }
.top-bar { flex: 1; height: 16rpx; background: #f1f5f9; border-radius: 8rpx; overflow: hidden; }
.top-fill { height: 100%; background: #10b981; border-radius: 8rpx; }
.top-amt { width: 180rpx; text-align: right; font-size: 26rpx; }

/* 股息率双条对比 */
.legend-row { display: flex; gap: 30rpx; padding-bottom: 20rpx; border-bottom: 1rpx solid #f1f5f9; margin-bottom: 8rpx; }
.legend-item { display: flex; align-items: center; gap: 10rpx; }
.legend-dot { width: 16rpx; height: 16rpx; border-radius: 4rpx; }
.legend-text { font-size: 24rpx; color: #64748b; }
.yc-row { padding: 18rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.yc-row:last-child { border-bottom: none; }
.yc-name { display: flex; align-items: center; gap: 10rpx; margin-bottom: 14rpx; }
.yc-hname { font-size: 26rpx; font-weight: 500; color: #1e293b; }
.yc-bars { display: flex; flex-direction: column; gap: 10rpx; }
.yc-bar-line { display: flex; align-items: center; gap: 14rpx; }
.yc-bar-track { flex: 1; height: 18rpx; background: #f1f5f9; border-radius: 9rpx; overflow: hidden; }
.yc-bar { height: 100%; border-radius: 9rpx; min-width: 4rpx; }
.yc-cost { background: #3b82f6; }
.yc-price { background: #059669; }
.yc-val { width: 110rpx; text-align: right; font-size: 24rpx; font-weight: 600; color: #475569; }

/* 股息率表格 */
.tbl { width: 100%; }
.tr { display: flex; padding: 18rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.tr.th { background: #f8fafc; color: #64748b; font-size: 24rpx; font-weight: 500; }
.tr:last-child { border-bottom: none; }
.td { flex: 1; font-size: 26rpx; }
.td.ar { text-align: right; }
.td-sub { color: #94a3b8; font-size: 22rpx; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 900px; margin: 0 auto; }
  .mkt-overview { gap: 48rpx; }
  .donut-wrap { width: 280rpx; height: 280rpx; }
}
/* #endif */
</style>
