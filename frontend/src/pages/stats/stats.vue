<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="统计分析" subtitle="看清分红结构与收益水平" /><!-- #endif -->

    <!-- 市场分红占比 -->
    <view class="card">
      <view class="card-title">各市场累计分红</view>
      <view class="mkt-row" v-for="m in marketList" :key="m.market">
        <view class="mkt-name">
          <text class="tag" :style="{ background: marketMap[m.market]?.color }">{{ marketMap[m.market]?.label }}</text>
        </view>
        <view class="mkt-bar"><view class="mkt-fill" :style="{ width: mktPct(m.amount_cny) + '%' }"></view></view>
        <view class="mkt-amt">¥{{ fmt(m.amount_cny) }}</view>
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
        <view class="top-amt text-income">¥{{ fmt(h.amount_cny) }}</view>
      </view>
    </view>

    <!-- 股息率排行 -->
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
          <view class="td ar text-income">{{ (h.yoc_ttm * 100).toFixed(2) }}%</view>
          <view class="td ar">{{ h.yield_price ? (h.yield_price * 100).toFixed(2) + '%' : '-' }}</view>
        </view>
      </view>
    </view>

    <view style="height: 60rpx"></view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiByMarket, apiTopHoldings, apiYieldRanking, apiMonthlyTrend } from '@/api'
import { marketMap, currencyMap } from '@/utils/constants'
import WebLayout from '@/components/WebLayout.vue'

const marketList = ref([])
const yearList = ref([])
const topList = ref([])
const yieldList = ref([])

function fmt(n) { return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
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

onShow(async () => {
  try {
    const [m, top, yld, trend] = await Promise.all([
      apiByMarket(), apiTopHoldings(), apiYieldRanking(), apiMonthlyTrend('12m'),
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
  } catch (e) { /* toast 已统一 */ }
})
</script>

<style scoped>
.page { padding-bottom: 40rpx; }
.card-title { font-size: 30rpx; font-weight: 600; margin-bottom: 24rpx; color: #1e293b; }

/* 市场占比 */
.mkt-row { display: flex; align-items: center; gap: 16rpx; padding: 16rpx 0; }
.mkt-name { width: 120rpx; flex-shrink: 0; }
.mkt-bar { flex: 1; height: 24rpx; background: #f1f5f9; border-radius: 12rpx; overflow: hidden; }
.mkt-fill { height: 100%; background: linear-gradient(90deg, #1668dc, #3b82f6); border-radius: 12rpx; }
.mkt-amt { width: 160rpx; text-align: right; font-size: 26rpx; font-weight: 600; }

/* 年度柱状 */
.year-bars { display: flex; align-items: flex-end; height: 300rpx; gap: 20rpx; }
.yb-col { flex: 1; display: flex; flex-direction: column; align-items: center; }
.yb-val { font-size: 20rpx; color: #475569; margin-bottom: 8rpx; }
.yb-wrap { height: 220rpx; display: flex; align-items: flex-end; width: 100%; justify-content: center; }
.yb-bar { width: 50rpx; background: linear-gradient(180deg, #10b981, #6ee7b7); border-radius: 8rpx 8rpx 0 0; }
.yb-label { font-size: 22rpx; color: #94a3b8; margin-top: 10rpx; }

/* Top 排行 */
.top-row { display: flex; align-items: center; gap: 16rpx; padding: 18rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.top-row:last-child { border-bottom: none; }
.top-rank { width: 48rpx; height: 48rpx; border-radius: 50%; background: #f1f5f9; color: #64748b; display: flex; align-items: center; justify-content: center; font-size: 24rpx; font-weight: 600; flex-shrink: 0; }
.top-rank.rank-top { background: linear-gradient(135deg, #f59e0b, #fbbf24); color: #fff; }
.top-name { width: 200rpx; flex-shrink: 0; }
.tn-main { font-size: 28rpx; font-weight: 500; }
.tn-sub { font-size: 22rpx; color: #94a3b8; margin-top: 4rpx; }
.top-bar { flex: 1; height: 16rpx; background: #f1f5f9; border-radius: 8rpx; overflow: hidden; }
.top-fill { height: 100%; background: linear-gradient(90deg, #10b981, #34d399); border-radius: 8rpx; }
.top-amt { width: 180rpx; text-align: right; font-size: 26rpx; }

/* 股息率表格 */
.tbl { width: 100%; }
.tr { display: flex; padding: 18rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.tr.th { background: #f8fafc; color: #64748b; font-size: 24rpx; font-weight: 500; }
.tr:last-child { border-bottom: none; }
.td { flex: 1; font-size: 26rpx; }
.td.ar { text-align: right; }
.td-sub { color: #94a3b8; font-size: 22rpx; }
</style>
