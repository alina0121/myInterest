<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="持仓管理" subtitle="点击行查看买入批次与分红归属" /><!-- #endif -->

    <!-- 加载中 -->
    <view v-if="loading && !list.length" class="loading-wrap">
      <text class="loading-text">加载中...</text>
    </view>

    <!-- 空态 -->
    <view v-else-if="!list.length" class="empty">
      <text class="empty-text">暂无持仓，点击下方按钮添加第一笔</text>
    </view>

    <!-- 持仓列表 -->
    <view v-else class="card list-card">
      <view
        v-for="(h, idx) in list"
        :key="h.id"
        :class="['list-item', idx === list.length - 1 ? 'no-border' : '']"
        @click="goDetail(h.id)"
      >
        <view class="item-top">
          <view class="item-name-row">
            <text class="item-name">{{ h.name }}</text>
            <text :class="['item-badge', badgeClass(h.market)]">{{ marketMap[h.market]?.label }}</text>
          </view>
          <view class="item-price">
            <text class="price-num">{{ h.current_price ? fmt(h.current_price) : '—' }}</text>
            <text class="price-cur">{{ h.currency }}</text>
          </view>
        </view>

        <view class="item-metrics">
          <view class="metric-cell">
            <view class="m-label">持股</view>
            <view class="m-value">{{ h.shares_now }}股</view>
          </view>
          <view class="metric-cell">
            <view class="m-label">成本</view>
            <view class="m-value">{{ moneyWith(h.currency, h.cost_total) }}</view>
          </view>
          <view class="metric-cell">
            <view class="m-label">市值</view>
            <view class="m-value">{{ h.current_price ? moneyWith(h.currency, h.current_price * h.shares_now) : '—' }}</view>
          </view>
          <view class="metric-cell">
            <view class="m-label">盈亏</view>
            <view class="m-value" :class="pnlClass(h)">
              {{ h.current_price ? ((h.current_price * h.shares_now - h.cost_total) >= 0 ? '+' : '') + fmt(h.current_price * h.shares_now - h.cost_total) : '—' }}
            </view>
          </view>
        </view>

        <view class="item-bottom">
          <view class="div-info">
            <text class="div-label">累计分红</text>
            <text class="div-amount">¥{{ fmt(h.total_dividend_cny || h.total_dividend || 0) }}</text>
          </view>
          <view class="yoc-info" v-if="h.yoc_ttm">
            <text class="yoc-label">成本息率</text>
            <text class="yoc-value">{{ (h.yoc_ttm * 100).toFixed(2) }}%</text>
          </view>
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
import { onShow, onPullDownRefresh } from '@dcloudio/uni-app'
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
    // #ifdef MP-WEIXIN || MP-ALIPAY
    uni.stopPullDownRefresh()
    // #endif
  }
}

function pnlClass(h) {
  if (!h.current_price) return ''
  const pnl = h.current_price * h.shares_now - h.cost_total
  return pnl >= 0 ? 'positive' : 'negative'
}

function goAdd() { uni.navigateTo({ url: '/pages/holdings/add' }) }
function goDetail(id) { uni.navigateTo({ url: '/pages/holdings/detail?id=' + id }) }

onShow(load)
onPullDownRefresh(load)
</script>

<style scoped>
.page { padding: 24rpx; }

.loading-wrap { padding: 100rpx 0; text-align: center; }
.loading-text { font-size: 26rpx; color: #94a3b8; }

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
  padding: 28rpx; border-bottom: 1rpx solid #f1f5f9;
}
.list-item.no-border { border-bottom: none; }
.list-item:active { background: #f8fafc; }

/* 顶部：名称 + 价格 */
.item-top { display: flex; justify-content: space-between; align-items: center; }
.item-name-row { display: flex; align-items: center; gap: 12rpx; }
.item-name {
  font-size: 30rpx; font-weight: 600; color: #1e293b;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300rpx;
}
.item-badge {
  display: inline-block; font-size: 18rpx; line-height: 1;
  padding: 6rpx 12rpx; border-radius: 9999rpx; font-weight: 500;
}
.item-price { text-align: right; }
.price-num { font-size: 30rpx; font-weight: 700; color: #1e293b; }
.price-cur { font-size: 20rpx; color: #94a3b8; margin-left: 6rpx; }

/* 指标区 */
.item-metrics {
  display: flex; margin-top: 20rpx; padding: 20rpx 0;
  border-top: 1rpx solid #f8fafc; border-bottom: 1rpx solid #f8fafc;
}
.metric-cell { flex: 1; text-align: center; }
.m-label { font-size: 22rpx; color: #94a3b8; margin-bottom: 6rpx; }
.m-value { font-size: 26rpx; font-weight: 600; color: #334155; }
.m-value.positive { color: #059669; }
.m-value.negative { color: #dc2626; }

/* 底部：累计分红 + 息率 */
.item-bottom { display: flex; justify-content: space-between; align-items: center; margin-top: 16rpx; }
.div-info { display: flex; align-items: baseline; gap: 10rpx; }
.div-label { font-size: 22rpx; color: #94a3b8; }
.div-amount { font-size: 28rpx; font-weight: 700; color: #059669; }
.yoc-info { display: flex; align-items: baseline; gap: 8rpx; }
.yoc-label { font-size: 22rpx; color: #94a3b8; }
.yoc-value { font-size: 26rpx; font-weight: 600; color: #1e3a8a; }

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

/* 市场徽章配色 */
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
