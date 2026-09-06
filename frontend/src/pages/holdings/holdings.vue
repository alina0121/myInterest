<template>
  <view class="page">
    <!-- 搜索 + 市场筛选 -->
    <view class="filter-bar">
      <input class="search" v-model="keyword" placeholder="搜索代码 / 名称" @confirm="load" />
    </view>
    <scroll-view scroll-x class="chips" :show-scrollbar="false">
      <view :class="['chip', market === '' ? 'on' : '']" @click="setMarket('')">全部</view>
      <view v-for="m in MARKETS" :key="m.value"
            :class="['chip', market === m.value ? 'on' : '']"
            @click="setMarket(m.value)">{{ m.label }}</view>
    </scroll-view>

    <view v-if="!list.length && !loading" class="empty card">
      暂无持仓，点右下角 ＋ 添加第一笔
    </view>

    <view v-for="h in list" :key="h.id" class="card h-card" @click="goDetail(h.id)">
      <view class="h-head">
        <view class="h-name">
          <text class="tag" :style="{ background: marketMap[h.market]?.color }">{{ marketMap[h.market]?.label }}</text>
          <text class="name">{{ h.name }}</text>
          <text class="code">{{ h.code }}</text>
        </view>
        <view class="h-yoc">
          <text class="yoc-label">成本股息率</text>
          <text class="yoc-val">{{ (h.yoc_ttm * 100).toFixed(2) }}%</text>
        </view>
      </view>
      <view class="h-grid">
        <view class="h-cell">
          <view class="cell-label">持仓数量</view>
          <view class="cell-val">{{ h.shares_now }}</view>
        </view>
        <view class="h-cell">
          <view class="cell-label">平均成本</view>
          <view class="cell-val">{{ sym(h.currency) }}{{ fmt(h.avg_cost) }}</view>
        </view>
        <view class="h-cell">
          <view class="cell-label">批次数</view>
          <view class="cell-val">{{ h.lot_count }}</view>
        </view>
        <view class="h-cell">
          <view class="cell-label">今年分红</view>
          <view class="cell-val text-income">¥{{ fmt(h.year_dividend) }}</view>
        </view>
      </view>
    </view>

    <view style="height: 140rpx"></view>

    <!-- 浮动添加按钮 -->
    <view class="fab" @click="goAdd">＋</view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiHoldings } from '@/api'
import { MARKETS, marketMap, currencyMap } from '@/utils/constants'

const list = ref([])
const keyword = ref('')
const market = ref('')
const loading = ref(false)

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

async function load() {
  loading.value = true
  try {
    const params = {}
    if (market.value) params.market = market.value
    if (keyword.value) params.keyword = keyword.value
    const data = await apiHoldings(params)
    list.value = data.items
  } finally {
    loading.value = false
  }
}

function setMarket(m) { market.value = m; load() }
function goAdd() { uni.navigateTo({ url: '/pages/holdings/add' }) }
function goDetail(id) { uni.navigateTo({ url: '/pages/holdings/detail?id=' + id }) }

onShow(load)
</script>

<style scoped>
.filter-bar { padding: 20rpx 24rpx 0; }
.search {
  background: #fff; border-radius: 40rpx; height: 72rpx; padding: 0 30rpx;
  font-size: 26rpx; box-shadow: 0 4rpx 12rpx rgba(22,104,220,0.05);
}
.chips { white-space: nowrap; padding: 20rpx 24rpx 0; }
.chip {
  display: inline-block; padding: 10rpx 30rpx; margin-right: 16rpx;
  background: #fff; color: #64748b; border-radius: 32rpx; font-size: 26rpx;
}
.chip.on { background: #1668dc; color: #fff; }
.h-card { padding: 26rpx 28rpx; }
.h-head { display: flex; justify-content: space-between; align-items: flex-start; }
.h-name { display: flex; align-items: center; flex-wrap: wrap; gap: 10rpx; }
.name { font-size: 32rpx; font-weight: 600; }
.code { font-size: 24rpx; color: #94a3b8; }
.h-yoc { text-align: right; }
.yoc-label { display: block; font-size: 20rpx; color: #94a3b8; }
.yoc-val { font-size: 32rpx; font-weight: 700; color: #16a34a; }
.h-grid { display: flex; margin-top: 24rpx; }
.h-cell { flex: 1; }
.cell-label { font-size: 22rpx; color: #94a3b8; }
.cell-val { font-size: 28rpx; font-weight: 600; margin-top: 8rpx; }
.fab {
  position: fixed; right: 40rpx; bottom: 140rpx; width: 100rpx; height: 100rpx;
  background: linear-gradient(135deg, #1668dc, #3b82f6); color: #fff;
  border-radius: 50%; text-align: center; line-height: 96rpx; font-size: 60rpx;
  box-shadow: 0 8rpx 24rpx rgba(22,104,220,0.4);
}
</style>
