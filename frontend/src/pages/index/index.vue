<template>
  <view class="page">
    <!-- #ifdef H5 -->
    <WebLayout title="总览看板" />
    <!-- #endif -->

    <!-- 2×2 核心指标卡 -->
    <view class="stat-grid">
      <view class="stat-card">
        <view class="stat-label">{{ year }}年度分红</view>
        <view class="stat-value">¥{{ fmt(summary.year_dividend_cny) }}</view>
        <view class="stat-foot" :class="growthClass">{{ growthText }}</view>
      </view>
      <view class="stat-card">
        <view class="stat-label">本月到账</view>
        <view class="stat-value">¥{{ fmt(summary.month_dividend_cny) }}</view>
        <view class="stat-foot text-muted">{{ summary.month_count || 0 }} 笔</view>
      </view>
      <view class="stat-card">
        <view class="stat-label">累计分红</view>
        <view class="stat-value">¥{{ fmt(summary.total_dividend_cny) }}</view>
        <view class="stat-foot text-muted">{{ summary.since_year ? '自 ' + summary.since_year : '暂无记录' }}</view>
      </view>
      <view class="stat-card">
        <view class="stat-label">持仓数量</view>
        <view class="stat-value">{{ summary.holding_count || 0 }} 只</view>
        <view class="stat-foot text-muted">{{ marketFoot }}</view>
      </view>
    </view>

    <!-- 分红趋势（近12月） -->
    <view class="section-title">分红趋势（近12月）</view>
    <view class="card trend-card">
      <view class="bars">
        <view class="bar-col" v-for="(m, i) in trend.months" :key="i">
          <view class="bar-wrap">
            <view class="bar" :style="{ height: barHeight(trend.amounts_cny[i]) + 'rpx' }"></view>
          </view>
          <view class="bar-label">{{ m.slice(5) }}</view>
        </view>
      </view>
    </view>

    <!-- 最近到账 -->
    <view class="section-title">
      最近到账
      <text class="more" @click="goDividends">全部 ›</text>
    </view>
    <view class="card list-card">
      <view v-if="!recent.length" class="empty">还没有分红记录</view>
      <view v-for="d in recent" :key="d.id" class="div-row" @click="goHolding(d.holding_id)">
        <view class="div-main">
          <view class="div-name">{{ d.holding_name }}</view>
          <view class="div-sub">{{ fmtDate(d.pay_date) }} 派息</view>
        </view>
        <view class="div-amt text-emerald">+{{ sym(d.currency) }}{{ fmt(d.net_amount) }}</view>
      </view>
    </view>

    <view style="height: 40rpx"></view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiSummary, apiMonthlyTrend, apiDividends, apiHoldings } from '@/api'
import { currencyMap, marketMap, MARKETS } from '@/utils/constants'
// #ifdef H5
import WebLayout from '@/components/WebLayout.vue'
// #endif

const summary = ref({})
const trend = ref({ months: [], amounts_cny: [] })
const recent = ref([])
const holdings = ref([])

const year = new Date().getFullYear()

const growthText = computed(() => {
  const g = summary.value.year_growth
  if (g === null || g === undefined) return '暂无同比'
  return (g >= 0 ? '↑ ' : '↓ ') + (Math.abs(g) * 100).toFixed(1) + '%'
})
const growthClass = computed(() => {
  const g = summary.value.year_growth
  if (g === null || g === undefined) return 'text-muted'
  return g >= 0 ? 'text-emerald' : 'text-amber'
})

const marketFoot = computed(() => {
  if (!holdings.value.length) return '暂无持仓'
  const counts = {}
  holdings.value.forEach(h => {
    const lbl = marketMap[h.market]?.label
    if (lbl) counts[lbl] = (counts[lbl] || 0) + 1
  })
  // 按市场字典顺序输出，仅保留有持仓的市场
  const parts = MARKETS
    .map(m => marketMap[m.value]?.label)
    .filter(lbl => lbl && counts[lbl])
    .map(lbl => `${lbl}${counts[lbl]}`)
  return parts.length ? parts.join('·') : '暂无持仓'
})

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }
function fmtDate(d) { return d ? String(d).slice(5) : '' }

function barHeight(v) {
  const max = Math.max(...(trend.value.amounts_cny || [0]), 1)
  return Math.max(6, Math.round((v / max) * 200))
}

async function load() {
  try {
    const [s, t, list, h] = await Promise.all([
      apiSummary(),
      apiMonthlyTrend('12m'),
      apiDividends({ status: 'confirmed', page: 1, page_size: 3 }),
      apiHoldings(),
    ])
    summary.value = s
    trend.value = t
    recent.value = list.items || []
    holdings.value = h.items || []
  } catch (e) { /* toast 已统一处理 */ }
}

onShow(load)

function goDividends() { uni.navigateTo({ url: '/pages/dividends/list' }) }
function goHolding(id) { uni.navigateTo({ url: '/pages/holdings/detail?id=' + id }) }
</script>

<style scoped>
.page { padding-bottom: 30rpx; }

/* 2×2 指标卡 */
.stat-grid {
  display: flex;
  flex-wrap: wrap;
  padding: 24rpx 24rpx 0;
}
.stat-card {
  width: calc(50% - 16rpx);
  margin: 8rpx;
  background: #fff;
  border-radius: 24rpx;
  padding: 28rpx 26rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
  box-sizing: border-box;
}
.stat-label { font-size: 22rpx; color: #94a3b8; }
.stat-value {
  font-size: 36rpx;
  font-weight: 700;
  color: #1e293b;
  margin: 12rpx 0 8rpx;
}
.stat-foot { font-size: 20rpx; }

/* 分红趋势柱状 */
.trend-card { padding: 32rpx 28rpx 24rpx; }
.bars { display: flex; align-items: flex-end; height: 260rpx; }
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.bar-wrap {
  height: 220rpx;
  display: flex;
  align-items: flex-end;
  width: 100%;
  justify-content: center;
}
.bar {
  width: 28rpx;
  background: rgba(30, 58, 138, 0.8);
  border-radius: 8rpx 8rpx 0 0;
  min-height: 6rpx;
}
.bar-label { font-size: 20rpx; color: #94a3b8; margin-top: 12rpx; }

/* 最近到账列表 */
.more { font-size: 24rpx; color: #1e3a8a; font-weight: 400; }
.list-card { padding: 8rpx 28rpx; }
.div-row {
  display: flex;
  align-items: center;
  padding: 26rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
}
.div-row:last-child { border-bottom: none; }
.div-main { flex: 1; min-width: 0; }
.div-name { font-size: 28rpx; font-weight: 500; color: #1e293b; }
.div-sub { font-size: 22rpx; color: #94a3b8; margin-top: 8rpx; }
.div-amt { font-size: 28rpx; flex-shrink: 0; margin-left: 16rpx; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 900px; margin: 0 auto; }
  .stat-grid { padding: 0; }
  .stat-card { width: calc(25% - 16rpx); }
}
/* #endif */
</style>
