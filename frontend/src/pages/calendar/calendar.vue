<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="分红日历" subtitle="一眼看清每月到账节奏" /><!-- #endif -->
    <!-- 月份切换 -->
    <view class="nav">
      <view class="nav-btn" @click="prev">‹</view>
      <view class="nav-title">{{ year }} 年 {{ month }} 月</view>
      <view class="nav-btn" @click="next">›</view>
    </view>

    <!-- 月汇总 -->
    <view class="sum">
      <view class="sum-cell">
        <view class="sum-val text-emerald">¥{{ fmt(data.month_confirmed_cny) }}</view>
        <view class="sum-label">本月已到账</view>
      </view>
      <view class="sum-divider"></view>
      <view class="sum-cell">
        <view class="sum-val text-amber">¥{{ fmt(data.month_pending_cny) }}</view>
        <view class="sum-label">预告中</view>
      </view>
    </view>

    <!-- 月历 -->
    <view class="card cal">
      <view class="week">
        <text v-for="w in weeks" :key="w" class="w-cell">{{ w }}</text>
      </view>
      <view class="days">
        <view v-for="(cell, i) in cells" :key="i"
              :class="['day-cell', cell.day ? '' : 'blank', selectedDay === cell.day ? 'sel' : '']"
              @click="cell.day && selectDay(cell.day)">
          <text :class="['d-num', hasDiv(cell.day) ? 'has' : '']">{{ cell.day || '' }}</text>
          <view v-if="dayItems(cell.day).length" class="d-dots">
            <view v-for="(d, j) in dayItems(cell.day)" :key="j"
                  class="dot"
                  :style="{ background: d.status === 'confirmed' ? '#059669' : '#d97706' }"></view>
          </view>
        </view>
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

    <!-- 本月分红流水 -->
    <view class="section-title">
      本月分红流水
      <text class="text-muted" style="font-size:24rpx;font-weight:400">{{ timelineList.length }} 笔</text>
    </view>
    <view class="card timeline-card" v-if="timelineList.length">
      <view v-for="(d, i) in timelineList" :key="i" class="tl-row">
        <view class="tl-rail">
          <view class="tl-dot"
                :style="{ background: d.status === 'confirmed' ? '#059669' : '#d97706' }"></view>
          <view v-if="i < timelineList.length - 1" class="tl-line"></view>
        </view>
        <view class="tl-body">
          <view class="tl-head">
            <view class="tl-date">
              <text class="tl-day">{{ d.dayNum }}</text>
              <text class="tl-month">日</text>
            </view>
            <view class="tl-name">{{ d.holding_name }}</view>
            <view :class="['tag', d.status === 'confirmed' ? 'badge-confirmed' : 'badge-pending']">
              {{ d.status === 'confirmed' ? '已到账' : '预告' }}
            </view>
          </view>
          <view class="tl-meta">
            <text class="text-muted">{{ d.code }}</text>
            <text class="text-muted">{{ d.dps }}/股 × {{ d.shares }}股</text>
          </view>
          <view class="tl-amt" :class="d.status === 'confirmed' ? 'text-emerald' : 'text-amber'">
            {{ sym(d.currency) }}{{ fmt(d.net || d.gross) }}
            <text v-if="d.tax > 0" class="text-muted tl-tax">税 {{ sym(d.currency) }}{{ fmt(d.tax) }}</text>
          </view>
        </view>
      </view>
    </view>
    <view v-else class="card empty">本月暂无分红流水</view>

    <view style="height: 40rpx"></view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
import { apiCalendar } from '@/api'
import { userStore } from '@/store/user'
import { currencyMap } from '@/utils/constants'
import WebLayout from '@/components/WebLayout.vue'

const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const selectedDay = ref(null)
const data = ref({ days: {} })

const weeks = ['日', '一', '二', '三', '四', '五', '六']

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

// 本月所有分红按日期排序的时间线
const timelineList = computed(() => {
  const days = data.value.days || {}
  const arr = []
  Object.keys(days).forEach(dayKey => {
    const dayNum = parseInt(dayKey, 10)
    const fullDate = `${year.value}-${String(month.value).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`
    ;(days[dayKey] || []).forEach(d => {
      arr.push({ ...d, dayNum, fullDate })
    })
  })
  arr.sort((a, b) => {
    if (a.dayNum !== b.dayNum) return a.dayNum - b.dayNum
    return a.holding_name?.localeCompare(b.holding_name || '') || 0
  })
  return arr
})

async function load() {
  selectedDay.value = null
  // v8：账户跟随
  const params = {}
  if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
    params.account = userStore.currentAccount
  }
  if (userStore.displayCurrency && userStore.displayCurrency !== 'CNY') {
    params.display_currency = userStore.displayCurrency
  }
  data.value = await apiCalendar(year.value, month.value, params)
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

onShow(load)
onPullDownRefresh(load)
</script>

<style scoped>
.nav { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 40rpx 0; }
.nav-btn { font-size: 48rpx; color: #1e3a8a; width: 80rpx; text-align: center; }
.nav-title { font-size: 32rpx; font-weight: 700; color: #1e293b; }

.sum {
  display: flex; margin: 20rpx 24rpx 0; background: #fff;
  border-radius: 24rpx; padding: 32rpx 26rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}
.sum-cell { flex: 1; text-align: center; }
.sum-divider { width: 1rpx; background: #f1f5f9; margin: 8rpx 0; }
.sum-val { font-size: 36rpx; font-weight: 700; }
.sum-label { font-size: 22rpx; color: #94a3b8; margin-top: 8rpx; }

.cal { padding: 20rpx; }
.week, .days { display: flex; flex-wrap: wrap; }
.w-cell { width: calc(100% / 7); text-align: center; font-size: 24rpx; color: #94a3b8; padding: 12rpx 0; }
.day-cell { width: calc(100% / 7); height: 96rpx; display: flex; flex-direction: column; align-items: center; padding-top: 12rpx; }
.day-cell.blank { visibility: hidden; }
.day-cell.sel { background: #eff6ff; border-radius: 12rpx; }
.d-num { font-size: 28rpx; color: #475569; }
.d-num.has { color: #1e3a8a; font-weight: 700; }
.d-dots { display: flex; gap: 6rpx; margin-top: 8rpx; }
.dot { width: 12rpx; height: 12rpx; border-radius: 50%; }
.day-row { display: flex; align-items: center; gap: 16rpx; padding: 20rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.day-row:last-child { border-bottom: none; }
.dr-name { font-size: 28rpx; font-weight: 500; }

/* 时间线 */
.timeline-card { padding: 12rpx 28rpx; }
.tl-row { display: flex; padding: 18rpx 0; }
.tl-rail { width: 32rpx; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; padding-top: 8rpx; }
.tl-dot { width: 16rpx; height: 16rpx; border-radius: 50%; flex-shrink: 0; }
.tl-line { flex: 1; width: 2rpx; background: #e2e8f0; margin-top: 6rpx; }
.tl-body { flex: 1; padding-bottom: 12rpx; }
.tl-head { display: flex; align-items: center; gap: 14rpx; }
.tl-date { display: flex; align-items: baseline; }
.tl-day { font-size: 28rpx; font-weight: 700; color: #1e293b; }
.tl-month { font-size: 20rpx; color: #94a3b8; margin-left: 2rpx; }
.tl-name { flex: 1; font-size: 28rpx; font-weight: 500; color: #1e293b; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tl-meta { display: flex; gap: 20rpx; margin-top: 8rpx; font-size: 22rpx; flex-wrap: wrap; }
.tl-amt { margin-top: 10rpx; font-size: 30rpx; font-weight: 700; }
.tl-tax { font-size: 22rpx; font-weight: 400; margin-left: 14rpx; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 900px; margin: 0 auto; }
}
/* #endif */
</style>
