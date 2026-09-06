<template>
  <!-- 仅 H5 端 ≥768px 渲染侧边栏 + 顶部栏；移动端保持原生 TabBar -->
  <!-- #ifdef H5 -->
  <view v-if="showDesktop" class="web-shell">
    <!-- 左侧边栏 -->
    <aside class="web-sidebar">
      <view class="brand">
        <view class="logo">息</view>
        <view>
          <view class="brand-name">息计</view>
          <view class="brand-sub">分红记录助手</view>
        </view>
      </view>
      <nav class="nav">
        <view v-for="item in menus" :key="item.path"
              :class="['nav-item', current === item.path ? 'active' : '']"
              @click="go(item.path)">
          <text class="nav-icon">{{ item.icon }}</text>
          <text class="nav-label">{{ item.label }}</text>
        </view>
      </nav>
      <view class="sidebar-foot">v1.0.0 · 桌面版</view>
    </aside>

    <!-- 顶部栏 -->
    <header class="web-header">
      <view class="hdr-left">
        <view class="page-title">{{ title }}</view>
        <view class="page-sub">{{ subtitle }}</view>
      </view>
      <view class="hdr-right">
        <slot name="actions" />
        <view class="user-box" @click="goMine">
          <view class="avatar">{{ avatarText }}</view>
          <view class="user-info">
            <view class="user-name">{{ nickname }}</view>
            <view class="user-logout">退出登录 →</view>
          </view>
        </view>
      </view>
    </header>
  </view>
  <!-- #endif -->
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { userStore } from '@/store/user'

const props = defineProps({
  title: { type: String, default: '总览看板' },
  subtitle: { type: String, default: '记录每一笔分红，见证复利的力量' },
})

const showDesktop = ref(false)
const current = ref('')
const menus = [
  { path: '/pages/index/index', label: '总览看板', icon: '📊' },
  { path: '/pages/holdings/holdings', label: '持仓管理', icon: '📈' },
  { path: '/pages/dividends/list', label: '分红记录', icon: '💰' },
  { path: '/pages/calendar/calendar', label: '分红日历', icon: '📅' },
  { path: '/pages/stats/stats', label: '统计分析', icon: '📉' },
  { path: '/pages/mine/mine', label: '我的', icon: '⚙️' },
]

const user = computed(() => userStore.user || {})
const nickname = computed(() => user.value.nickname || user.value.username || '用户')
const avatarText = computed(() => (nickname.value || 'U').charAt(0).toUpperCase())

function checkWidth() {
  // #ifdef H5
  showDesktop.value = window.innerWidth >= 768
  if (showDesktop.value) {
    uni.hideTabBar({ animation: false })
  } else {
    uni.showTabBar({ animation: false })
  }
  // #endif
}

function go(path) {
  if (current.value === path) return
  uni.reLaunch({ url: path })
}
function goMine() { uni.reLaunch({ url: '/pages/mine/mine' }) }

onMounted(() => {
  checkWidth()
  // #ifdef H5
  window.addEventListener('resize', checkWidth)
  // #endif
})
onUnmounted(() => {
  // #ifdef H5
  window.removeEventListener('resize', checkWidth)
  // #endif
})
onShow(() => {
  // #ifdef H5
  const pages = getCurrentPages()
  if (pages.length) {
    current.value = '/' + pages[pages.length - 1].route
  }
  checkWidth()
  // #endif
})
</script>

<style>
/* H5 桌面布局：侧边栏 fixed + 顶部栏 fixed，页面内容靠 padding 让位 */
/* #ifdef H5 */
.web-shell { position: fixed; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; z-index: 999; }
.web-shell > * { pointer-events: auto; }
.web-sidebar {
  position: fixed; left: 0; top: 0; bottom: 0; width: 224px;
  background: #fff; border-right: 1rpx solid #e2e8f0;
  display: flex; flex-direction: column;
}
.brand { display: flex; align-items: center; gap: 16rpx; padding: 32rpx; border-bottom: 1rpx solid #f1f5f9; }
.logo { width: 56rpx; height: 56rpx; border-radius: 12rpx; background: #1e3a8a; color: #fff; font-weight: 700; font-size: 32rpx; display: flex; align-items: center; justify-content: center; }
.brand-name { font-weight: 700; color: #1e293b; font-size: 30rpx; }
.brand-sub { font-size: 20rpx; color: #94a3b8; }
.nav { flex: 1; padding: 20rpx; }
.nav-item { display: flex; align-items: center; gap: 18rpx; padding: 20rpx 24rpx; border-radius: 12rpx; color: #64748b; font-size: 28rpx; margin-bottom: 6rpx; cursor: pointer; }
.nav-item:hover { background: #f8fafc; }
.nav-item.active { background: #1e3a8a; color: #fff; }
.nav-icon { font-size: 32rpx; }
.sidebar-foot { padding: 24rpx; font-size: 20rpx; color: #cbd5e1; border-top: 1rpx solid #f1f5f9; }
.web-header {
  position: fixed; top: 0; left: 224px; right: 0; height: 80px;
  background: #fff; border-bottom: 1rpx solid #e2e8f0;
  display: flex; align-items: center; justify-content: space-between; padding: 0 40rpx;
}
.hdr-left .page-title { font-size: 34rpx; font-weight: 700; color: #1e293b; }
.hdr-left .page-sub { font-size: 24rpx; color: #94a3b8; margin-top: 4rpx; }
.hdr-right { display: flex; align-items: center; gap: 24rpx; }
.user-box { display: flex; align-items: center; gap: 16rpx; cursor: pointer; }
.avatar { width: 64rpx; height: 64rpx; border-radius: 50%; background: #dbeafe; color: #1e3a8a; font-weight: 600; display: flex; align-items: center; justify-content: center; }
.user-info .user-name { font-size: 26rpx; font-weight: 500; color: #475569; }
.user-info .user-logout { font-size: 20rpx; color: #94a3b8; }
.user-box:hover .user-logout { color: #ef4444; }
/* 页面内容让位：H5 桌面端 */
@media (min-width: 768px) {
  page { padding-left: 224px; padding-top: 80px; }
  /* 隐藏原生 TabBar，改用侧边栏导航 */
  uni-tabbar, .uni-tabbar, uni-tabbar + view { display: none !important; }
}
/* #endif */
</style>
