<template>
  <view class="page">
    <!-- #ifdef H5 -->
    <WebLayout title="记分红" subtitle="查看即将到账的分红预告" />
    <!-- #endif -->

    <!-- 待确认预告 -->
    <view class="section-title">待确认预告</view>
    <view class="card list-card">
      <view v-if="!upcoming.length" class="empty">暂无待确认的分红预告</view>
      <view v-for="(u, i) in upcoming" :key="u.id || i" class="row">
        <view class="row-left">{{ u.name }} · 约{{ sym(u.currency) }}{{ fmt(u.est_net) }}</view>
        <view class="row-right text-amber">{{ fmtDate(u.pay_date) }} 到账</view>
      </view>
    </view>

    <view style="height: 40rpx"></view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiUpcoming } from '@/api'
import { currencyMap } from '@/utils/constants'
// #ifdef H5
import WebLayout from '@/components/WebLayout.vue'
// #endif

const upcoming = ref([])

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }
function fmtDate(d) {
  if (!d) return ''
  return String(d).slice(5) // YYYY-MM-DD → MM-DD
}

async function load() {
  try {
    const res = await apiUpcoming()
    upcoming.value = res.items || res || []
  } catch (e) { /* toast 已统一处理 */ }
}
onShow(load)
</script>

<style scoped>
.page { padding-bottom: 30rpx; }

/* 待确认预告列表 */
.list-card {
  padding: 8rpx 28rpx;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 26rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
}
.row:last-child { border-bottom: none; }
.row-left {
  font-size: 26rpx;
  color: #1e293b;
  flex: 1;
  min-width: 0;
}
.row-right {
  font-size: 24rpx;
  flex-shrink: 0;
  margin-left: 16rpx;
}

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
