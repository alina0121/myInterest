<template>
  <view class="page">
    <!-- #ifdef H5 -->
    <WebLayout title="攒息" />
    <!-- #endif -->

    <!-- ========== 深色主卡 ========== -->
    <view class="hero-card">
      <view class="hero-top">
        <view>
          <view class="hero-label">{{ mainMetricName }}</view>
          <view class="hero-value">
            <text v-if="mainMetric?.format === 'currency'" class="hero-currency">¥</text>
            {{ formatMetricValue(mainMetric, enhanced[mainMetricKey]) }}
          </view>
          <view class="hero-sub" v-if="enhanced.year_growth !== null && enhanced.year_growth !== undefined">
            <text :class="enhanced.year_growth >= 0 ? 'up' : 'down'">
              {{ enhanced.year_growth >= 0 ? '↑' : '↓' }}{{ Math.abs(enhanced.year_growth * 100).toFixed(1) }}%
            </text>
            <text>较去年同期</text>
          </view>
        </view>
        <view class="hero-edit" @click="goSettings">
          <text>自定义</text>
        </view>
      </view>

      <!-- 指标网格 -->
      <view class="m-metric-grid">
        <view
          v-for="(key, idx) in selectedMetrics"
          :key="key"
          class="m-metric-item"
          :class="{ 'metric-item--main': idx === 0 }"
        >
          <view class="m-metric-label">{{ getMetricDef(key)?.name }}</view>
          <view class="m-metric-value" :class="valueColorClass(key, enhanced[key])">
            {{ formatMetricValue(getMetricDef(key), enhanced[key]) }}
          </view>
        </view>
      </view>
    </view>

    <!-- ========== 分红趋势 ========== -->
    <view class="m-section-title">分红趋势 · 近 12 个月</view>
    <view class="m-chart-card">
      <view class="m-bar-chart">
        <view class="m-bar-col" v-for="(m, i) in trend.months" :key="i">
          <view class="m-bar-wrap">
            <view class="m-bar" :style="{ height: barHeight(trend.amounts_cny[i]) + 'rpx' }"></view>
          </view>
          <view class="m-bar-label">{{ m.slice(5) }}</view>
        </view>
      </view>
    </view>

    <!-- ========== 持仓快照 ========== -->
    <view class="m-section-title">持仓快照</view>
    <view class="m-snapshot-card">
      <view class="m-snapshot-row">
        <text class="label">持仓只数</text>
        <text class="value">{{ enhanced.holding_count || 0 }} 只</text>
      </view>
      <view class="m-snapshot-row">
        <text class="label">累计收息</text>
        <text class="value">¥{{ fmt(enhanced.total_received_cny) }}</text>
      </view>
      <view class="m-snapshot-row">
        <text class="label">总市值</text>
        <text class="value">{{ enhanced.market_value_cny > 0 ? '¥' + fmt(enhanced.market_value_cny) : '—' }}</text>
      </view>
      <view class="m-snapshot-row">
        <text class="label">浮动盈亏</text>
        <text class="value" :class="pnlClass(enhanced.floating_pnl_cny)">
          {{ enhanced.market_value_cny > 0 ? (enhanced.floating_pnl_cny >= 0 ? '+' : '') + '¥' + fmt(enhanced.floating_pnl_cny) : '—' }}
        </text>
      </view>
      <view class="m-snapshot-row">
        <text class="label">净投入</text>
        <text class="value">¥{{ fmt(enhanced.net_investment_cny) }}</text>
      </view>
    </view>

    <view style="height: 40rpx"></view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiEnhancedSummary, apiDashboardMetrics, apiMonthlyTrend } from '@/api'
// #ifdef H5
import WebLayout from '@/components/WebLayout.vue'
// #endif

// ---------- 数据 ----------
const enhanced = ref({})
const registry = ref([])
const selectedMetrics = ref([])
const trend = ref({ months: [], amounts_cny: [] })

// ---------- 计算属性 ----------
const mainMetricKey = computed(() => selectedMetrics.value[0] || 'forecast_year_cny')
const mainMetric = computed(() => getMetricDef(mainMetricKey.value))
const mainMetricName = computed(() => mainMetric.value?.name || '预测年度分红')

// ---------- 指标工具 ----------
function getMetricDef(key) {
  return registry.value.find(m => m.key === key)
}

function fmt(n, digits = 2) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

function formatMetricValue(def, val) {
  if (val === null || val === undefined || val === 0) return '—'
  if (!def) return fmt(val)
  switch (def.format) {
    case 'currency': return '¥' + fmt(val)
    case 'percent': return (val * 100).toFixed(2) + '%'
    case 'number': return val + ' 只'
    default: return fmt(val)
  }
}

function valueColorClass(key, val) {
  if (val === null || val === undefined || val === 0) return ''
  if (key === 'floating_pnl_cny' || key === 'pnl_rate') {
    return val >= 0 ? 'positive' : 'negative'
  }
  return ''
}

function pnlClass(val) {
  if (val === null || val === undefined || val === 0) return ''
  return val >= 0 ? 'positive' : 'negative'
}

function barHeight(v) {
  const max = Math.max(...(trend.value.amounts_cny || [0]), 1)
  return Math.max(6, Math.round((v / max) * 200))
}

// ---------- 页面跳转 ----------
function goSettings() {
  uni.navigateTo({ url: '/pages/index/metrics' })
}

// ---------- 加载 ----------
async function load() {
  try {
    const [enh, fm, t] = await Promise.all([
      apiEnhancedSummary(),
      apiDashboardMetrics(),
      apiMonthlyTrend('12m'),
    ])
    enhanced.value = enh
    registry.value = fm.registry
    selectedMetrics.value = fm.selected
    trend.value = t
  } catch (e) { /* toast 已统一处理 */ }
}

onShow(load)
</script>

<style scoped>
.page { padding-bottom: 30rpx; }

/* ========== 深色主卡 ========== */
.hero-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 20rpx;
  padding: 32rpx 28rpx;
  color: #fff;
  margin: 16rpx;
  position: relative;
  overflow: hidden;
}
.hero-card::before {
  content: '';
  position: absolute;
  top: -30%; right: -20%;
  width: 250px; height: 250px;
  background: radial-gradient(circle, rgba(255,165,0,0.15) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}
.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24rpx;
  position: relative;
  z-index: 1;
}
.hero-label {
  font-size: 24rpx;
  color: rgba(255,255,255,0.5);
  letter-spacing: 4rpx;
}
.hero-value {
  font-size: 72rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
  margin-top: 8rpx;
}
.hero-currency {
  font-size: 30rpx;
  font-weight: 400;
  margin-right: 6rpx;
  opacity: 0.7;
}
.hero-sub {
  font-size: 24rpx;
  color: rgba(255,255,255,0.5);
  margin-top: 6rpx;
}
.hero-sub .up { color: #4ade80; margin-right: 6rpx; }
.hero-sub .down { color: #f87171; margin-right: 6rpx; }

.hero-edit {
  font-size: 22rpx;
  color: rgba(255,255,255,0.6);
  padding: 8rpx 20rpx;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12rpx;
  z-index: 1;
}

/* 指标网格 */
.m-metric-grid {
  display: flex;
  flex-wrap: wrap;
  position: relative;
  z-index: 1;
}
.m-metric-item {
  width: 33.33%;
  padding: 20rpx 16rpx;
  border-top: 1px solid rgba(255,255,255,0.1);
  box-sizing: border-box;
}
/* 同一行内非首列加左边框 */
.m-metric-item:not(:nth-child(3n+1)):not(:first-child) {
  border-left: 1px solid rgba(255,255,255,0.06);
}
.m-metric-label {
  font-size: 22rpx;
  color: rgba(255,255,255,0.5);
  margin-bottom: 6rpx;
}
.m-metric-value {
  font-size: 34rpx;
  font-weight: 600;
  color: #fff;
}
.m-metric-value.positive { color: #4ade80; }
.m-metric-value.negative { color: #f87171; }

/* ========== 通用区块标题 ========== */
.m-section-title {
  font-size: 28rpx;
  font-weight: 600;
  margin: 28rpx 32rpx 16rpx;
  color: #1a1a1a;
}

/* ========== 分红趋势 ========== */
.m-chart-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx 16rpx;
  margin: 0 16rpx;
  border: 1px solid #eee;
}
.m-bar-chart {
  display: flex;
  align-items: flex-end;
  height: 260rpx;
  gap: 4rpx;
}
.m-bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.m-bar-wrap {
  height: 220rpx;
  display: flex;
  align-items: flex-end;
  width: 100%;
  justify-content: center;
}
.m-bar {
  width: 18rpx;
  background: linear-gradient(180deg, #1e3a8a 0%, #3b82f6 100%);
  border-radius: 4rpx 4rpx 0 0;
  min-height: 4rpx;
}
.m-bar-label { font-size: 18rpx; color: #94a3b8; margin-top: 8rpx; }

/* ========== 持仓快照 ========== */
.m-snapshot-card {
  background: #fff;
  border-radius: 16rpx;
  margin: 0 16rpx;
  border: 1px solid #eee;
  overflow: hidden;
}
.m-snapshot-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 28rpx;
  border-bottom: 1px solid #f5f5f5;
  font-size: 26rpx;
}
.m-snapshot-row:last-child { border-bottom: none; }
.m-snapshot-row .label { color: #999; }
.m-snapshot-row .value { font-weight: 500; color: #333; }
.m-snapshot-row .value.positive { color: #16a34a; }
.m-snapshot-row .value.negative { color: #dc2626; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 900px; margin: 0 auto; }
}
/* #endif */
</style>
