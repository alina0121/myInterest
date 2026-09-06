<template>
  <view class="page">
    <!-- #ifdef H5 -->
    <WebLayout title="总览看板" />
    <!-- #endif -->
    <!-- 顶部欢迎条 -->
    <view class="header">
      <view>
        <view class="hi">{{ greeting }}，{{ user?.nickname || user?.username || '投资者' }}</view>
        <view class="sub">今天也是收息的好日子</view>
      </view>
      <view class="record-btn" @click="goRecord">＋ 记一笔</view>
    </view>

    <!-- 核心指标卡 -->
    <view class="stat-grid">
      <view class="stat-card">
        <view class="stat-label">今年分红(¥)</view>
        <view class="stat-value">{{ fmt(summary.year_dividend_cny) }}</view>
        <view class="stat-foot" :class="growthClass">
          {{ growthText }}
        </view>
      </view>
      <view class="stat-card">
        <view class="stat-label">本月到账(¥)</view>
        <view class="stat-value">{{ fmt(summary.month_dividend_cny) }}</view>
        <view class="stat-foot text-muted">{{ summary.month_count || 0 }} 笔分红</view>
      </view>
      <view class="stat-card">
        <view class="stat-label">累计分红(¥)</view>
        <view class="stat-value">{{ fmt(summary.total_dividend_cny) }}</view>
        <view class="stat-foot text-muted">{{ summary.since_year ? '自 ' + summary.since_year + ' 年' : '暂无记录' }}</view>
      </view>
      <view class="stat-card">
        <view class="stat-label">持仓数</view>
        <view class="stat-value">{{ summary.holding_count || 0 }}</view>
        <view class="stat-foot text-muted">下月预计 ¥{{ fmt(summary.next_month_forecast_cny) }}</view>
      </view>
    </view>

    <!-- 12 个月分红趋势 -->
    <view class="section-title">近 12 个月分红趋势</view>
    <view class="card">
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
      <view v-if="!recent.length" class="empty">还没有分红记录，点右上角「记一笔」开始吧</view>
      <view v-for="d in recent" :key="d.id" class="div-row" @click="goHolding(d.holding_id)">
        <view class="dot" :class="d.status === 'confirmed' ? 'dot-ok' : 'dot-pend'"></view>
        <view class="div-main">
          <view class="div-name">{{ d.holding_name }}</view>
          <view class="div-sub">{{ d.pay_date }} · {{ d.shares }} 股</view>
        </view>
        <view class="div-amt">
          <view :class="d.status === 'confirmed' ? 'text-income' : 'text-pending'">
            {{ sym(d.currency) }}{{ fmt(d.net_amount) }}
          </view>
          <view class="div-sub text-muted">税前 {{ sym(d.currency) }}{{ fmt(d.gross_amount) }}</view>
        </view>
      </view>
    </view>

    <view style="height: 40rpx"></view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiSummary, apiMonthlyTrend, apiDividends } from '@/api'
import { userStore } from '@/store/user'
import { currencyMap } from '@/utils/constants'
import WebLayout from '@/components/WebLayout.vue'

const user = computed(() => userStore.user)
const summary = ref({})
const trend = ref({ months: [], amounts_cny: [] })
const recent = ref([])

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const growthText = computed(() => {
  const g = summary.value.year_growth
  if (g === null || g === undefined) return '暂无同比数据'
  return (g >= 0 ? '↑ ' : '↓ ') + (g * 100).toFixed(1) + '% 同比'
})
const growthClass = computed(() => {
  const g = summary.value.year_growth
  if (g === null || g === undefined) return 'text-muted'
  return g >= 0 ? 'text-income' : 'text-pending'
})

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

function barHeight(v) {
  const max = Math.max(...(trend.value.amounts_cny || [0]), 1)
  return Math.max(6, Math.round((v / max) * 200))
}

async function load() {
  try {
    const [s, t, list] = await Promise.all([
      apiSummary(),
      apiMonthlyTrend('12m'),
      apiDividends({ page: 1, page_size: 5 }),
    ])
    summary.value = s
    trend.value = t
    recent.value = list.items
  } catch (e) { /* toast 已统一处理 */ }
}

onShow(load)

function goRecord() { uni.navigateTo({ url: '/pages/dividends/add' }) }
function goDividends() { uni.navigateTo({ url: '/pages/dividends/list' }) }
function goHolding(id) { uni.navigateTo({ url: '/pages/holdings/detail?id=' + id }) }
</script>

<style scoped>
.page { padding-bottom: 30rpx; }
.header {
  display: flex; align-items: center; justify-content: space-between;
  background: linear-gradient(135deg, #1668dc, #3b82f6);
  padding: 30rpx 32rpx 90rpx; color: #fff;
}
.hi { font-size: 36rpx; font-weight: 700; }
.sub { font-size: 24rpx; opacity: 0.85; margin-top: 8rpx; }
.record-btn {
  background: rgba(255,255,255,0.2); border: 1rpx solid rgba(255,255,255,0.5);
  padding: 14rpx 28rpx; border-radius: 36rpx; font-size: 26rpx;
}
.stat-grid {
  display: flex; flex-wrap: wrap; margin: -60rpx 12rpx 0; position: relative;
}
.stat-card {
  width: calc(50% - 24rpx); margin: 12rpx; background: #fff; border-radius: 18rpx;
  padding: 24rpx 26rpx; box-shadow: 0 6rpx 20rpx rgba(22,104,220,0.08);
}
.stat-label { font-size: 24rpx; color: #94a3b8; }
.stat-value { font-size: 40rpx; font-weight: 700; color: #1e293b; margin: 10rpx 0; }
.stat-foot { font-size: 22rpx; }
.bars { display: flex; align-items: flex-end; height: 260rpx; padding-top: 10rpx; }
.bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; }
.bar-wrap { height: 220rpx; display: flex; align-items: flex-end; width: 100%; justify-content: center; }
.bar { width: 28rpx; background: linear-gradient(180deg, #3b82f6, #93c5fd); border-radius: 8rpx 8rpx 0 0; min-height: 6rpx; }
.bar-label { font-size: 20rpx; color: #94a3b8; margin-top: 10rpx; }
.more { font-size: 24rpx; color: #1668dc; font-weight: 400; }
.list-card { padding: 4rpx 28rpx; }
.div-row { display: flex; align-items: center; padding: 26rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.div-row:last-child { border-bottom: none; }
.dot { width: 16rpx; height: 16rpx; border-radius: 50%; margin-right: 18rpx; flex-shrink: 0; }
.dot-ok { background: #16a34a; }
.dot-pend { background: #f59e0b; }
.div-main { flex: 1; }
.div-name { font-size: 28rpx; font-weight: 500; }
.div-sub { font-size: 22rpx; color: #94a3b8; margin-top: 6rpx; }
.div-amt { text-align: right; font-size: 28rpx; }

/* #ifdef H5 */
/* 桌面端：4 列统计卡、双列内容区 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; }
  .header { border-radius: 16rpx; margin: 0 0 24rpx; padding: 36rpx 40rpx 40rpx; }
  .stat-grid { margin: 0; }
  .stat-card { width: calc(25% - 24rpx); }
  .section-title { margin: 32rpx 0 16rpx; }
}
/* #endif */
</style>
