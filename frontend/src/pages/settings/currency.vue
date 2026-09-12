<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="显示币种" subtitle="勾选要在列表与统计中显示的币种" /><!-- #endif -->

    <view class="tip">勾选后，持仓页、分红页、统计页将只显示勾选币种的数据。统计金额仍统一折算为 CNY。</view>

    <view class="card list-card">
      <view
        v-for="(c, idx) in CURRENCIES"
        :key="c.value"
        :class="['cur-item', idx === CURRENCIES.length - 1 ? 'no-border' : '']"
        @click="toggle(c.value)"
      >
        <view class="cur-info">
          <text class="cur-symbol">{{ c.symbol }}</text>
          <view class="cur-text">
            <text class="cur-label">{{ c.label }}</text>
            <text class="cur-code">{{ c.value }}</text>
          </view>
        </view>
        <view :class="['checkbox', selected.includes(c.value) ? 'on' : '']">
          <text v-if="selected.includes(c.value)" class="check-mark">✓</text>
        </view>
      </view>
    </view>

    <view class="add-btn-wrap">
      <button class="save-btn" :loading="saving" @click="save">保存设置</button>
    </view>

    <view style="height: 140rpx"></view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiSettings, apiSaveSettings } from '@/api'
import { CURRENCIES } from '@/utils/constants'
import { setVisibleCurrencies, userStore } from '@/store/user'
import WebLayout from '@/components/WebLayout.vue'

const selected = ref(['CNY', 'USD', 'HKD'])
const saving = ref(false)

async function load() {
  try {
    const s = await apiSettings()
    if (s.visible_currencies) {
      try {
        const arr = JSON.parse(s.visible_currencies)
        if (Array.isArray(arr) && arr.length) selected.value = arr
      } catch (e) {}
    }
  } catch (e) {}
}
onShow(load)

function toggle(code) {
  const i = selected.value.indexOf(code)
  if (i >= 0) {
    if (selected.value.length === 1) {
      return uni.showToast({ title: '至少保留一个币种', icon: 'none' })
    }
    selected.value.splice(i, 1)
  } else {
    selected.value.push(code)
  }
}

async function save() {
  if (!selected.value.length) {
    return uni.showToast({ title: '至少选择一个币种', icon: 'none' })
  }
  saving.value = true
  try {
    await apiSaveSettings({
      visible_currencies: JSON.stringify(selected.value),
    })
    // 同步到 store，让其他页面立即可见
    setVisibleCurrencies(selected.value)
    uni.showToast({ title: '保存成功', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 600)
  } catch (e) {
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page { padding: 24rpx; }
.tip {
  background: #fff; border-radius: 16rpx; padding: 20rpx 24rpx;
  font-size: 24rpx; color: #94a3b8; line-height: 1.5; margin-bottom: 24rpx;
}
.card { background: #fff; border-radius: 24rpx; box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.06); }
.list-card { padding: 0 28rpx; }
.cur-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 30rpx 0; border-bottom: 1rpx solid #f1f5f9;
}
.cur-item.no-border { border-bottom: none; }
.cur-info { display: flex; align-items: center; gap: 20rpx; }
.cur-symbol {
  width: 64rpx; height: 64rpx; line-height: 64rpx; text-align: center;
  background: #eff6ff; color: #1e3a8a; border-radius: 16rpx;
  font-size: 28rpx; font-weight: 700;
}
.cur-text { display: flex; flex-direction: column; }
.cur-label { font-size: 30rpx; color: #1e293b; font-weight: 500; }
.cur-code { font-size: 22rpx; color: #94a3b8; margin-top: 4rpx; }

.checkbox {
  width: 44rpx; height: 44rpx; border-radius: 50%;
  border: 2rpx solid #cbd5e1; display: flex;
  align-items: center; justify-content: center;
}
.checkbox.on { background: #1e3a8a; border-color: #1e3a8a; }
.check-mark { color: #fff; font-size: 24rpx; font-weight: 700; }

.add-btn-wrap { margin-top: 40rpx; padding: 0 8rpx; }
.save-btn {
  width: 100%; height: 88rpx; line-height: 88rpx;
  background: #1e3a8a; color: #fff; font-size: 30rpx;
  border-radius: 24rpx; border: none;
  box-shadow: 0 4rpx 12rpx rgba(30, 58, 138, 0.18);
}
.save-btn::after { border: none; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
