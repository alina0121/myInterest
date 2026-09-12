<template>
  <view class="tabbar">
    <view
      v-for="item in list"
      :key="item.pagePath"
      :class="['tab-item', current === item.pagePath ? 'active' : '']"
      @click="switchTab(item.pagePath)"
    >
      <SvgIcon :name="item.icon" :size="44" :stroke="current === item.pagePath ? 2.5 : 2" />
      <text class="tab-text">{{ item.text }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import SvgIcon from './SvgIcon.vue'

const list = [
  { pagePath: '/pages/index/index', text: '总览', icon: 'home' },
  { pagePath: '/pages/holdings/holdings', text: '持仓', icon: 'holdings' },
  { pagePath: '/pages/record/record', text: '记分红', icon: 'record' },
  { pagePath: '/pages/calendar/calendar', text: '日历', icon: 'calendar' },
  { pagePath: '/pages/mine/mine', text: '我的', icon: 'mine' },
]

const current = ref('/pages/index/index')

function switchTab(path) {
  if (current.value === path) return
  current.value = path
  uni.switchTab({ url: path })
}

// 监听页面切换，更新高亮
const pages = getCurrentPages()
if (pages.length) {
  current.value = '/' + pages[pages.length - 1].route
}
</script>

<style scoped>
.tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 110rpx;
  background: #fff;
  border-top: 1rpx solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 999;
}
.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4rpx;
  color: #94a3b8;
  transition: color 0.2s;
}
.tab-item.active { color: #1e3a8a; }
.tab-text { font-size: 20rpx; margin-top: 2rpx; }
</style>
