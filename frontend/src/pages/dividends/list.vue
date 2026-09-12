<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="分红记录" subtitle="点击行展开批次归属明细" /><!-- #endif -->
    <!-- 状态筛选 -->
    <scroll-view scroll-x class="chips" :show-scrollbar="false">
      <view :class="['chip', status === '' ? 'on' : '']" @click="setStatus('')">全部</view>
      <view :class="['chip', status === 'confirmed' ? 'on' : '']" @click="setStatus('confirmed')">已到账</view>
      <view :class="['chip', status === 'pending' ? 'on' : '']" @click="setStatus('pending')">预告</view>
      <view :class="['chip', year ? 'on' : '']" @click="toggleYear">{{ year || new Date().getFullYear() }}年</view>
    </scroll-view>

    <!-- 市场筛选 -->
    <scroll-view scroll-x class="chips chips-market" :show-scrollbar="false">
      <view :class="['chip', market === '' ? 'on' : '']" @click="setMarket('')">全部</view>
      <view v-for="m in MARKETS" :key="m.value"
            :class="['chip', market === m.value ? 'on' : '']"
            @click="setMarket(m.value)">{{ m.label }}</view>
    </scroll-view>

    <!-- 汇总条 -->
    <view class="sum-bar">
      <text>共 {{ total }} 笔</text>
      <text class="text-emerald">已到账 ¥{{ fmt(netSum) }}</text>
      <text class="text-amber" v-if="pendSum > 0">预告 ¥{{ fmt(pendSum) }}</text>
    </view>

    <view v-if="!list.length && !loading" class="empty card">暂无分红记录</view>

    <view v-for="d in list" :key="d.id" class="card d-card" @click="toggle(d.id)">
      <view class="d-head">
        <view class="d-name-wrap">
          <text :class="['tag', badgeClass(d.market)]">{{ marketMap[d.market]?.label }}</text>
          <text class="d-name">{{ d.holding_name }}</text>
        </view>
        <view class="d-amt">
          <view :class="d.status === 'confirmed' ? 'text-emerald' : 'text-amber'">
            {{ sym(d.currency) }}{{ fmt(d.net_amount) }}
          </view>
          <view class="text-muted" style="font-size:22rpx">{{ d.pay_date }}</view>
        </view>
      </view>
      <view class="d-line">
        <text>每股 {{ sym(d.currency) }}{{ fmt(d.dps) }}</text>
        <text>登记日持仓 {{ d.shares }} 股</text>
        <text>税前 {{ sym(d.currency) }}{{ fmt(d.gross_amount) }}</text>
        <text v-if="d.tax > 0" class="text-amber">税 {{ sym(d.currency) }}{{ fmt(d.tax) }}</text>
        <text :class="['tag', d.status === 'confirmed' ? 'badge-confirmed' : 'badge-pending']">
          {{ d.status === 'confirmed' ? '已到账' : '预告' }}
        </text>
      </view>
      <!-- 批次归属 -->
      <view v-if="openId === d.id" class="alloc">
        <view class="alloc-title">批次归属明细（共 {{ d.allocations?.length || 0 }} 个批次参与）</view>
        <view v-for="(a, i) in d.allocations" :key="i" class="alloc-row">
          <text>{{ a.lot_date }} 批次</text>
          <text>{{ a.shares }} 股 · 税 {{ sym(d.currency) }}{{ fmt(a.tax) }}</text>
          <text class="text-emerald">{{ sym(d.currency) }}{{ fmt(a.net) }}</text>
        </view>
      </view>
    </view>

    <!-- 加载更多 -->
    <view v-if="hasMore" class="load-more" @click="loadMore">
      <text v-if="loading" class="text-muted">加载中...</text>
      <text v-else>加载更多</text>
    </view>
    <view v-else-if="list.length" class="load-more">
      <text class="text-muted">没有更多了</text>
    </view>

    <view style="height: 40rpx"></view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow, onReachBottom, onPullDownRefresh } from '@dcloudio/uni-app'
import { apiDividends } from '@/api'
import { MARKETS, marketMap, currencyMap, badgeClass } from '@/utils/constants'
import { userStore } from '@/store/user'
import WebLayout from '@/components/WebLayout.vue'

const list = ref([])
const total = ref(0)
const status = ref('')
const year = ref('')
const market = ref('')
const openId = ref(null)
const page = ref(1)
const hasMore = ref(false)
const loading = ref(false)
const netSum = ref(0)
const pendSum = ref(0)

/** v8：账户跟随 + 显示币种参数（从 store 读） */
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

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

async function load(reset = true) {
  if (loading.value) return
  if (reset) {
    page.value = 1
    list.value = []
    hasMore.value = true
  }
  loading.value = true
  try {
    const params = { page: page.value, page_size: 20, expand: 'allocations' }
    if (status.value) params.status = status.value
    if (year.value) params.year = year.value
    if (market.value) params.market = market.value
    // v8：账户跟随 + 币种过滤
    Object.assign(params, filterParams())
    const data = await apiDividends(params)
    list.value = reset ? data.items : [...list.value, ...data.items]
    total.value = data.total
    hasMore.value = list.value.length < data.total
  } finally {
    loading.value = false
  }
}

async function loadSummary() {
  const params = { page: 1, page_size: 999 }
  if (status.value) params.status = status.value
  if (year.value) params.year = year.value
  if (market.value) params.market = market.value
  // v8：账户跟随 + 币种过滤
  Object.assign(params, filterParams())
  const data = await apiDividends(params)
  netSum.value = data.items
    .filter(d => d.status === 'confirmed')
    .reduce((s, d) => s + (d.net_cny || 0), 0)
  pendSum.value = data.items
    .filter(d => d.status === 'pending')
    .reduce((s, d) => s + (d.net_cny || d.gross_amount || 0), 0)
}

async function refresh() {
  await Promise.all([load(true), loadSummary()])
  // #ifdef MP-WEIXIN || MP-ALIPAY
  uni.stopPullDownRefresh()
  // #endif
}

function setStatus(s) { status.value = s; refresh() }
function setMarket(m) { market.value = m; refresh() }
function toggleYear() {
  year.value = year.value ? '' : String(new Date().getFullYear())
  refresh()
}
function toggle(id) { openId.value = openId.value === id ? null : id }

async function loadMore() {
  if (!hasMore.value || loading.value) return
  page.value++
  await load(false)
}

onShow(refresh)
onReachBottom(loadMore)
onPullDownRefresh(refresh)
</script>

<style scoped>
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
.d-head { display: flex; justify-content: space-between; align-items: center; }
.d-name-wrap { display: flex; align-items: center; }
.d-name { font-size: 30rpx; font-weight: 600; margin-left: 10rpx; }
.d-amt { text-align: right; font-size: 30rpx; font-weight: 600; }
.d-line { display: flex; gap: 22rpx; flex-wrap: wrap; align-items: center; margin-top: 14rpx; font-size: 24rpx; color: #64748b; }
.alloc { margin-top: 18rpx; background: #f8fafc; border-radius: 12rpx; padding: 18rpx 20rpx; }
.alloc-title { font-size: 24rpx; font-weight: 600; color: #475569; margin-bottom: 10rpx; }
.alloc-row { display: flex; justify-content: space-between; font-size: 24rpx; color: #64748b; padding: 6rpx 0; }
.load-more { text-align: center; padding: 30rpx 0; font-size: 26rpx; color: #1e3a8a; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; }
  .d-card { display: inline-block; width: calc(50% - 24rpx); margin: 12rpx; vertical-align: top; box-sizing: border-box; }
}
/* #endif */
</style>
