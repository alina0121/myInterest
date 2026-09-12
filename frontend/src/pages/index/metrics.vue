<template>
  <view class="page">
    <!-- 提示 -->
    <view class="hint-card">
      <view class="hint-text">已选 {{ tempSelected.length }} / {{ maxSelect }} · 点击可加入或取消</view>
      <view class="hint-tip">提示：第 1 个为主指标，显示在首页主卡顶部大字</view>
    </view>

    <!-- 已选指标 -->
    <view class="group-title">已选指标（{{ tempSelected.length }}）</view>
    <view class="metric-list">
      <view
        v-for="(key, idx) in tempSelected"
        :key="key"
        class="metric-row selected"
        @click="tempSelected.splice(idx, 1)"
      >
        <view class="metric-num">{{ idx + 1 }}</view>
        <view class="metric-info">
          <view class="metric-name">
            {{ getMetricDef(key)?.name }}
            <text v-if="idx === 0" class="main-tag">主指标</text>
          </view>
          <view class="metric-desc">{{ getMetricDef(key)?.desc }}</view>
        </view>
        <view class="metric-val">{{ formatMetricValue(getMetricDef(key), enhanced[key]) }}</view>
      </view>
    </view>

    <!-- 可选指标 -->
    <view class="group-title">可选指标（{{ availableMetrics.length }}）</view>
    <view class="metric-list">
      <view
        v-for="m in availableMetrics"
        :key="m.key"
        class="metric-row available"
        @click="addMetric(m.key)"
      >
        <view class="metric-plus">+</view>
        <view class="metric-info">
          <view class="metric-name">{{ m.name }}</view>
          <view class="metric-desc">{{ m.desc }}</view>
        </view>
        <view class="metric-val">{{ formatMetricValue(m, enhanced[m.key]) }}</view>
      </view>
      <view v-if="tempSelected.length >= maxSelect" class="empty-tip">
        已达最大可选数量（{{ maxSelect }}），请先取消不需要的指标
      </view>
    </view>

    <!-- 保存按钮 -->
    <view class="save-wrap">
      <button class="save-btn" @click="saveMetrics">确认保存</button>
    </view>
  </view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiDashboardMetrics, apiSaveDashboardMetrics, apiEnhancedSummary } from '@/api'

const registry = ref([])
const enhanced = ref({})
const tempSelected = ref([])
const maxSelect = ref(9)

const availableMetrics = computed(() => {
  const sel = new Set(tempSelected.value)
  return registry.value.filter(m => !sel.has(m.key))
})

function getMetricDef(key) {
  return registry.value.find(m => m.key === key)
}

function fmt(n, digits = 2) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

function formatMetricValue(def, val) {
  if (val === null || val === undefined || val === 0) return '—'
  if (!def) return fmt(val)
  switch (def.format) {
    case 'currency': return '¥' + fmt(val)
    case 'percent': return (val * 100).toFixed(2) + '%'
    case 'number': return val + ' 只'
    default: return fmt(val)
  }
}

function addMetric(key) {
  if (tempSelected.value.length >= maxSelect.value) return
  tempSelected.value.push(key)
}

async function saveMetrics() {
  if (!tempSelected.value.length) return
  try {
    await apiSaveDashboardMetrics(tempSelected.value)
    uni.showToast({ title: '保存成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 800)
  } catch (e) {
    uni.showToast({ title: '保存失败', icon: 'none' })
  }
}

async function load() {
  try {
    const [fm, enh] = await Promise.all([
      apiDashboardMetrics(),
      apiEnhancedSummary(),
    ])
    registry.value = fm.registry
    tempSelected.value = [...fm.selected]
    maxSelect.value = fm.max_select
    enhanced.value = enh
  } catch (e) { /* toast 已统一处理 */ }
}

onLoad(load)
</script>

<style scoped>
.page { padding: 24rpx; padding-bottom: 180rpx; }

.hint-card {
  background: #f8f8f8;
  border-radius: 16rpx;
  padding: 20rpx 24rpx;
  margin-bottom: 24rpx;
}
.hint-text {
  font-size: 26rpx;
  color: #666;
}
.hint-tip {
  font-size: 22rpx;
  color: #999;
  margin-top: 6rpx;
}

.group-title {
  font-size: 26rpx;
  color: #999;
  margin: 24rpx 8rpx 12rpx;
}

.metric-list {
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
  border: 1rpx solid #f0f0f0;
}
.metric-row {
  display: flex;
  align-items: center;
  padding: 28rpx 24rpx;
  border-bottom: 1rpx solid #f5f5f5;
}
.metric-row:last-child { border-bottom: none; }
.metric-row.selected { background: #fafafa; }
.metric-row:active { background: #f0f0f0; }

.metric-num {
  width: 52rpx;
  height: 52rpx;
  background: #1a1a2e;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: 600;
  margin-right: 20rpx;
  flex-shrink: 0;
}
.metric-plus {
  width: 52rpx;
  height: 52rpx;
  background: #f0f0f0;
  color: #999;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  margin-right: 20rpx;
  flex-shrink: 0;
}
.metric-info { flex: 1; min-width: 0; }
.metric-name {
  font-size: 30rpx;
  font-weight: 500;
  color: #1a1a1a;
}
.metric-name .main-tag {
  display: inline-block;
  font-size: 20rpx;
  color: #1a1a2e;
  background: #fef3c7;
  padding: 2rpx 12rpx;
  border-radius: 6rpx;
  margin-left: 12rpx;
  font-weight: 400;
}
.metric-desc {
  font-size: 24rpx;
  color: #999;
  margin-top: 6rpx;
}
.metric-val {
  font-size: 26rpx;
  color: #1a1a1a;
  font-weight: 500;
  white-space: nowrap;
  margin-left: 16rpx;
}

.empty-tip {
  padding: 40rpx;
  text-align: center;
  color: #999;
  font-size: 26rpx;
}

.save-wrap {
  position: fixed;
  bottom: 40rpx;
  left: 24rpx;
  right: 24rpx;
}
.save-btn {
  background: #1a1a2e;
  color: #fff;
  border-radius: 24rpx;
  font-size: 32rpx;
  font-weight: 600;
  height: 96rpx;
  line-height: 96rpx;
}
</style>
