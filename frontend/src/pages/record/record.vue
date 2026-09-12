<template>
  <view class="page">
    <!-- #ifdef H5 -->
    <WebLayout title="记分红" subtitle="快速记录一笔到账分红" />
    <!-- #endif -->

    <!-- 记录入口卡 -->
    <view class="card record-card">
      <view class="round-btn">+</view>
      <view class="rc-title">记录一笔分红</view>
      <view class="rc-sub">选择持仓 → 填写派息日与金额 → 自动计入统计</view>
      <button class="btn-primary rc-btn" @click="goAdd">开始记录</button>
    </view>

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

function goAdd() { uni.navigateTo({ url: '/pages/dividends/add' }) }
</script>

<style scoped>
.page { padding-bottom: 30rpx; }

/* 记录入口卡 */
.record-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 56rpx 40rpx 40rpx;
}
.round-btn {
  width: 128rpx;
  height: 128rpx;
  border-radius: 50%;
  background: #1e3a8a;
  color: #fff;
  font-size: 48rpx;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.rc-title {
  font-size: 30rpx;
  font-weight: 600;
  color: #1e293b;
  margin-top: 24rpx;
}
.rc-sub {
  font-size: 24rpx;
  color: #94a3b8;
  margin-top: 10rpx;
  line-height: 1.5;
}
.rc-btn {
  margin-top: 32rpx;
  width: 100%;
}

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
  .record-card { padding: 64rpx 48rpx 48rpx; }
  .rc-btn { max-width: 420rpx; margin-left: auto; margin-right: auto; }
}
/* #endif */
</style>
