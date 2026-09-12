<template>
  <view class="page">
    <!-- 选择标的 -->
    <view class="section-title">选择标的</view>
    <view class="card sec-card">
      <!-- #ifdef H5 -->
      <view class="sec-search">
        <input class="search-input" v-model="secKeyword" placeholder="输入代码或名称搜索（仅列出已有分红数据的标的）"
               @input="onSecInput" @focus="secFocused = true" />
        <text v-if="selectedSec" class="sec-clear" @click="clearSec">✕</text>
      </view>
      <view v-if="secFocused && !selectedSec && filteredSecs.length" class="sec-dropdown">
        <view v-for="s in filteredSecs" :key="s.market + s.code" class="sec-item" @click="pickSec(s)">
          <view class="sec-item-main">
            <text :class="['tag', badgeClass(s.market)]">{{ marketMap[s.market]?.label }}</text>
            <text class="sec-item-name">{{ s.name }}</text>
            <text class="sec-item-code">{{ s.code }}</text>
          </view>
          <text v-if="s.latest_price" class="sec-item-price">{{ sym(s.currency) }}{{ fmt(s.latest_price) }}</text>
        </view>
      </view>
      <view v-else-if="secFocused && !selectedSec && secKeyword && !filteredSecs.length" class="sec-empty">
        未找到匹配的标的
      </view>
      <!-- #endif -->
      <!-- #ifdef MP-WEIXIN -->
      <picker v-if="!selectedSec" mode="selector" :range="secPickerLabels" @change="onSecPickerChange">
        <view class="picker-placeholder">点击选择标的（共 {{ securities.length }} 个）</view>
      </picker>
      <view v-else class="sec-search">
        <text class="picked-text">{{ selectedSec.name }}（{{ selectedSec.code }}）</text>
        <text class="sec-clear" @click="clearSec">✕</text>
      </view>
      <!-- #endif -->
    </view>

    <!-- 已选标的信息 -->
    <view v-if="selectedSec" class="card">
      <view class="form-row">
        <text class="form-label">市场</text>
        <text class="form-static">{{ marketMap[form.market]?.label }}</text>
      </view>
      <view class="form-row">
        <text class="form-label">代码</text>
        <text class="form-static">{{ form.code }}</text>
      </view>
      <view class="form-row">
        <text class="form-label">名称</text>
        <text class="form-static">{{ form.name }}</text>
      </view>
      <view class="form-row">
        <text class="form-label">币种</text>
        <text class="form-static">{{ form.currency }}</text>
      </view>
      <view v-if="form.latest_price" class="price-tip">
        <text>参考最新价：</text><text class="price-val">{{ sym(form.currency) }}{{ fmt(form.latest_price) }}</text>
        <text class="text-muted">（来自行情抓取，可能非实时）</text>
      </view>
    </view>

    <!-- 派息频率 + 账户 -->
    <view v-if="selectedSec" class="card">
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

    <!-- 首笔买入（可选） -->
    <view v-if="selectedSec" class="section-title">首笔买入（可选）</view>
    <view v-if="selectedSec" class="card">
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

    <view v-if="selectedSec" style="padding: 30rpx 24rpx">
      <button class="btn-primary" :loading="saving" @click="submit">保 存</button>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiCreateHolding, apiSecurities } from '@/api'
import { FREQS, marketMap, currencyMap, badgeClass } from '@/utils/constants'

const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  market: '', code: '', name: '', currency: '',
  freq: 'unknown', account: '',
  latest_price: null,
})
const lot = reactive({ trade_date: today, shares: '', price: '', fee: '' })
const saving = ref(false)

// 标的搜索
const securities = ref([])
const secKeyword = ref('')
const secFocused = ref(false)
const selectedSec = ref(null)

const freqLabels = FREQS.map(f => f.label)
const freqLabel = computed(() => FREQS.find(f => f.value === form.freq)?.label)

// #ifdef H5
const filteredSecs = computed(() => {
  const kw = secKeyword.value.trim().toLowerCase()
  if (!kw) return securities.value.slice(0, 8)
  return securities.value
    .filter(s =>
      (s.code || '').toLowerCase().includes(kw) ||
      (s.name || '').toLowerCase().includes(kw))
    .slice(0, 8)
})
// #endif

// #ifdef MP-WEIXIN
const secPickerLabels = computed(() =>
  securities.value.map(s => `${s.name}（${s.code}）`))
// #endif

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

async function loadSecurities() {
  try {
    const data = await apiSecurities({ keyword: '' })
    securities.value = data.items || []
  } catch (e) { /* toast 统一处理 */ }
}

// #ifdef H5
function onSecInput() {
  secFocused.value = true
  selectedSec.value = null
}
// #endif

// #ifdef MP-WEIXIN
function onSecPickerChange(e) {
  const s = securities.value[e.detail.value]
  if (s) pickSec(s)
}
// #endif

function pickSec(s) {
  selectedSec.value = s
  form.market = s.market
  form.code = s.code
  form.name = s.name
  form.currency = s.currency
  form.latest_price = s.latest_price
  form.freq = s.freq && s.freq !== 'unknown' ? s.freq : 'unknown'
  // #ifdef H5
  secKeyword.value = `${s.name}（${s.code}）`
  secFocused.value = false
  // #endif
}

function clearSec() {
  selectedSec.value = null
  secKeyword.value = ''
  form.market = ''; form.code = ''; form.name = ''
  form.currency = ''; form.latest_price = null; form.freq = 'unknown'
  // #ifdef H5
  secFocused.value = true
  // #endif
}

async function submit() {
  if (!form.code || !form.name) {
    return uni.showToast({ title: '请先选择标的', icon: 'none' })
  }
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

onLoad(loadSecurities)
</script>

<style scoped>
.sec-card { padding: 20rpx 24rpx; }
.sec-search { display: flex; align-items: center; gap: 16rpx; }
.search-input {
  flex: 1; height: 72rpx; background: #f8fafc; border-radius: 40rpx;
  padding: 0 30rpx; font-size: 26rpx;
}
.picker-placeholder {
  height: 72rpx; line-height: 72rpx; background: #f8fafc; border-radius: 40rpx;
  padding: 0 30rpx; font-size: 26rpx; color: #94a3b8;
}
.picked-text { flex: 1; font-size: 28rpx; color: #1e3a8a; font-weight: 600; }
.sec-clear { font-size: 32rpx; color: #94a3b8; padding: 0 10rpx; }
.sec-dropdown {
  margin-top: 16rpx; border-top: 1rpx solid #f1f5f9; padding-top: 10rpx;
  max-height: 480rpx; overflow-y: auto;
}
.sec-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20rpx 8rpx; border-bottom: 1rpx solid #f8fafc;
}
.sec-item:last-child { border-bottom: none; }
.sec-item-main { display: flex; align-items: center; gap: 12rpx; flex: 1; min-width: 0; }
.sec-item-name { font-size: 28rpx; font-weight: 500; color: #1e293b; }
.sec-item-code { font-size: 24rpx; color: #94a3b8; }
.sec-item-price { font-size: 24rpx; color: #475569; }
.sec-empty { padding: 30rpx 0; text-align: center; font-size: 24rpx; color: #94a3b8; }
.picker-val { text-align: right; color: #1e293b; font-size: 28rpx; }
.form-static { flex: 1; text-align: right; color: #1e293b; font-size: 28rpx; }
.form-input::placeholder { color: #cbd5e1; }
.price-tip {
  margin-top: 16rpx; padding: 16rpx 20rpx; background: #f8fafc;
  border-radius: 12rpx; font-size: 24rpx; color: #475569; line-height: 1.6;
}
.price-val { font-weight: 700; color: #1e3a8a; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; }
  .sec-dropdown { max-height: 360rpx; }
}
/* #endif */
</style>
