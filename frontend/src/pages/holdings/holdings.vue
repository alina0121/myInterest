<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="持仓 · 分红预告" subtitle="持仓批次与即将到账的分红预案" /><!-- #endif -->

    <!-- 顶部功能切换 -->
    <view class="segment">
      <view :class="['seg-item', tab === 'holdings' ? 'on' : '']" @click="tab = 'holdings'">
        <text class="seg-emoji">💼</text><text class="seg-text">持仓</text>
      </view>
      <view :class="['seg-item', tab === 'record' ? 'on' : '']" @click="tab = 'record'">
        <text class="seg-emoji">🔔</text><text class="seg-text">分红预告</text>
      </view>
    </view>

    <!-- ===== 持仓 ===== -->
    <block v-if="tab === 'holdings'">
    <!-- 加载中 -->
    <view v-if="loading && !list.length" class="loading-wrap">
      <text class="loading-text">加载中...</text>
    </view>

    <!-- 空态 -->
    <view v-else-if="!list.length" class="empty">
      <text class="empty-text">暂无持仓，点击下方按钮添加第一笔</text>
    </view>

    <!-- 持仓列表：每只独立卡片，信息分三层 -->
    <view v-else class="h-list">
      <view v-for="h in list" :key="h.id" class="h-card" @click="goDetail(h.id)">
        <!-- 层1：名称/市场 + 市值/盈亏 -->
        <view class="hc-top">
          <view class="hc-id">
            <view class="hc-name-row">
              <text class="hc-name">{{ h.name }}</text>
              <text :class="['item-badge', badgeClass(h.market)]">{{ marketMap[h.market]?.label }}</text>
            </view>
            <text v-if="h.account" class="hc-account">{{ h.account }}</text>
          </view>
          <view class="hc-right">
            <view class="hc-mv">{{ h.current_price ? moneyWith(h.currency, h.current_price * h.shares_now) : '—' }}</view>
            <view v-if="h.current_price" class="hc-pnl" :class="pnlClass(h)">
              {{ pnlSign(h) }}{{ fmt(Math.abs(h.current_price * h.shares_now - h.cost_total)) }}<text v-if="h.cost_total">（{{ pnlPct(h) }}%）</text>
            </view>
            <view v-else class="hc-pnl hc-pnl-none">待更新现价</view>
          </view>
        </view>

        <!-- 层2：三列指标 -->
        <view class="hc-metrics">
          <view class="hc-cell">
            <view class="hc-label">持股</view>
            <view class="hc-value">{{ h.shares_now }}股</view>
          </view>
          <view class="hc-cell">
            <view class="hc-label">成本</view>
            <view class="hc-value">{{ moneyWith(h.currency, h.cost_total) }}</view>
          </view>
          <view class="hc-cell">
            <view class="hc-label">现价</view>
            <view class="hc-value">{{ h.current_price ? fmt(h.current_price) : '—' }}</view>
          </view>
        </view>

        <!-- 层3：分红底条 -->
        <view class="hc-foot">
          <view class="hc-div">
            <text class="hc-div-icon">🪙</text>
            <text class="hc-div-label">累计分红</text>
            <text class="hc-div-amt">{{ moneyWith(h.currency, h.total_dividend || 0) }}</text>
          </view>
          <view class="hc-yoc" v-if="h.yoc_ttm">
            <text class="hc-yoc-label">成本息率</text>
            <text class="hc-yoc-val">{{ (h.yoc_ttm * 100).toFixed(2) }}%</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 添加按钮 -->
    <view class="add-btn-wrap">
      <button class="add-btn" @click="goAdd">+ 添加持仓</button>
    </view>
    </block>

    <!-- ===== 分红预告 ===== -->
    <block v-else>
      <!-- 本月合计 -->
      <view v-if="upcoming.length" class="month-bar">
        <view class="mb-left">
          <text class="mb-label">本月预计到账</text>
          <text class="mb-amount">≈ ¥{{ fmtMoney(monthTotal) }}</text>
        </view>
        <text class="mb-count">共 {{ upcoming.length }} 笔待到账</text>
      </view>

      <view v-if="!upcoming.length" class="empty">
        <text class="empty-text">暂无即将到账的分红预告</text>
        <text class="empty-sub">有已发布的分红预案后会自动出现在这里</text>
      </view>

      <view v-for="(u, i) in upcoming" :key="u.id || i" class="u-card">
        <!-- 行1：名称/徽章 + 预估税后金额 -->
        <view class="uc-top">
          <view class="uc-name-row">
            <text class="uc-name">{{ u.name }}</text>
            <text :class="['item-badge', badgeClass(u.market)]">{{ marketMap[u.market]?.label }}</text>
          </view>
          <view class="uc-amt-box">
            <view class="uc-amt">{{ cSym(u.currency) }}{{ fmtMoney(u.est_net) }}</view>
            <view class="uc-amt-label">预计税后</view>
          </view>
        </view>

        <!-- 行2：三个关键日期 -->
        <view class="uc-dates">
          <view class="uc-date">
            <view class="ucd-label">除权日</view>
            <view class="ucd-value">{{ fmtDate(u.ex_date) || '—' }}</view>
          </view>
          <view class="uc-date">
            <view class="ucd-label">登记日</view>
            <view class="ucd-value">{{ fmtDate(u.record_date) || '—' }}</view>
          </view>
          <view class="uc-date">
            <view class="ucd-label">到账日</view>
            <view class="ucd-value ucd-pay">{{ fmtDate(u.pay_date) || '待定' }}</view>
          </view>
        </view>

        <!-- 行3：底条 持股明细 + 倒计时 -->
        <view class="uc-foot">
          <view class="uc-detail">
            持 {{ u.my_shares }}股 · 每股{{ cSym(u.currency) }}{{ fmtMoney(u.dps) }}
            <text v-if="u.est_gross && u.est_net !== u.est_gross" class="uc-tax">（税前 {{ cSym(u.currency) }}{{ fmtMoney(u.est_gross) }}）</text>
          </view>
          <view :class="['uc-count', u.days_to_pay !== null && u.days_to_pay <= 7 ? 'hot' : '']" v-if="u.days_to_pay !== null && u.days_to_pay !== undefined">
            {{ payCountdown(u) }}
          </view>
        </view>
      </view>
    </block>

    <view style="height: 140rpx"></view>
    <!-- #ifdef H5 --><CustomTab current="/pages/holdings/holdings" /><!-- #endif -->
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { onShow, onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import { apiHoldings, apiUpcoming } from '@/api'
import { marketMap, badgeClass, fmt, moneyWith, currencyMap } from '@/utils/constants'
import { userStore } from '@/store/user'
import WebLayout from '@/components/WebLayout.vue'
import CustomTab from '@/components/CustomTab.vue'

const tab = ref('holdings')
const list = ref([])
const loading = ref(false)
const upcoming = ref([])
const monthTotal = ref(0)

// 支持 ?tab=record 直达分红预告视图
onLoad((query) => {
  if (query && query.tab === 'record') tab.value = 'record'
})

async function load() {
  loading.value = true
  try {
    // v8：传 account 参数给后端做服务端过滤
    const params = {}
    if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
      params.account = userStore.currentAccount
    }
    const data = await apiHoldings(params)
    list.value = data.items || []
  } finally {
    loading.value = false
    // #ifdef MP-WEIXIN || MP-ALIPAY
    uni.stopPullDownRefresh()
    // #endif
  }
  try {
    const res = await apiUpcoming()
    upcoming.value = res.items || res || []
    monthTotal.value = res.month_total_cny || 0
  } catch (e) { /* toast 已统一处理 */ }
}

function fmtMoney(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function cSym(c) { return currencyMap[c]?.symbol || '' }
function fmtDate(d) {
  if (!d) return ''
  return String(d).slice(5) // YYYY-MM-DD → MM-DD
}
function payCountdown(u) {
  const d = u.days_to_pay
  if (d === 0) return '今天到账'
  if (d === 1) return '明天到账'
  if (d <= 7) return d + ' 天后到账'
  if (d <= 14) return '两周内到账'
  return '约 ' + Math.ceil(d / 30) + ' 个月后到账'
}

function pnlClass(h) {
  if (!h.current_price) return ''
  const pnl = h.current_price * h.shares_now - h.cost_total
  return pnl >= 0 ? 'positive' : 'negative'
}
function pnlSign(h) {
  return h.current_price * h.shares_now - h.cost_total >= 0 ? '+' : '-'
}
function pnlPct(h) {
  if (!h.cost_total) return ''
  const pct = (h.current_price * h.shares_now - h.cost_total) / h.cost_total * 100
  return (pct >= 0 ? '+' : '') + pct.toFixed(2)
}

function goAdd() { uni.navigateTo({ url: '/pages/holdings/add' }) }
function goDetail(id) { uni.navigateTo({ url: '/pages/holdings/detail?id=' + id }) }

onShow(load)
onPullDownRefresh(load)
</script>

<style scoped>
.page { padding: 24rpx; }

/* 顶部功能切换 segment */
.segment {
  display: flex; background: #eef2f7; border-radius: 9999rpx;
  padding: 6rpx; margin-bottom: 24rpx;
}
.seg-item {
  flex: 1; display: flex; align-items: center; justify-content: center;
  gap: 8rpx; height: 68rpx; border-radius: 9999rpx;
  color: #64748b; font-size: 28rpx;
}
.seg-item.on {
  background: #fff; color: #1e3a8a; font-weight: 600;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.08);
}
.seg-emoji { font-size: 30rpx; line-height: 1; }

/* 分红预告：本月合计条 */
.month-bar {
  display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(135deg, #1e3a8a, #2d4ea8);
  border-radius: 24rpx; padding: 28rpx 32rpx; margin-bottom: 24rpx;
  box-shadow: 0 6rpx 16rpx rgba(30, 58, 138, 0.25);
}
.mb-left { display: flex; flex-direction: column; gap: 8rpx; }
.mb-label { font-size: 22rpx; color: rgba(255, 255, 255, 0.75); }
.mb-amount { font-size: 40rpx; font-weight: 700; color: #fff; }
.mb-count { font-size: 22rpx; color: rgba(255, 255, 255, 0.75); }

/* 分红预告：单条卡片（与持仓卡片同风格） */
.u-card {
  background: #fff; border-radius: 28rpx; padding: 32rpx;
  margin-bottom: 24rpx; box-shadow: 0 2rpx 12rpx rgba(15, 23, 42, 0.05);
}
.uc-top { display: flex; justify-content: space-between; align-items: flex-start; }
.uc-name-row { display: flex; align-items: center; gap: 12rpx; flex: 1; min-width: 0; }
.uc-name {
  font-size: 30rpx; font-weight: 700; color: #0f172a;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.uc-amt-box { text-align: right; margin-left: 24rpx; flex-shrink: 0; }
.uc-amt { font-size: 34rpx; font-weight: 700; color: #059669; }
.uc-amt-label { font-size: 20rpx; color: #94a3b8; margin-top: 6rpx; }

/* 三列关键日期 */
.uc-dates {
  display: flex; margin-top: 28rpx; padding-top: 24rpx;
  border-top: 1rpx solid #f1f5f9;
}
.uc-date { flex: 1; }
.ucd-label { font-size: 22rpx; color: #94a3b8; margin-bottom: 10rpx; }
.ucd-value { font-size: 26rpx; font-weight: 600; color: #334155; }
.ucd-value.ucd-pay { color: #d97706; }

/* 底条：持股明细 + 倒计时 */
.uc-foot {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 24rpx; padding: 18rpx 24rpx;
  background: #f6f8fb; border-radius: 16rpx;
}
.uc-detail { font-size: 22rpx; color: #64748b; flex: 1; min-width: 0; }
.uc-tax { color: #94a3b8; }
.uc-count {
  font-size: 22rpx; color: #64748b; flex-shrink: 0; margin-left: 16rpx;
  font-weight: 600;
}
.uc-count.hot { color: #d97706; }

/* v8：账户切换条 */
.chips {
  display: flex; white-space: nowrap; padding: 8rpx 0 16rpx;
}
.chips-account { margin-bottom: 8rpx; }
.chips-currency { margin-bottom: 20rpx; }
.chip {
  display: inline-flex; align-items: center; gap: 6rpx;
  padding: 10rpx 22rpx; margin-right: 12rpx;
  border-radius: 9999rpx; font-size: 24rpx; color: #64748b;
  background: #fff; border: 1rpx solid #e2e8f0;
  flex-shrink: 0;
}
.chip.on {
  background: #1e3a8a; color: #fff; border-color: #1e3a8a;
}
.chip.archived { opacity: 0.5; }
.chip-dot {
  width: 12rpx; height: 12rpx; border-radius: 50%;
  display: inline-block;
}
.chip-count {
  font-size: 20rpx; background: rgba(0,0,0,0.08); color: inherit;
  padding: 2rpx 8rpx; border-radius: 9999rpx; margin-left: 4rpx;
}
.chip.on .chip-count { background: rgba(255,255,255,0.2); }

/* 币种筛选 chip */
.c-chip { gap: 4rpx; }
.c-symbol { font-weight: 600; }

.loading-wrap { padding: 100rpx 0; text-align: center; }
.loading-text { font-size: 26rpx; color: #94a3b8; }

/* 空态 */
.empty {
  background: #fff; border-radius: 24rpx; padding: 80rpx 40rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06); text-align: center;
}
.empty-text { font-size: 26rpx; color: #94a3b8; }
.empty-sub { display: block; margin-top: 12rpx; font-size: 22rpx; color: #cbd5e1; }

/* 通用卡片 */
.card {
  background: #fff; border-radius: 24rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}

/* 持仓卡片列表：每只独立卡片，留白更足 */
.h-card {
  background: #fff; border-radius: 28rpx; padding: 32rpx;
  margin-bottom: 24rpx; box-shadow: 0 2rpx 12rpx rgba(15, 23, 42, 0.05);
}
.h-card:active { background: #f8fafc; }

/* 层1：名称 + 市值/盈亏 */
.hc-top { display: flex; justify-content: space-between; align-items: flex-start; }
.hc-id { flex: 1; min-width: 0; }
.hc-name-row { display: flex; align-items: center; gap: 12rpx; }
.hc-name {
  font-size: 32rpx; font-weight: 700; color: #0f172a;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300rpx;
}
.item-badge {
  display: inline-block; font-size: 20rpx; line-height: 1;
  padding: 8rpx 14rpx; border-radius: 9999rpx; font-weight: 500; flex-shrink: 0;
}
.hc-account { display: block; margin-top: 12rpx; font-size: 22rpx; color: #94a3b8; }
.hc-right { text-align: right; margin-left: 24rpx; flex-shrink: 0; }
.hc-mv { font-size: 34rpx; font-weight: 700; color: #0f172a; }
.hc-pnl { font-size: 24rpx; margin-top: 10rpx; color: #94a3b8; }
.hc-pnl.positive { color: #059669; }
.hc-pnl.negative { color: #dc2626; }
.hc-pnl-none { font-size: 22rpx; }

/* 层2：三列指标 */
.hc-metrics {
  display: flex; margin-top: 28rpx; padding-top: 24rpx;
  border-top: 1rpx solid #f1f5f9;
}
.hc-cell { flex: 1; }
.hc-label { font-size: 22rpx; color: #94a3b8; margin-bottom: 10rpx; }
.hc-value { font-size: 26rpx; font-weight: 600; color: #334155; }

/* 层3：分红底条 */
.hc-foot {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 24rpx; padding: 18rpx 24rpx;
  background: #f6f8fb; border-radius: 16rpx;
}
.hc-div { display: flex; align-items: baseline; gap: 8rpx; }
.hc-div-icon { font-size: 24rpx; align-self: center; }
.hc-div-label { font-size: 22rpx; color: #64748b; }
.hc-div-amt { font-size: 28rpx; font-weight: 700; color: #059669; }
.hc-yoc { display: flex; align-items: baseline; gap: 8rpx; }
.hc-yoc-label { font-size: 22rpx; color: #64748b; }
.hc-yoc-val { font-size: 26rpx; font-weight: 700; color: #1e3a8a; }

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
