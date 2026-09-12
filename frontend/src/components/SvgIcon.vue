<template>
  <!-- 统一的 SVG 图标组件，用 currentColor 控制颜色 -->
  <view class="icon" :style="{ width: size + 'rpx', height: size + 'rpx' }">
    <svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor"
         :stroke-width="stroke" stroke-linecap="round" stroke-linejoin="round">
      <!-- 总览/首页 -->
      <template v-if="name === 'home'">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
      </template>
      <!-- 持仓 -->
      <template v-else-if="name === 'holdings'">
        <path d="M3 3h18v18H3z"/>
        <path d="M3 9h18"/>
        <path d="M9 21V9"/>
      </template>
      <!-- 记分红（加号） -->
      <template v-else-if="name === 'record'">
        <circle cx="12" cy="12" r="9"/>
        <path d="M12 8v8M8 12h8"/>
      </template>
      <!-- 日历 -->
      <template v-else-if="name === 'calendar'">
        <rect x="3" y="4" width="18" height="18" rx="2"/>
        <path d="M16 2v4M8 2v4M3 10h18"/>
      </template>
      <!-- 我的 -->
      <template v-else-if="name === 'mine'">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </template>
      <!-- 统计 -->
      <template v-else-if="name === 'stats'">
        <path d="M3 3v18h18"/>
        <path d="M7 14l3-3 3 3 5-6"/>
      </template>
      <!-- 设置 -->
      <template v-else-if="name === 'settings'">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
      </template>
      <!-- 账户 -->
      <template v-else-if="name === 'account'">
        <rect x="2" y="5" width="20" height="14" rx="2"/>
        <path d="M2 10h20"/>
      </template>
      <!-- 汇率 -->
      <template v-else-if="name === 'rate'">
        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
      </template>
      <!-- 数据导入导出 -->
      <template v-else-if="name === 'data'">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </template>
      <!-- 提醒/铃铛 -->
      <template v-else-if="name === 'bell'">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </template>
      <!-- 退出 -->
      <template v-else-if="name === 'logout'">
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
        <polyline points="16 17 21 12 16 7"/>
        <line x1="21" y1="12" x2="9" y2="12"/>
      </template>
      <!-- 右箭头 -->
      <template v-else-if="name === 'arrow-right'">
        <polyline points="9 18 15 12 9 6"/>
      </template>
      <!-- 下拉 -->
      <template v-else-if="name === 'chevron-down'">
        <polyline points="6 9 12 15 18 9"/>
      </template>
    </svg>
  </view>
</template>

<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 40 },
  stroke: { type: Number, default: 2 },
})
</script>

<style scoped>
.icon { display: inline-flex; align-items: center; justify-content: center; }
</style>
