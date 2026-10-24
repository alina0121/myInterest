<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="分红日历 · 记录" subtitle="到账节奏与历史分红明细" /><!-- #endif -->

    <!-- 大功能切换：日历 / 分红记录 -->
    <view class="seg-wrap">
      <view class="seg">
        <view :class="['seg-item', tab === 'calendar' ? 'on' : '']" @click="setTab('calendar')">
          <text class="seg-emoji">📅</text><text class="seg-text">日历</text>
        </view>
        <view :class="['seg-item', tab === 'records' ? 'on' : '']" @click="setTab('records')">
          <text class="seg-emoji">📋</text><text class="seg-text">分红记录</text>
        </view>
      </view>
    </view>

    <!-- ===== 日历 ===== -->
    <block v-if="tab === 'calendar'">
    <!-- 月份切换 -->
    <view class="nav">
      <view class="nav-btn" @click="prev">‹</view>
      <view class="nav-title">{{ year }} 年 {{ month }} 月</view>
      <view class="nav-right">
        <view v-if="!isCurrentMonth" class="today-btn" @click="goToday">今</view>
        <view class="nav-btn" @click="next">›</view>
      </view>
    </view>

    <!-- 月汇总（渐变卡，与分红预告页合计条同风格） -->
    <view class="sum">
      <view class="sum-cell">
        <view class="sum-val sum-green">¥{{ fmt(data.month_confirmed) }}</view>
        <view class="sum-label">本月已到账 · {{ confirmedCount }} 笔</view>
      </view>
      <view class="sum-divider"></view>
      <view class="sum-cell">
        <view class="sum-val sum-amber">¥{{ fmt(data.month_pending) }}</view>
        <view class="sum-label">预告中 · {{ pendingCount }} 笔</view>
      </view>
    </view>

    <!-- 月历 -->
    <view class="card cal">
      <view class="week">
        <text v-for="w in weeks" :key="w" class="w-cell">{{ w }}</text>
      </view>
      <view class="days">
        <view v-for="(cell, i) in cells" :key="i"
              :class="['day-cell', cell.day ? '' : 'blank', selectedDay === cell.day ? 'sel' : '', hasDiv(cell.day) ? 'has-div' : '']"
              @click="cell.day && selectDay(cell.day)">
          <text :class="['d-num', hasDiv(cell.day) ? 'has' : '', isToday(cell.day) ? 'today' : '', selectedDay === cell.day ? 'sel-num' : '']">{{ cell.day || '' }}</text>
          <view v-if="dayItems(cell.day).length" class="d-dots">
            <view v-for="(d, j) in dayItems(cell.day)" :key="j"
                  class="dot"
                  :style="{ background: d.status === 'confirmed' ? '#059669' : '#d97706' }"></view>
          </view>
        </view>
      </view>
      <!-- 图例 -->
      <view class="cal-legend">
        <view class="lg-item"><view class="dot" style="background:#059669"></view><text>已到账</text></view>
        <view class="lg-item"><view class="dot" style="background:#d97706"></view><text>预告中</text></view>
        <text class="lg-tip" v-if="isCurrentMonth">点日期看明细</text>
      </view>
    </view>

    <!-- 选中日的分红 -->
    <view class="section-title" v-if="selectedDay">
      {{ month }}月{{ selectedDay }}日 分红
      <text class="text-muted" style="font-size:24rpx;font-weight:400">{{ dayItems(selectedDay).length }} 笔</text>
    </view>
    <view class="card" v-if="selectedDay">
      <view v-if="!dayItems(selectedDay).length" class="empty" style="padding:40rpx 0">当天没有分红</view>
      <view v-for="(d, i) in dayItems(selectedDay)" :key="i" class="day-row">
        <view class="dot"
              :style="{ background: d.status === 'confirmed' ? '#059669' : '#d97706' }"></view>
        <view style="flex:1">
          <view class="dr-name">{{ d.holding_name }}</view>
          <view class="text-muted" style="font-size:22rpx">{{ d.code }} · {{ d.dps }}/股 × {{ d.shares }}股</view>
        </view>
        <view :class="d.status === 'confirmed' ? 'text-emerald' : 'text-amber'">
          {{ sym(d.currency) }}{{ fmt(d.net || d.gross) }}
        </view>
      </view>
    </view>

    </block>

    <!-- ===== 分红记录 ===== -->
    <block v-else>
      <!-- 状态筛选 -->
      <scroll-view scroll-x class="chips" :show-scrollbar="false">
        <view :class="['chip', rStatus === '' ? 'on' : '']" @click="setStatus('')">全部</view>
        <view :class="['chip', rStatus === 'confirmed' ? 'on' : '']" @click="setStatus('confirmed')">已到账</view>
        <view :class="['chip', rStatus === 'pending' ? 'on' : '']" @click="setStatus('pending')">预告</view>
        <view :class="['chip', rYear ? 'on' : '']" @click="toggleYear">{{ rYear || now.getFullYear() }}年</view>
      </scroll-view>

      <!-- 市场筛选 -->
      <scroll-view scroll-x class="chips chips-market" :show-scrollbar="false">
        <view :class="['chip', rMarket === '' ? 'on' : '']" @click="setMarket('')">全部</view>
        <view v-for="m in MARKETS" :key="m.value"
              :class="['chip', rMarket === m.value ? 'on' : '']"
              @click="setMarket(m.value)">{{ m.label }}</view>
      </scroll-view>

      <!-- 汇总条 -->
      <view class="sum-bar">
        <text>共 {{ rTotal }} 笔</text>
        <text class="text-emerald">已到账 ¥{{ fmt(rNet) }}</text>
        <text class="text-amber" v-if="rPend > 0">预告 ¥{{ fmt(rPend) }}</text>
      </view>

      <view v-if="!rList.length && !rLoading" class="empty card">暂无分红记录</view>

      <view v-for="d in rList" :key="d.id" class="card d-card" @click="rOpenId = rOpenId === d.id ? null : d.id">
        <!-- 第一层：徽章 + 名称 | 税后金额 -->
        <view class="d-top">
          <view class="d-name-wrap">
            <text :class="['tag', badgeClass(d.market)]">{{ marketMap[d.market]?.label }}</text>
            <text class="d-name">{{ d.holding_name }}</text>
          </view>
          <view class="d-amt-wrap">
            <text :class="['d-amt-main', d.status === 'confirmed' ? 'text-emerald' : 'text-amber']">
              {{ sym(d.currency) }}{{ fmt(d.net_amount) }}
            </text>
            <text class="d-cur">{{ d.currency }}</text>
          </view>
        </view>

        <!-- 第二层：四列指标 -->
        <view class="d-metrics">
          <view class="d-cell">
            <view class="d-label">每股税前</view>
            <view class="d-value">{{ sym(d.currency) }}{{ fmt(d.dps) }}</view>
          </view>
          <view class="d-cell">
            <view class="d-label">登记持仓</view>
            <view class="d-value">{{ fmt(d.shares) }}股</view>
          </view>
          <view class="d-cell">
            <view class="d-label">税前</view>
            <view class="d-value">{{ sym(d.currency) }}{{ fmt(d.gross_amount) }}</view>
          </view>
          <view class="d-cell">
            <view class="d-label">扣税</view>
            <view class="d-value" :class="d.tax > 0 ? 'text-amber' : ''">
              {{ d.tax > 0 ? sym(d.currency) + fmt(d.tax) : '—' }}
            </view>
          </view>
        </view>

        <!-- 第三层：到账日期 + 状态 + 批次展开提示 -->
        <view class="d-foot">
          <text class="d-pay">📅 {{ d.status === 'confirmed' ? d.pay_date + ' 已到账' : d.pay_date + ' 到账' }}</text>
          <view class="d-foot-right">
            <text :class="['tag', d.status === 'confirmed' ? 'badge-confirmed' : 'badge-pending']">
              {{ d.status === 'confirmed' ? '已到账' : '预告' }}
            </text>
            <text :class="['d-arrow', rOpenId === d.id ? 'open' : '']" v-if="d.batches?.length">›</text>
          </view>
        </view>

        <!-- 批次归属 -->
        <view v-if="rOpenId === d.id" class="alloc">
          <view class="alloc-title">批次归属明细（共 {{ d.batches?.length || 0 }} 个批次参与）</view>
          <view v-for="(a, i) in d.batches" :key="i" class="alloc-row">
            <text>{{ a.lot_date }} 批次</text>
            <text>{{ fmt(a.shares) }} 股 · 税率 {{ fmt(a.rate * 100) }}%</text>
            <text class="text-emerald">{{ sym(d.currency) }}{{ fmt(a.gross) }}</text>
          </view>
        </view>
      </view>

      <!-- 加载更多 -->
      <view v-if="rHasMore" class="load-more" @click="loadMoreRecords">
        <text v-if="rLoading" class="text-muted">加载中...</text>
        <text v-else>加载更多</text>
      </view>
      <view v-else-if="rList.length" class="load-more">
        <text class="text-muted">没有更多了</text>
      </view>
    </block>

    <view style="height: 40rpx"></view>
    <!-- #ifdef H5 --><CustomTab current="/pages/calendar/calendar" /><!-- #endif -->
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onShow, onReachBottom, onPullDownRefresh } from '@dcloudio/uni-app'
import { apiCalendar, apiDividends } from '@/api'
import { userStore } from '@/store/user'
import { MARKETS, marketMap, badgeClass, currencyMap } from '@/utils/constants'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'

const now = new Date()
const tab = ref('calendar')
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const selectedDay = ref(null)
const data = ref({ days: {} })

// ---------- 大功能切换 ----------
function setTab(t) {
  tab.value = t
  if (t === 'records' && !rList.value.length && !rLoading.value) loadRecords(true)
}

const weeks = ['日', '一', '二', '三', '四', '五', '六']

/** 是否正在查看当前月 */
const isCurrentMonth = computed(() =>
  year.value === now.getFullYear() && month.value === now.getMonth() + 1)
function isToday(day) {
  return isCurrentMonth.value && day === now.getDate()
}
function goToday() {
  year.value = now.getFullYear()
  month.value = now.getMonth() + 1
  load()
}

/** 各状态笔数（图例/汇总用） */
const confirmedCount = computed(() => {
  let n = 0
  Object.values(data.value.days || {}).forEach(list => { n += list.filter(d => d.status === 'confirmed').length })
  return n
})
const pendingCount = computed(() => {
  let n = 0
  Object.values(data.value.days || {}).forEach(list => { n += list.filter(d => d.status !== 'confirmed').length })
  return n
})

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

const cells = computed(() => {
  const first = new Date(year.value, month.value - 1, 1).getDay()
  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const arr = []
  for (let i = 0; i < first; i++) arr.push({ day: '' })
  for (let d = 1; d <= daysInMonth; d++) arr.push({ day: d })
  return arr
})

function dayItems(day) {
  return data.value.days[String(day)] || []
}
function hasDiv(day) {
  return dayItems(day).length > 0
}

async function load() {
  selectedDay.value = null
  // v8：账户跟随（币种转换仅在总览页生效，日历页按 CNY 显示）
  const params = {}
  if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
    params.account = userStore.currentAccount
  }
  data.value = await apiCalendar(year.value, month.value, params)
  // 当前月自动聚焦最近一次待到账日（>= 今天），让用户一进来就看到"钱什么时候来"
  if (isCurrentMonth.value) {
    const today = now.getDate()
    const upcoming = Object.keys(data.value.days || {})
      .map(Number).filter(d => d >= today).sort((a, b) => a - b)
    selectedDay.value = upcoming.length ? upcoming[0] : null
  }
  // #ifdef MP-WEIXIN || MP-ALIPAY
  uni.stopPullDownRefresh()
  // #endif
}

function selectDay(d) { selectedDay.value = selectedDay.value === d ? null : d }
function prev() {
  if (month.value === 1) { year.value--; month.value = 12 } else month.value--
  load()
}
function next() {
  if (month.value === 12) { year.value++; month.value = 1 } else month.value++
  load()
}

// ---------- 分红记录 tab（原 dividends/list 完整功能内联） ----------
const rList = ref([])
const rTotal = ref(0)
const rStatus = ref('')
const rYear = ref('')
const rMarket = ref('')
const rOpenId = ref(null)
const rPage = ref(1)
const rHasMore = ref(false)
const rLoading = ref(false)
const rNet = ref(0)
const rPend = ref(0)

/** v8：账户跟随（币种转换仅在总览页生效，分红页按 CNY 显示） */
function filterParams() {
  const p = {}
  if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
    p.account = userStore.currentAccount
  }
  return p
}

async function loadRecords(reset = true) {
  if (rLoading.value) return
  if (reset) {
    rPage.value = 1
    rList.value = []
    rHasMore.value = true
  }
  rLoading.value = true
  try {
    const params = { page: rPage.value, page_size: 20, expand: 'batches' }
    if (rStatus.value) params.status = rStatus.value
    if (rYear.value) params.year = rYear.value
    if (rMarket.value) params.market = rMarket.value
    Object.assign(params, filterParams())
    const res = await apiDividends(params)
    rList.value = reset ? res.items : [...rList.value, ...res.items]
    rTotal.value = res.total
    rHasMore.value = rList.value.length < res.total
  } finally {
    rLoading.value = false
  }
}

async function loadSummary() {
  const params = { page: 1, page_size: 999 }
  if (rStatus.value) params.status = rStatus.value
  if (rYear.value) params.year = rYear.value
  if (rMarket.value) params.market = rMarket.value
  Object.assign(params, filterParams())
  const res = await apiDividends(params)
  // 后端已将各币种统一换算为 net_cny，直接求和
  rNet.value = res.items
    .filter(d => d.status === 'confirmed')
    .reduce((s, d) => s + (d.net_cny || 0), 0)
  rPend.value = res.items
    .filter(d => d.status === 'pending')
    .reduce((s, d) => s + (d.net_cny || 0), 0)
}

function setStatus(s) { rStatus.value = s; refreshRecords() }
function setMarket(m) { rMarket.value = m; refreshRecords() }
function toggleYear() {
  rYear.value = rYear.value ? '' : String(now.getFullYear())
  refreshRecords()
}
async function refreshRecords() {
  await Promise.all([loadRecords(true), loadSummary()])
  // #ifdef MP-WEIXIN || MP-ALIPAY
  uni.stopPullDownRefresh()
  // #endif
}
async function loadMoreRecords() {
  if (!rHasMore.value || rLoading.value) return
  rPage.value++
  await loadRecords(false)
}

// 支持 ?tab=records 直达分红记录视图
onLoad((options) => {
  if (options && options.tab === 'records') {
    tab.value = 'records'
    loadRecords(true)
  }
})

onShow(() => { tab.value === 'calendar' ? load() : (rList.value.length ? refreshRecords() : loadRecords(true)) })
onPullDownRefresh(() => { tab.value === 'calendar' ? load() : refreshRecords() })
// 记录列表触底翻页（仅记录 tab 生效）
onReachBottom(() => { if (tab.value === 'records') loadMoreRecords() })
</script>

<style scoped>
/* 大功能 segment（与持仓页同款） */
.seg-wrap { display: flex; padding: 20rpx 24rpx 4rpx; }
.seg {
  display: flex; background: #eef1f6; border-radius: 20rpx; padding: 6rpx;
  width: 100%;
}
.seg-item {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 8rpx;
  padding: 16rpx 0; border-radius: 16rpx; color: #64748b;
}
.seg-item.on {
  background: #fff; color: #1e3a8a;
  box-shadow: 0 2rpx 8rpx rgba(15, 23, 42, 0.08);
}
.seg-emoji { font-size: 28rpx; line-height: 1; }
.seg-text { font-size: 27rpx; font-weight: 600; }

.nav { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 40rpx 0; }
.nav-btn { font-size: 48rpx; color: #1e3a8a; width: 80rpx; text-align: center; }
.nav-right { display: flex; align-items: center; }
.nav-title { font-size: 32rpx; font-weight: 700; color: #1e293b; }
.today-btn {
  width: 56rpx; height: 56rpx; line-height: 56rpx; text-align: center;
  font-size: 26rpx; font-weight: 600; color: #1e3a8a;
  background: #eff6ff; border-radius: 50%; margin-right: 8rpx;
}

.sum {
  display: flex; margin: 20rpx 24rpx 0;
  background: linear-gradient(135deg, #1e3a8a, #2d4ea8);
  border-radius: 24rpx; padding: 32rpx 26rpx;
  box-shadow: 0 6rpx 16rpx rgba(30, 58, 138, 0.25);
}
.sum-cell { flex: 1; text-align: center; }
.sum-divider { width: 1rpx; background: rgba(255, 255, 255, 0.2); margin: 8rpx 0; }
.sum-val { font-size: 36rpx; font-weight: 700; color: #fff; }
.sum-val.sum-green { color: #6ee7b7; }
.sum-val.sum-amber { color: #fcd34d; }
.sum-label { font-size: 22rpx; color: rgba(255, 255, 255, 0.7); margin-top: 8rpx; }

.cal { padding: 20rpx; }
.week, .days { display: flex; flex-wrap: wrap; }
.w-cell { width: calc(100% / 7); text-align: center; font-size: 24rpx; color: #94a3b8; padding: 12rpx 0; }
.day-cell {
  width: calc(100% / 7); height: 96rpx;
  display: flex; flex-direction: column; align-items: center; padding-top: 12rpx;
  border-radius: 12rpx;
}
.day-cell.blank { visibility: hidden; }
.day-cell.has-div { background: #f6f8fb; }
.day-cell.sel { background: #eff6ff; box-shadow: inset 0 0 0 2rpx #93c5fd; }
.d-num {
  width: 52rpx; height: 52rpx; line-height: 52rpx; text-align: center;
  font-size: 28rpx; color: #475569; border-radius: 50%;
}
.d-num.has { color: #1e3a8a; font-weight: 700; }
/* 今天：蓝色描边圈 */
.d-num.today { box-shadow: inset 0 0 0 3rpx #2563eb; color: #2563eb; font-weight: 700; }
/* 选中：实心蓝圆白字 */
.d-num.sel-num { background: #1e3a8a; color: #fff !important; font-weight: 700; }
.d-dots { display: flex; gap: 6rpx; margin-top: 6rpx; height: 12rpx; }
.dot { width: 12rpx; height: 12rpx; border-radius: 50%; }

/* 图例 */
.cal-legend {
  display: flex; align-items: center; gap: 28rpx;
  padding: 16rpx 12rpx 4rpx; font-size: 20rpx; color: #94a3b8;
}
.lg-item { display: flex; align-items: center; gap: 8rpx; }
.lg-item .dot { width: 10rpx; height: 10rpx; }
.lg-tip { margin-left: auto; }
.day-row { display: flex; align-items: center; gap: 16rpx; padding: 20rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.day-row:last-child { border-bottom: none; }
.dr-name { font-size: 28rpx; font-weight: 500; }

/* ===== 分红记录 tab ===== */
.chips { white-space: nowrap; padding: 20rpx 24rpx 0; }
.chips-market { padding-top: 16rpx; }
.chip {
  display: inline-block; padding: 10rpx 30rpx; margin-right: 16rpx;
  background: #fff; color: #64748b; border-radius: 32rpx; font-size: 26rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}
.chip.on { background: #1e3a8a; color: #fff; box-shadow: 0 4rpx 12rpx rgba(30, 58, 138, 0.18); }
.sum-bar {
  display: flex; gap: 30rpx; padding: 20rpx 32rpx 0;
  font-size: 24rpx; color: #64748b;
}
.d-card { padding: 24rpx 28rpx; }
.d-top { display: flex; justify-content: space-between; align-items: center; }
.d-name-wrap { display: flex; align-items: center; min-width: 0; }
.d-name {
  font-size: 30rpx; font-weight: 600; margin-left: 10rpx; color: #1e293b;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.d-amt-wrap { display: flex; align-items: baseline; flex-shrink: 0; margin-left: 12rpx; }
.d-amt-main { font-size: 32rpx; font-weight: 700; }
.d-cur { font-size: 20rpx; color: #94a3b8; margin-left: 6rpx; }

/* 四列指标（持仓卡同款发丝线分区） */
.d-metrics {
  display: flex; margin-top: 20rpx; padding: 16rpx 0;
  border-top: 1rpx solid #f8fafc; border-bottom: 1rpx solid #f8fafc;
}
.d-cell { flex: 1; text-align: center; }
.d-label { font-size: 22rpx; color: #94a3b8; margin-bottom: 4rpx; }
.d-value { font-size: 26rpx; font-weight: 600; color: #334155; }

.d-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 16rpx; }
.d-pay { font-size: 22rpx; color: #64748b; }
.d-foot-right { display: flex; align-items: center; gap: 10rpx; }
.d-arrow {
  font-size: 32rpx; color: #cbd5e1; line-height: 1;
  transition: transform 0.2s; display: inline-block;
}
.d-arrow.open { transform: rotate(90deg); }
.alloc { margin-top: 18rpx; background: #f8fafc; border-radius: 12rpx; padding: 18rpx 20rpx; }
.alloc-title { font-size: 24rpx; font-weight: 600; color: #475569; margin-bottom: 10rpx; }
.alloc-row { display: flex; justify-content: space-between; font-size: 24rpx; color: #64748b; padding: 6rpx 0; }
.load-more { text-align: center; padding: 30rpx 0; font-size: 26rpx; color: #1e3a8a; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 900px; margin: 0 auto; }
  .d-card { display: inline-block; width: calc(50% - 24rpx); margin: 12rpx; vertical-align: top; box-sizing: border-box; }
}
/* #endif */
</style>
