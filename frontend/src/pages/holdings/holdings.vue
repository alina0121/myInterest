<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="持仓管理" subtitle="点击行查看买入批次与分红归属" /><!-- #endif -->

    <!-- 空态 -->
    <view v-if="!list.length && !loading" class="empty">
      <text class="empty-text">暂无持仓，点击下方按钮添加第一笔</text>
    </view>

    <!-- 持仓列表（单卡片 + divide-y） -->
    <view v-else class="card list-card">
      <view
        v-for="(h, idx) in list"
        :key="h.id"
        :class="['list-item', idx === list.length - 1 ? 'no-border' : '']"
        @click="goDetail(h.id)"
      >
        <view class="item-left">
          <view class="item-name-row">
            <text class="item-name">{{ h.name }}</text>
            <text :class="['item-badge', badgeClass(h.market)]">{{ marketMap[h.market]?.label }}</text>
          </view>
          <view class="item-sub">
            <text>{{ h.shares_now }} 股 · 成本 {{ moneyWith(h.currency, (Number(h.shares_now) || 0) * (Number(h.avg_cost) || 0)) }}</text>
          </view>
        </view>
        <view class="item-right">
          <text class="item-div">¥{{ fmt(h.total_dividend_cny || h.total_dividend || 0) }}</text>
          <text class="item-div-label">累计分红</text>
        </view>
      </view>
    </view>

    <!-- 添加按钮 -->
    <view class="add-btn-wrap">
      <button class="add-btn" @click="goAdd">+ 添加持仓</button>
    </view>

    <view style="height: 140rpx"></view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiHoldings } from '@/api'
import { marketMap, badgeClass, fmt, moneyWith } from '@/utils/constants'
import WebLayout from '@/components/WebLayout.vue'

const list = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const data = await apiHoldings()
    list.value = data.items || []
  } finally {
    loading.value = false
  }
}

function goAdd() { uni.navigateTo({ url: '/pages/holdings/add' }) }
function goDetail(id) { uni.navigateTo({ url: '/pages/holdings/detail?id=' + id }) }

onShow(load)
</script>

<style scoped>
.page { padding: 24rpx; }

/* 空态 */
.empty {
  background: #fff; border-radius: 24rpx; padding: 80rpx 40rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06); text-align: center;
}
.empty-text { font-size: 26rpx; color: #94a3b8; }

/* 列表卡片 */
.card {
  background: #fff; border-radius: 24rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}
.list-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 28rpx 28rpx; border-bottom: 1rpx solid #f1f5f9;
}
.list-item.no-border { border-bottom: none; }
.list-item:active { background: #f8fafc; }

.item-left { flex: 1; min-width: 0; }
.item-name-row { display: flex; align-items: center; gap: 12rpx; }
.item-name {
  font-size: 28rpx; font-weight: 500; color: #1e293b;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 360rpx;
}
.item-badge {
  display: inline-block; font-size: 18rpx; line-height: 1;
  padding: 6rpx 12rpx; border-radius: 9999rpx; font-weight: 500;
}
.item-sub { margin-top: 10rpx; font-size: 20rpx; color: #94a3b8; }

.item-right { text-align: right; flex-shrink: 0; margin-left: 16rpx; }
.item-div { display: block; font-size: 24rpx; font-weight: 600; color: #059669; }
.item-div-label { display: block; margin-top: 8rpx; font-size: 20rpx; color: #94a3b8; }

/* 添加按钮 */
.add-btn-wrap { margin-top: 32rpx; padding: 0 8rpx; }
.add-btn {
  width: 100%; height: 88rpx; line-height: 88rpx;
  background: #1e3a8a; color: #fff; font-size: 30rpx; font-weight: 500;
  border-radius: 24rpx; border: none; padding: 0;
  box-shadow: 0 4rpx 12rpx rgba(30, 58, 138, 0.18);
}
.add-btn::after { border: none; }
.add-btn:active { opacity: 0.9; }

/* 市场徽章配色（浅底深字） */
.tag-a { background: #fef2f2; color: #dc2626; }
.tag-us { background: #eff6ff; color: #2563eb; }
.tag-hk { background: #ecfdf5; color: #059669; }
.tag-fund { background: #fffbeb; color: #d97706; }
.tag-bond { background: #f5f3ff; color: #7c3aed; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
