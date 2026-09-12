<template>
  <!-- 仅 H5 端 ≥768px 渲染顶部导航；移动端保持原生 TabBar -->
  <!-- #ifdef H5 -->
  <view v-if="showDesktop" class="web-topbar">
    <view class="topbar-left">
      <view class="brand" @click="go('/pages/index/index')">
        <view class="logo">攒</view>
        <view class="brand-text">
          <view class="brand-name">攒息</view>
          <view class="brand-sub">时间的朋友</view>
        </view>
      </view>
      <nav class="nav">
        <view v-for="item in menus" :key="item.path"
              :class="['nav-item', current === item.path ? 'active' : '']"
              @click="go(item.path)">
          <SvgIcon :name="item.icon" :size="16" :stroke="2" />
          <text>{{ item.label }}</text>
        </view>
      </nav>
    </view>
    <view class="topbar-right">
      <slot name="actions" />
      <view class="user-box" @click="goMine">
        <view class="avatar">{{ avatarText }}</view>
        <view class="user-name">{{ nickname }}</view>
      </view>
    </view>
  </view>
  <!-- #endif -->
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { userStore } from '@/store/user'
import SvgIcon from './SvgIcon.vue'

defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})

const showDesktop = ref(false)
const current = ref('')
const menus = [
  { path: '/pages/index/index', label: '总览看板', icon: 'home' },
  { path: '/pages/holdings/holdings', label: '持仓管理', icon: 'holdings' },
  { path: '/pages/dividends/list', label: '分红记录', icon: 'record' },
  { path: '/pages/calendar/calendar', label: '分红日历', icon: 'calendar' },
  { path: '/pages/stats/stats', label: '统计分析', icon: 'stats' },
  { path: '/pages/mine/mine', label: '我的', icon: 'mine' },
]

const user = computed(() => userStore.user || {})
const nickname = computed(() => user.value.nickname || user.value.username || '用户')
const avatarText = computed(() => (nickname.value || 'U').charAt(0).toUpperCase())

function checkWidth() {
  // #ifdef H5
  showDesktop.value = window.innerWidth >= 768
  // 自定义 TabBar 通过 CSS 控制显示/隐藏，无需 API 调用
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
/* #ifdef H5 */
.web-topbar {
  position: fixed; top: 0; left: 0; right: 0; height: 60px; z-index: 999;
  background: #fff; border-bottom: 1px solid #e2e8f0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.topbar-left { display: flex; align-items: center; gap: 32px; }
.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.logo {
  width: 34px; height: 34px; border-radius: 8px; background: #1e3a8a;
  color: #fff; font-weight: 700; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
}
.brand-text { line-height: 1.2; }
.brand-name { font-weight: 700; font-size: 16px; color: #1e3a8a; letter-spacing: 1px; }
.brand-sub { font-size: 11px; color: #94a3b8; }
.nav { display: flex; align-items: center; gap: 4px; }
.nav-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 14px;
  border-radius: 8px; color: #64748b; font-size: 14px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
}
.nav-item:hover { background: #f1f5f9; color: #1e3a8a; }
.nav-item.active { background: #1e3a8a; color: #fff; }
.topbar-right { display: flex; align-items: center; gap: 16px; }
.user-box { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; background: #dbeafe;
  color: #1e3a8a; font-weight: 600; display: flex; align-items: center; justify-content: center;
}
.user-name { font-size: 14px; font-weight: 500; }

@media (min-width: 768px) {
  page { padding-top: 60px; }
  uni-tabbar, .uni-tabbar, uni-tabbar + view { display: none !important; }
}
/* #endif */
</style>
