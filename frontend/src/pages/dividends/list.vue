<template>
  <view class="page">
    <!-- 状态筛选 -->
    <scroll-view scroll-x class="chips" :show-scrollbar="false">
      <view :class="['chip', status === '' ? 'on' : '']" @click="setStatus('')">全部</view>
      <view :class="['chip', status === 'confirmed' ? 'on' : '']" @click="setStatus('confirmed')">已到账</view>
      <view :class="['chip', status === 'pending' ? 'on' : '']" @click="setStatus('pending')">预告</view>
      <view :class="['chip', year ? 'on' : '']" @click="toggleYear">{{ year || new Date().getFullYear() }}年</view>
    </scroll-view>

    <!-- 汇总条 -->
    <view class="sum-bar">
      <text>共 {{ total }} 笔</text>
      <text class="text-income">已到账 ¥{{ fmt(netSum) }}</text>
      <text class="text-pending" v-if="pendSum > 0">预告 ¥{{ fmt(pendSum) }}</text>
    </view>

    <view v-if="!list.length" class="empty card">暂无分红记录</view>

    <view v-for="d in list" :key="d.id" class="card d-card" @click="toggle(d.id)">
      <view class="d-head">
        <view>
          <text class="tag" :style="{ background: marketMap[d.market]?.color }">{{ marketMap[d.market]?.label }}</text>
          <text class="d-name">{{ d.holding_name }}</text>
        </view>
        <view class="d-amt">
          <view :class="d.status === 'confirmed' ? 'text-income' : 'text-pending'">
            {{ sym(d.currency) }}{{ fmt(d.net_amount) }}
          </view>
          <view class="text-muted" style="font-size:22rpx">{{ d.pay_date }}</view>
        </view>
      </view>
      <view class="d-line">
        <text>每股 {{ sym(d.currency) }}{{ fmt(d.dps) }}</text>
        <text>登记日持仓 {{ d.shares }} 股</text>
        <text>税前 {{ sym(d.currency) }}{{ fmt(d.gross_amount) }}</text>
        <text v-if="d.tax > 0" class="text-pending">税 {{ sym(d.currency) }}{{ fmt(d.tax) }}</text>
        <text class="tag" :style="{ background: d.status === 'confirmed' ? '#16a34a' : '#f59e0b' }">
          {{ d.status === 'confirmed' ? '已到账' : '预告' }}
        </text>
      </view>
      <!-- 批次归属 -->
      <view v-if="openId === d.id" class="alloc">
        <view class="alloc-title">批次归属明细（共 {{ d.allocations?.length || 0 }} 个批次参与）</view>
        <view v-for="(a, i) in d.allocations" :key="i" class="alloc-row">
          <text>{{ a.lot_date }} 批次</text>
          <text>{{ a.shares }} 股 · 税 {{ sym(d.currency) }}{{ fmt(a.tax) }}</text>
          <text class="text-income">{{ sym(d.currency) }}{{ fmt(a.net) }}</text>
        </view>
      </view>
    </view>

    <view style="height: 40rpx"></view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiDividends } from '@/api'
import { marketMap, currencyMap } from '@/utils/constants'

const list = ref([])
const total = ref(0)
const status = ref('')
const year = ref('')
const openId = ref(null)

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

const netSum = computed(() =>
  list.value.filter(d => d.status === 'confirmed').reduce((s, d) => s + (d.net_cny || 0), 0))
const pendSum = computed(() =>
  list.value.filter(d => d.status === 'pending').reduce((s, d) => s + (d.net_cny || d.gross_amount || 0), 0))

async function load() {
  const params = { page: 1, page_size: 100, expand: 'allocations' }
  if (status.value) params.status = status.value
  if (year.value) params.year = year.value
  const data = await apiDividends(params)
  list.value = data.items
  total.value = data.total
}

function setStatus(s) { status.value = s; load() }
function toggleYear() {
  year.value = year.value ? '' : String(new Date().getFullYear())
  load()
}
function toggle(id) { openId.value = openId.value === id ? null : id }

onShow(load)
</script>

<style scoped>
.chips { white-space: nowrap; padding: 20rpx 24rpx 0; }
.chip {
  display: inline-block; padding: 10rpx 30rpx; margin-right: 16rpx;
  background: #fff; color: #64748b; border-radius: 32rpx; font-size: 26rpx;
}
.chip.on { background: #1668dc; color: #fff; }
.sum-bar {
  display: flex; gap: 30rpx; padding: 20rpx 32rpx 0;
  font-size: 24rpx; color: #64748b;
}
.d-card { padding: 24rpx 28rpx; }
.d-head { display: flex; justify-content: space-between; align-items: center; }
.d-name { font-size: 30rpx; font-weight: 600; margin-left: 10rpx; }
.d-amt { text-align: right; font-size: 30rpx; font-weight: 600; }
.d-line { display: flex; gap: 22rpx; flex-wrap: wrap; align-items: center; margin-top: 14rpx; font-size: 24rpx; color: #64748b; }
.alloc { margin-top: 18rpx; background: #f8fafc; border-radius: 12rpx; padding: 18rpx 20rpx; }
.alloc-title { font-size: 24rpx; font-weight: 600; color: #475569; margin-bottom: 10rpx; }
.alloc-row { display: flex; justify-content: space-between; font-size: 24rpx; color: #64748b; padding: 6rpx 0; }
</style>
