<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="我的" subtitle="账户、汇率、提醒与数据" /><!-- #endif -->

    <!-- 用户卡 -->
    <view class="profile-card">
      <view class="avatar">{{ (user?.nickname || user?.username || '投')[0] }}</view>
      <view class="profile-info">
        <text class="nick">{{ user?.nickname || user?.username || '用户' }}</text>
        <text class="profile-sub">数据按用户隔离 · 仅本人可见</text>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view class="card menu-card">
      <view class="menu-row" @click="go('/pages/accounts/accounts')">
        <SvgIcon name="account" :size="40" />
        <text class="m-label">账户管理</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row" @click="go('/pages/rates/rates')">
        <SvgIcon name="rate" :size="40" />
        <text class="m-label">汇率设置</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row" @click="go('/pages/stats/stats')">
        <SvgIcon name="stats" :size="40" />
        <text class="m-label">统计分析</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row" @click="go('/pages/data/io')">
        <SvgIcon name="data" :size="40" />
        <text class="m-label">数据导入 / 导出</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row no-border" @click="toggleRemind">
        <SvgIcon name="bell" :size="40" />
        <text class="m-label">分红提醒</text>
        <text :class="['m-status', settings.remind_on_payday ? 'on' : 'off']">
          {{ settings.remind_on_payday ? '已开启' : '未开启' }}
        </text>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="logout-wrap">
      <view class="card logout-card" @click="logout">
        <SvgIcon name="logout" :size="36" />
        <text class="logout-text">退出登录</text>
      </view>
    </view>

    <view style="height: 140rpx"></view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiRates, apiSettings, apiSaveSettings, apiLogout } from '@/api'
import { userStore, clearAuth } from '@/store/user'
import WebLayout from '@/components/WebLayout.vue'
import SvgIcon from '@/components/SvgIcon.vue'

const user = computed(() => userStore.user)
const rates = ref({})
const settings = reactive({})

async function load() {
  try {
    const [r, s] = await Promise.all([apiRates(), apiSettings()])
    rates.value = r.rates || {}
    Object.assign(settings, s)
  } catch (e) {}
}
onShow(load)

function go(url) {
  uni.navigateTo({
    url,
    fail: () => uni.switchTab({ url, fail: () => uni.showToast({ title: '页面未就绪', icon: 'none' }) }),
  })
}

async function toggleRemind() {
  const next = !settings.remind_on_payday
  settings.remind_on_payday = next
  try {
    await apiSaveSettings({ remind_on_payday: next ? 1 : 0 })
    uni.showToast({ title: next ? '已开启' : '已关闭', icon: 'none' })
  } catch (e) {
    settings.remind_on_payday = !next
  }
}

function logout() {
  uni.showModal({
    title: '提示', content: '确定退出登录吗？',
    success: async (r) => {
      if (!r.confirm) return
      try { await apiLogout() } catch (e) { /* 即使失败也清本地态 */ }
      clearAuth()
      uni.reLaunch({ url: '/pages/login/login' })
    },
  })
}
</script>

<style scoped>
.page { padding: 24rpx; }

/* 用户卡 */
.profile-card {
  display: flex; align-items: center; gap: 24rpx;
  background: #fff; border-radius: 24rpx; padding: 36rpx 32rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}
.avatar {
  width: 48rpx; height: 48rpx; border-radius: 50%;
  background: #dbeafe; color: #1e3a8a;
  text-align: center; line-height: 48rpx;
  font-size: 28rpx; font-weight: 700; flex-shrink: 0;
}
.profile-info { flex: 1; min-width: 0; }
.nick { display: block; font-size: 30rpx; font-weight: 600; color: #1e293b; }
.profile-sub { display: block; margin-top: 8rpx; font-size: 22rpx; color: #94a3b8; }

/* 菜单卡 */
.card {
  background: #fff; border-radius: 24rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}
.menu-card { margin-top: 24rpx; padding: 0 28rpx; }
.menu-row {
  display: flex; align-items: center; padding: 30rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
  gap: 20rpx;
  color: #475569;
}
.menu-row.no-border { border-bottom: none; }
.menu-row:active { background: #f8fafc; }
.m-label { flex: 1; font-size: 28rpx; color: #1e293b; }
.m-arrow { color: #cbd5e1; flex-shrink: 0; }
.m-status { font-size: 24rpx; }
.m-status.on { color: #059669; }
.m-status.off { color: #94a3b8; }

/* 退出登录 */
.logout-wrap { margin-top: 32rpx; padding: 0 8rpx; }
.logout-card {
  padding: 30rpx 0; text-align: center;
  display: flex; align-items: center; justify-content: center; gap: 12rpx;
  color: #dc2626;
}
.logout-card:active { background: #f8fafc; }
.logout-text { font-size: 28rpx; color: #dc2626; font-weight: 500; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
