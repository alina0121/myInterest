<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="我的" subtitle="账户、汇率、提醒与数据" /><!-- #endif -->
    <!-- 用户卡 -->
    <view class="profile">
      <view class="avatar">{{ (user?.nickname || user?.username || '投')[0] }}</view>
      <view style="flex:1">
        <view class="nick">{{ user?.nickname || user?.username }}</view>
        <view class="uid">@{{ user?.username }} · {{ user?.has_wx ? '已绑微信' : '账号登录' }}</view>
      </view>
      <view class="tag" style="background: rgba(255,255,255,0.25)">v0.1</view>
    </view>

    <!-- 功能菜单 -->
    <view class="card menu">
      <view class="menu-row" @click="go('/pages/dividends/list')">
        <text class="m-icon">💰</text><text class="m-label">分红记录</text><text class="m-arrow">›</text>
      </view>
      <view class="menu-row" @click="go('/pages/dividends/add')">
        <text class="m-icon">✍️</text><text class="m-label">记一笔分红</text><text class="m-arrow">›</text>
      </view>
      <view class="menu-row" @click="go('/pages/holdings/holdings')">
        <text class="m-icon">📊</text><text class="m-label">我的持仓</text><text class="m-arrow">›</text>
      </view>
    </view>

    <!-- 汇率 -->
    <view class="section-title">今日汇率</view>
    <view class="card rate-card">
      <view v-for="(r, k) in rates" :key="k" class="rate-row">
        <text class="r-cur">{{ k }}/CNY</text>
        <text class="r-val">{{ r }}</text>
      </view>
      <view v-if="!Object.keys(rates).length" class="text-muted">加载中…</view>
    </view>

    <!-- 提醒设置 -->
    <view class="section-title">提醒设置</view>
    <view class="card menu">
      <view class="menu-row">
        <text class="m-icon">🔔</text><text class="m-label">派息日提醒</text>
        <switch :checked="!!settings.remind_on_payday" color="#1668dc" @change="e => save('remind_on_payday', e.detail.value)" />
      </view>
      <view class="menu-row">
        <text class="m-icon">📣</text><text class="m-label">推送通知</text>
        <switch :checked="!!settings.push_enabled" color="#1668dc" @change="e => save('push_enabled', e.detail.value)" />
      </view>
      <view class="menu-row">
        <text class="m-icon">🤖</text><text class="m-label">自动匹配分红预告</text>
        <switch :checked="!!settings.auto_match_schedule" color="#1668dc" @change="e => save('auto_match_schedule', e.detail.value)" />
      </view>
    </view>

    <view style="padding: 40rpx 24rpx">
      <button class="btn-ghost" @click="logout">退出登录</button>
    </view>
    <view class="footer text-muted">息计 · 让每一笔分红都有记录</view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiRates, apiSettings, apiSaveSettings } from '@/api'
import { userStore, clearAuth } from '@/store/user'
import WebLayout from '@/components/WebLayout.vue'

const user = computed(() => userStore.user)
const rates = ref({})
const settings = reactive({})

async function load() {
  try {
    const r = await apiRates()
    rates.value = r.rates
    Object.assign(settings, await apiSettings())
  } catch (e) {}
}
onShow(load)

async function save(key, val) {
  settings[key] = val
  await apiSaveSettings({ [key]: val ? 1 : 0 })
  uni.showToast({ title: '已保存', icon: 'none' })
}

function go(url) {
  // tabbar 页用 switchTab，其余 navigateTo
  if (url.includes('holdings/holdings')) return uni.switchTab({ url })
  uni.navigateTo({ url })
}

function logout() {
  uni.showModal({
    title: '提示', content: '确定退出登录吗？',
    success: (r) => {
      if (r.confirm) {
        clearAuth()
        uni.reLaunch({ url: '/pages/login/login' })
      }
    },
  })
}
</script>

<style scoped>
.profile {
  display: flex; align-items: center; gap: 24rpx;
  background: linear-gradient(135deg, #1668dc, #3b82f6);
  margin: 20rpx 24rpx; border-radius: 20rpx; padding: 40rpx 32rpx; color: #fff;
}
.avatar {
  width: 100rpx; height: 100rpx; border-radius: 50%;
  background: rgba(255,255,255,0.25); text-align: center; line-height: 100rpx;
  font-size: 44rpx; font-weight: 700;
}
.nick { font-size: 34rpx; font-weight: 700; }
.uid { font-size: 24rpx; opacity: 0.85; margin-top: 8rpx; }
.menu { padding: 0 28rpx; }
.menu-row { display: flex; align-items: center; padding: 30rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.menu-row:last-child { border-bottom: none; }
.m-icon { font-size: 36rpx; margin-right: 20rpx; }
.m-label { flex: 1; font-size: 28rpx; }
.m-arrow { color: #cbd5e1; font-size: 36rpx; }
.rate-card { padding: 10rpx 28rpx; }
.rate-row { display: flex; justify-content: space-between; padding: 22rpx 0; border-bottom: 1rpx solid #f1f5f9; font-size: 28rpx; }
.rate-row:last-child { border-bottom: none; }
.r-cur { color: #64748b; }
.r-val { font-weight: 600; }
.footer { text-align: center; font-size: 22rpx; padding: 20rpx 0 60rpx; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
