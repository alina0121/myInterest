<template>
  <view class="page">
    <!-- 月份切换 -->
    <view class="nav">
      <view class="nav-btn" @click="prev">‹</view>
      <view class="nav-title">{{ year }} 年 {{ month }} 月</view>
      <view class="nav-btn" @click="next">›</view>
    </view>

    <!-- 月汇总 -->
    <view class="sum">
      <view class="sum-cell">
        <view class="sum-val text-income">¥{{ fmt(data.month_confirmed_cny) }}</view>
        <view class="sum-label">本月已到账</view>
      </view>
      <view class="sum-cell">
        <view class="sum-val text-pending">¥{{ fmt(data.month_pending_cny) }}</view>
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
                  class="dot" :style="{ background: d.status === 'confirmed' ? '#16a34a' : '#f59e0b' }"></view>
          </view>
        </view>
      </view>
    </view>

    <!-- 选中日的分红 -->
    <view class="section-title" v-if="selectedDay">{{ month }}月{{ selectedDay }}日 分红</view>
    <view class="card" v-if="selectedDay">
      <view v-if="!dayItems(selectedDay).length" class="empty" style="padding:40rpx 0">当天没有分红</view>
      <view v-for="(d, i) in dayItems(selectedDay)" :key="i" class="day-row">
        <view class="dot" :style="{ background: d.status === 'confirmed' ? '#16a34a' : '#f59e0b' }"></view>
        <view style="flex:1">
          <view class="dr-name">{{ d.holding_name }}</view>
          <view class="text-muted" style="font-size:22rpx">{{ d.code }} · {{ d.dps }}/股 × {{ d.shares }}股</view>
        </view>
        <view :class="d.status === 'confirmed' ? 'text-income' : 'text-pending'">
          {{ sym(d.currency) }}{{ fmt(d.net_amount || d.gross_amount) }}
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiCalendar } from '@/api'
import { currencyMap } from '@/utils/constants'

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

async function load() {
  selectedDay.value = null
  data.value = await apiCalendar(year.value, month.value)
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
</script>

<style scoped>
.nav { display: flex; align-items: center; justify-content: space-between; padding: 24rpx 40rpx 0; }
.nav-btn { font-size: 48rpx; color: #1668dc; width: 80rpx; text-align: center; }
.nav-title { font-size: 32rpx; font-weight: 700; }
.sum { display: flex; margin: 20rpx 24rpx 0; background: #fff; border-radius: 20rpx; padding: 26rpx; box-shadow: 0 4rpx 16rpx rgba(22,104,220,0.06); }
.sum-cell { flex: 1; text-align: center; }
.sum-val { font-size: 34rpx; font-weight: 700; }
.sum-label { font-size: 22rpx; color: #94a3b8; margin-top: 8rpx; }
.cal { padding: 20rpx; }
.week, .days { display: flex; flex-wrap: wrap; }
.w-cell { width: calc(100% / 7); text-align: center; font-size: 24rpx; color: #94a3b8; padding: 12rpx 0; }
.day-cell { width: calc(100% / 7); height: 96rpx; display: flex; flex-direction: column; align-items: center; padding-top: 12rpx; }
.day-cell.blank { visibility: hidden; }
.day-cell.sel { background: #eff6ff; border-radius: 12rpx; }
.d-num { font-size: 28rpx; color: #475569; }
.d-num.has { color: #1668dc; font-weight: 700; }
.d-dots { display: flex; gap: 6rpx; margin-top: 8rpx; }
.dot { width: 12rpx; height: 12rpx; border-radius: 50%; }
.day-row { display: flex; align-items: center; gap: 16rpx; padding: 20rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.day-row:last-child { border-bottom: none; }
.dr-name { font-size: 28rpx; font-weight: 500; }
</style>
