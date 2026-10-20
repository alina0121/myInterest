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
            <text v-if="mainMetric?.format === 'currency'" class="hero-currency">{{ curSymbol }}</text>
            {{ formatMetricValue(mainMetric, enhanced[mainMetricKey]) }}
          </view>
          <view class="hero-sub" v-if="enhanced.year_growth !== null && enhanced.year_growth !== undefined">
            <text :class="enhanced.year_growth >= 0 ? 'up' : 'down'">
              {{ enhanced.year_growth >= 0 ? '↑' : '↓' }}{{ Math.abs(enhanced.year_growth * 100).toFixed(1) }}%
            </text>
            <text>较去年同期</text>
          </view>
        </view>
        <view class="hero-actions">
          <!-- v8：币种切换（仅总览页生效，对齐 PC 端深色主卡右上角） -->
          <view class="hero-edit" @click="curVisible = true">
            <text class="cur-symbol">{{ curSymbol }}</text>
            <text>{{ curLabel }}</text>
          </view>
          <view class="hero-edit" @click="goSettings">
            <text>自定义</text>
          </view>
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

    <!-- 到账提醒条：有即将到账分红时展示，点击进入分红预告 -->
    <view v-if="upcomingCount" :class="['soon-bar', soonHot ? 'hot' : '']" @click="goRecord">
      <text class="soon-icon">🔔</text>
      <view class="soon-text">
        <text v-if="soonHot" class="soon-strong">{{ soonHot }} 笔分红 7 天内到账</text>
        <text v-else class="soon-strong">近期有 {{ upcomingCount }} 笔分红待到账</text>
        <text class="soon-sub">本月预计 ≈ ¥{{ fmt(soonMonthTotal) }}</text>
      </view>
      <text class="soon-arrow">›</text>
    </view>

    <!-- 币种切换弹窗 -->
    <view v-if="curVisible" class="modal-mask" @click="curVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">显示币种</view>
        <view class="modal-tip">仅总览看板生效，聚合多币种持仓统一折算；其他页面按人民币显示。</view>
        <view class="acct-list">
          <view v-for="c in DISPLAY_CURRENCIES" :key="c.value"
                :class="['acct-row', userStore.displayCurrency === c.value ? 'on' : '']"
                @click="pickCurrency(c.value)">
            <text class="acct-dot" :style="{ background: c.color || '#94a3b8' }"></text>
            <text class="acct-name">{{ c.label }}</text>
            <text v-if="userStore.displayCurrency === c.value" class="acct-check">✓</text>
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="curVisible = false">关闭</button>
        </view>
      </view>
    </view>

    <!-- ========== 分红趋势 ========== -->
    <view class="m-section-title">
      <text>分红趋势 · 近 12 个月</text>
      <text class="m-section-extra">合计 {{ fmtDisplay(trendTotal, enhanced.display_currency) }}</text>
    </view>
    <view class="m-chart-card">
      <!-- 图例 + 交互提示 -->
      <view class="m-chart-legend">
        <view class="legend-item"><view class="legend-swatch green"></view><text>本月</text></view>
        <view class="legend-item"><view class="legend-swatch avg"></view><text>月均 {{ fmtDisplay(avgAmount, enhanced.display_currency) }}</text></view>
        <text class="legend-tip" v-if="selIdx < 0">点击柱子看金额</text>
        <text class="legend-tip" v-else>{{ trend.months[selIdx] }} · {{ fmtDisplay(trend.amounts[selIdx], enhanced.display_currency) }}</text>
      </view>
      <view class="m-bar-chart">
        <!-- 月均虚线参考线 -->
        <view class="avg-line" :style="{ bottom: (avgHeight + 26) + 'rpx' }" v-if="avgAmount > 0"></view>
        <view class="m-bar-col" v-for="(m, i) in trend.months" :key="i" @click="pickBar(i)">
          <view class="m-bar-wrap">
            <view class="m-bubble" v-if="selIdx === i" :style="{ bottom: (barHeight(trend.amounts[i]) + 14) + 'rpx' }">
              {{ fmtDisplay(trend.amounts[i], enhanced.display_currency) }}
            </view>
            <view :class="['m-bar', m === curMonth ? 'cur' : '', trend.amounts[i] > 0 ? '' : 'zero', selIdx === i ? 'sel' : '']" :style="{ height: barHeight(trend.amounts[i]) + 'rpx' }"></view>
          </view>
          <view :class="['m-bar-label', m === curMonth ? 'cur' : '']">{{ m.slice(5) }}</view>
        </view>
      </view>
    </view>

    <!-- ========== 持仓快照（紧凑宫格） ========== -->
    <view class="m-section-title">
      <text>持仓快照</text>
      <text class="m-section-extra" @click="goHoldings">管理 ›</text>
    </view>
    <view class="snap-grid">
      <view class="snap-cell">
        <view class="snap-label">持仓只数</view>
        <view class="snap-value">{{ enhanced.holding_count || 0 }} 只</view>
      </view>
      <view class="snap-cell">
        <view class="snap-label">累计收息</view>
        <view class="snap-value green">{{ fmtDisplay(enhanced.total_received, enhanced.display_currency) }}</view>
      </view>
      <view class="snap-cell">
        <view class="snap-label">总市值</view>
        <view class="snap-value">{{ enhanced.market_value > 0 ? fmtDisplay(enhanced.market_value, enhanced.display_currency) : '—' }}</view>
      </view>
      <view class="snap-cell">
        <view class="snap-label">浮动盈亏</view>
        <view class="snap-value" :class="pnlClass(enhanced.floating_pnl)">
          {{ enhanced.market_value > 0 ? (enhanced.floating_pnl >= 0 ? '+' : '') + fmtDisplay(enhanced.floating_pnl, enhanced.display_currency) : '—' }}
        </view>
      </view>
      <view class="snap-cell">
        <view class="snap-label">净投入</view>
        <view class="snap-value">{{ fmtDisplay(enhanced.net_investment, enhanced.display_currency) }}</view>
      </view>
      <view class="snap-cell">
        <view class="snap-label">回本进度</view>
        <view class="snap-value blue">{{ recoverPct }}</view>
      </view>
    </view>

    <view style="height: 40rpx"></view>
    <!-- #ifdef H5 --><CustomTab current="/pages/index/index" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { apiEnhancedSummary, apiDashboardMetrics, apiMonthlyTrend, apiSaveSettings, apiUpcoming } from '@/api'
import { userStore, setDisplayCurrency } from '@/store/user'
import { fmtDisplay } from '@/utils/constants'
// #ifdef H5
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'
// #endif

// ---------- 数据 ----------
const enhanced = ref({})
const registry = ref([])
const selectedMetrics = ref([])
const trend = ref({ months: [], amounts: [] })
const curVisible = ref(false)
const upcomingCount = ref(0)
const soonHot = ref(0)          // 7 天内到账笔数
const soonMonthTotal = ref(0)   // 本月预计到账（CNY）

/** v8：币种选项（仅总览页生效，对齐 PC 端总览下拉） */
const DISPLAY_CURRENCIES = [
  { value: 'CNY', label: '人民币（统一折算）', color: '#dc2626' },
  { value: 'USD', label: '美元', color: '#2563eb' },
  { value: 'HKD', label: '港币', color: '#059669' },
  { value: 'ORIGINAL', label: '本币（按原币种）', color: '#7c3aed' },
]

/** v8：总览页显示币种符号（¥ / $ / HK$），跟随 userStore.displayCurrency */
const curSymbol = computed(() => {
  const symbols = { CNY: '¥', USD: '$', HKD: 'HK$' }
  return symbols[userStore.displayCurrency] || '¥'
})
/** 币种切换按钮标签 */
const curLabel = computed(() => {
  const labels = { CNY: '人民币', USD: '美元', HKD: '港币', ORIGINAL: '本币' }
  return labels[userStore.displayCurrency] || '人民币'
})

/** v8：账户跟随 + 显示币种参数（仅总览页传 display_currency） */
function filterParams() {
  const p = {}
  if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
    p.account = userStore.currentAccount
  }
  if (userStore.displayCurrency && userStore.displayCurrency !== 'CNY') {
    p.display_currency = userStore.displayCurrency
  }
  return p
}

/** v8：切换显示币种（持久化到后端后刷新数据） */
async function pickCurrency(value) {
  // setDisplayCurrency 是 store 独立导出函数（非 userStore 方法）
  setDisplayCurrency(value)
  curVisible.value = false
  try { await apiSaveSettings({ display_currency: value }) } catch (e) { /* 静默 */ }
  await load()
}

// ---------- 计算属性 ----------
const mainMetricKey = computed(() => selectedMetrics.value[0] || 'forecast_year')
const mainMetric = computed(() => getMetricDef(mainMetricKey.value))
const mainMetricName = computed(() => mainMetric.value?.name || '预测年度分红')

/** 近 12 个月分红合计 */
const trendTotal = computed(() => (trend.value.amounts || []).reduce((a, b) => a + Number(b || 0), 0))
/** 月均分红（有值的月份） */
const avgAmount = computed(() => {
  const arr = (trend.value.amounts || []).map(Number).filter(v => v > 0)
  return arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0
})
const avgHeight = computed(() => barHeight(avgAmount.value))
/** 点选的柱子索引 */
const selIdx = ref(-1)
function pickBar(i) { selIdx.value = selIdx.value === i ? -1 : i }
/** 当前月份 YYYY-MM，用于柱状图高亮 */
const curMonth = new Date().toISOString().slice(0, 7)
/** 回本进度 = 累计收息 / 净投入 */
const recoverPct = computed(() => {
  const e = enhanced.value
  if (!e.net_investment) return '—'
  return (Math.min((e.total_received || 0) / e.net_investment, 9.99) * 100).toFixed(1) + '%'
})

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
    // v8：货币类用 fmtDisplay 动态符号（跟随总览币种）
    case 'currency': return fmtDisplay(val, userStore.displayCurrency)
    case 'percent': return (val * 100).toFixed(2) + '%'
    case 'number': return val + ' 只'
    default: return fmt(val)
  }
}

function valueColorClass(key, val) {
  if (val === null || val === undefined || val === 0) return ''
  if (key === 'floating_pnl' || key === 'pnl_rate') {
    return val >= 0 ? 'positive' : 'negative'
  }
  return ''
}

function pnlClass(val) {
  if (val === null || val === undefined || val === 0) return ''
  return val >= 0 ? 'positive' : 'negative'
}

function barHeight(v) {
  const max = Math.max(...(trend.value.amounts || [0]), 1)
  return Math.max(6, Math.round((v / max) * 200))
}

// ---------- 页面跳转 ----------
function goSettings() {
  uni.navigateTo({ url: '/pages/index/metrics' })
}
function goRecord() {
  uni.switchTab({ url: '/pages/holdings/holdings' })
}
function goHoldings() {
  uni.switchTab({ url: '/pages/holdings/holdings' })
}

// ---------- 加载 ----------
async function load() {
  try {
    // v8：账户跟随 + 币种过滤（metrics 与账户/币种无关）
    const fp = filterParams()
    const [enh, fm, t, up] = await Promise.all([
      apiEnhancedSummary(fp),
      apiDashboardMetrics(),
      apiMonthlyTrend('12m', fp),
      apiUpcoming(),
    ])
    enhanced.value = enh
    registry.value = fm.registry
    selectedMetrics.value = fm.selected
    trend.value = t
    const items = up.items || []
    upcomingCount.value = items.length
    soonHot.value = items.filter(x => x.days_to_pay !== null && x.days_to_pay !== undefined && x.days_to_pay <= 7).length
    soonMonthTotal.value = up.month_total_cny || 0
  } catch (e) { /* toast 已统一处理 */ }
  finally {
    // #ifdef MP-WEIXIN || MP-ALIPAY
    uni.stopPullDownRefresh()
    // #endif
  }
}

onShow(load)
onPullDownRefresh(load)
</script>

<style scoped>
.page { padding-bottom: 30rpx; }

/* ========== Hero 主卡（浅色版） ========== */
/* 改用浅蓝渐变 + 深色文字，与下方白卡同色系过渡，避免深色突兀 */
.hero-card {
  background: linear-gradient(135deg, #eff6ff 0%, #e0e7ff 100%);
  border: 1px solid #dbe4f0;
  border-radius: 20rpx;
  padding: 28rpx 28rpx 22rpx;
  color: #1e293b;
  margin: 16rpx;
  position: relative;
  overflow: hidden;
  box-shadow: 0 6rpx 24rpx rgba(30, 58, 138, 0.06);
}
.hero-card::before {
  content: '';
  position: absolute;
  top: -25%; right: -18%;
  width: 220px; height: 220px;
  /* 装饰光晕改为柔蓝色，融入主背景 */
  background: radial-gradient(circle, rgba(59,130,246,0.12) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}
.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20rpx;
  position: relative;
  z-index: 1;
}
.hero-label {
  font-size: 24rpx;
  color: #64748b;
  letter-spacing: 4rpx;
}
.hero-value {
  font-size: 60rpx;
  font-weight: 700;
  letter-spacing: 2rpx;
  margin-top: 8rpx;
  line-height: 1.15;
  color: #2563eb;
}
.hero-currency {
  font-size: 28rpx;
  font-weight: 500;
  margin-right: 6rpx;
  opacity: 0.65;
  color: #2563eb;
}
.hero-sub {
  font-size: 24rpx;
  color: #64748b;
  margin-top: 6rpx;
}
.hero-sub .up { color: #16a34a; margin-right: 6rpx; }
.hero-sub .down { color: #dc2626; margin-right: 6rpx; }

.hero-edit {
  font-size: 22rpx;
  color: #475569;
  padding: 8rpx 20rpx;
  background: rgba(255,255,255,0.7);
  border: 1px solid #cbd5e1;
  border-radius: 12rpx;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 6rpx;
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 12rpx;
  z-index: 1;
}
.cur-symbol {
  font-size: 26rpx;
  font-weight: 600;
  color: #2563eb;
}

/* ========== 币种切换弹窗（对齐 mine 账户切换弹窗） ========== */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 999;
  display: flex;
  align-items: flex-end;
}
.modal-card {
  width: 100%;
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 32rpx 32rpx 40rpx;
  box-sizing: border-box;
}
.modal-title {
  font-size: 32rpx;
  font-weight: 600;
  text-align: center;
}
.modal-tip {
  font-size: 22rpx;
  color: #999;
  margin: 12rpx 0 24rpx;
  text-align: center;
  line-height: 1.6;
}
.acct-list { display: flex; flex-direction: column; }
.acct-row {
  display: flex;
  align-items: center;
  padding: 26rpx 8rpx;
  border-bottom: 1px solid #f5f5f5;
}
.acct-row:last-child { border-bottom: none; }
.acct-row.on .acct-name { color: #2563eb; font-weight: 600; }
.acct-dot {
  width: 16rpx; height: 16rpx;
  border-radius: 50%;
  margin-right: 20rpx;
  flex-shrink: 0;
}
.acct-name { flex: 1; font-size: 28rpx; color: #333; }
.acct-check { color: #2563eb; font-size: 30rpx; font-weight: 700; }
.modal-actions { display: flex; gap: 20rpx; margin-top: 32rpx; }
.btn-cancel {
  flex: 1;
  height: 84rpx;
  line-height: 84rpx;
  text-align: center;
  border-radius: 16rpx;
  background: #f1f5f9;
  color: #475569;
  font-size: 28rpx;
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
  border-top: 1px solid rgba(30, 58, 138, 0.08);
  box-sizing: border-box;
}
/* 同一行内非首列加左边框 */
.m-metric-item:not(:nth-child(3n+1)):not(:first-child) {
  border-left: 1px solid rgba(30, 58, 138, 0.06);
}
.m-metric-label {
  font-size: 22rpx;
  color: #64748b;
  margin-bottom: 6rpx;
}
.m-metric-value {
  font-size: 34rpx;
  font-weight: 600;
  color: #1e293b;
}
.m-metric-value.positive { color: #16a34a; }
.m-metric-value.negative { color: #dc2626; }

/* ========== 到账提醒条 ========== */
.soon-bar {
  display: flex; align-items: center; gap: 16rpx;
  background: #fff; border: 1px solid #eef0f4;
  border-radius: 20rpx; padding: 22rpx 28rpx; margin: 0 16rpx 8rpx;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
}
.soon-bar.hot { background: #fffbeb; border-color: #fde68a; }
.soon-icon { font-size: 36rpx; }
.soon-text { flex: 1; display: flex; flex-direction: column; gap: 4rpx; min-width: 0; }
.soon-strong { font-size: 26rpx; font-weight: 600; color: #1e293b; }
.soon-bar.hot .soon-strong { color: #b45309; }
.soon-sub { font-size: 22rpx; color: #94a3b8; }
.soon-arrow { font-size: 40rpx; color: #cbd5e1; }

/* ========== 通用区块标题 ========== */
.m-section-title {
  font-size: 28rpx;
  font-weight: 600;
  margin: 28rpx 32rpx 16rpx;
  color: #1a1a1a;
  position: relative;
  padding-left: 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.m-section-extra {
  font-size: 22rpx;
  font-weight: 400;
  color: #94a3b8;
}
.m-section-title::before {
  content: '';
  position: absolute;
  left: 0; top: 50%;
  transform: translateY(-50%);
  width: 6rpx; height: 26rpx;
  background: linear-gradient(180deg, #2563eb 0%, #3b82f6 100%);
  border-radius: 3rpx;
}

/* ========== 分红趋势 ========== */
/* 优化：边框颜色改为更柔和的灰，并加阴影层次 */
.m-chart-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx 16rpx;
  margin: 0 16rpx;
  border: 1px solid #eef0f4;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
}
/* 图例行 */
.m-chart-legend {
  display: flex; align-items: center; gap: 24rpx;
  font-size: 20rpx; color: #94a3b8;
  margin-bottom: 20rpx;
}
.legend-item { display: flex; align-items: center; gap: 8rpx; }
.legend-swatch { width: 14rpx; height: 14rpx; border-radius: 4rpx; }
.legend-swatch.green { background: #059669; }
.legend-swatch.avg { width: 22rpx; height: 0; border-top: 2rpx dashed #94a3b8; border-radius: 0; }
.legend-tip { margin-left: auto; font-size: 20rpx; color: #cbd5e1; }

.m-bar-chart {
  position: relative;
  display: flex;
  align-items: flex-end;
  height: 260rpx;
  gap: 4rpx;
}
/* 月均虚线参考线（bottom 由脚本计算，26 = 标签区高度补偿） */
.avg-line {
  position: absolute; left: 0; right: 0;
  border-top: 2rpx dashed #cbd5e1;
  pointer-events: none;
  z-index: 0;
}
.m-bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
}
.m-bar-wrap {
  height: 220rpx;
  display: flex;
  align-items: flex-end;
  width: 100%;
  justify-content: center;
  position: relative;
}
.m-bar {
  width: 20rpx;
  background: linear-gradient(180deg, #2563eb 0%, #3b82f6 100%);
  border-radius: 6rpx 6rpx 0 0;
  min-height: 4rpx;
}
/* 当月柱高亮为绿色，突出"本月已收" */
.m-bar.cur { background: linear-gradient(180deg, #059669 0%, #34d399 100%); }
/* 零值月：浅灰矮柱 */
.m-bar.zero { background: #e2e8f0; height: 4rpx !important; }
/* 选中柱加深 */
.m-bar.sel { filter: saturate(1.4) brightness(0.85); }
/* 金额气泡 */
.m-bubble {
  position: absolute; left: 50%; transform: translateX(-50%);
  background: #1e293b; color: #fff;
  font-size: 20rpx; padding: 6rpx 14rpx; border-radius: 10rpx;
  white-space: nowrap; z-index: 3;
}
.m-bubble::after {
  content: '';
  position: absolute; left: 50%; bottom: -8rpx; transform: translateX(-50%);
  border: 5rpx solid transparent; border-top-color: #1e293b;
}
.m-bar-label { font-size: 18rpx; color: #94a3b8; margin-top: 8rpx; }
.m-bar-label.cur { color: #059669; font-weight: 600; }

/* ========== 持仓快照（2 列宫格，替代原 5 行长列表） ========== */
.snap-grid {
  display: flex; flex-wrap: wrap;
  background: #fff;
  border-radius: 20rpx;
  margin: 0 16rpx;
  border: 1px solid #eef0f4;
  overflow: hidden;
  box-shadow: 0 4rpx 16rpx rgba(15, 23, 42, 0.04);
}
.snap-cell {
  width: 50%; box-sizing: border-box;
  padding: 26rpx 28rpx;
  border-bottom: 1px solid #f1f5f9;
}
.snap-cell:nth-child(odd) { border-right: 1px solid #f1f5f9; }
.snap-cell:nth-last-child(-n+2) { border-bottom: none; }
.snap-label { font-size: 22rpx; color: #94a3b8; margin-bottom: 10rpx; }
.snap-value { font-size: 30rpx; font-weight: 700; color: #1e293b; }
.snap-value.positive { color: #16a34a; }
.snap-value.negative { color: #dc2626; }
.snap-value.green { color: #059669; }
.snap-value.blue { color: #1e3a8a; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 900px; margin: 0 auto; }
}
/* #endif */
</style>
