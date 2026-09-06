<template>
  <view class="page">
    <view class="card">
      <view class="form-row">
        <text class="form-label">市场</text>
        <picker :range="marketLabels" @change="e => form.market = MARKETS[e.detail.value].value">
          <view class="picker-val">{{ marketLabel }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">代码</text>
        <input class="form-input" v-model="form.code" placeholder="如 600519 / AAPL" />
      </view>
      <view class="form-row">
        <text class="form-label">名称</text>
        <input class="form-input" v-model="form.name" placeholder="如 贵州茅台" />
      </view>
      <view class="form-row">
        <text class="form-label">币种</text>
        <picker :range="currencyLabels" @change="e => form.currency = CURRENCIES[e.detail.value].value">
          <view class="picker-val">{{ currencyLabel }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">派息频率</text>
        <picker :range="freqLabels" @change="e => form.freq = FREQS[e.detail.value].value">
          <view class="picker-val">{{ freqLabel }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">账户</text>
        <input class="form-input" v-model="form.account" placeholder="选填，如 华泰 / 富途" />
      </view>
    </view>

    <view class="section-title">首笔买入（可选）</view>
    <view class="card">
      <view class="form-row">
        <text class="form-label">买入日期</text>
        <picker mode="date" :value="lot.trade_date" @change="e => lot.trade_date = e.detail.value">
          <view class="picker-val">{{ lot.trade_date || '请选择' }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">数量</text>
        <input class="form-input" type="digit" v-model="lot.shares" placeholder="股 / 份" />
      </view>
      <view class="form-row">
        <text class="form-label">成交价</text>
        <input class="form-input" type="digit" v-model="lot.price" placeholder="单价" />
      </view>
      <view class="form-row">
        <text class="form-label">手续费</text>
        <input class="form-input" type="digit" v-model="lot.fee" placeholder="选填，默认 0" />
      </view>
    </view>

    <view style="padding: 30rpx 24rpx">
      <button class="btn-primary" :loading="saving" @click="submit">保 存</button>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { apiCreateHolding } from '@/api'
import { MARKETS, CURRENCIES, FREQS } from '@/utils/constants'

const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  market: 'a_share', code: '', name: '', currency: 'CNY',
  freq: 'unknown', account: '',
})
const lot = reactive({ trade_date: today, shares: '', price: '', fee: '' })
const saving = ref(false)

const marketLabels = MARKETS.map(m => m.label)
const currencyLabels = CURRENCIES.map(c => c.label)
const freqLabels = FREQS.map(f => f.label)
const marketLabel = computed(() => MARKETS.find(m => m.value === form.market)?.label)
const currencyLabel = computed(() => CURRENCIES.find(c => c.value === form.currency)?.label)
const freqLabel = computed(() => FREQS.find(f => f.value === form.freq)?.label)

async function submit() {
  if (!form.code || !form.name) {
    return uni.showToast({ title: '请填写代码和名称', icon: 'none' })
  }
  // 币种随市场联动（未手动改过时）
  const payload = {
    market: form.market, code: form.code.trim(), name: form.name.trim(),
    currency: form.currency, freq: form.freq,
    account: form.account || null,
  }
  if (lot.shares && lot.price && lot.trade_date) {
    payload.first_lot = {
      trade_date: lot.trade_date,
      shares: Number(lot.shares),
      price: Number(lot.price),
      fee: Number(lot.fee || 0),
    }
  }
  saving.value = true
  try {
    await apiCreateHolding(payload)
    uni.showToast({ title: '已添加', icon: 'success' })
    setTimeout(() => uni.navigateBack(), 500)
  } catch (e) { /* toast 统一处理 */ } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.picker-val { text-align: right; color: #1e293b; font-size: 28rpx; }
.form-input::placeholder { color: #cbd5e1; }
</style>
