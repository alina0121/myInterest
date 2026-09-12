<template>
  <view class="page">
    <view class="card">
      <view class="form-row">
        <text class="form-label">持仓</text>
        <picker :range="holdingNames" @change="onPickHolding">
          <view class="picker-val">{{ pickedName || '请选择持仓' }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">除权日</text>
        <picker mode="date" :value="form.ex_date" @change="e => form.ex_date = e.detail.value">
          <view class="picker-val">{{ form.ex_date }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">股权登记日</text>
        <picker mode="date" :value="form.record_date" @change="e => form.record_date = e.detail.value">
          <view class="picker-val">{{ form.record_date || '不填则自动推断（A股=除权日前一天）' }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">派息日</text>
        <picker mode="date" :value="form.pay_date" @change="e => form.pay_date = e.detail.value">
          <view class="picker-val">{{ form.pay_date }}</view>
        </picker>
      </view>
      <view class="form-row">
        <text class="form-label">每股分红</text>
        <input class="form-input" type="digit" v-model="form.dps" placeholder="税前每股/每份金额" />
      </view>
      <view class="form-row">
        <text class="form-label">税费(选填)</text>
        <input class="form-input" type="digit" v-model="form.tax" placeholder="留空自动按规则估算" />
      </view>
      <view class="form-row">
        <text class="form-label">状态</text>
        <picker :range="['已到账', '预告(待确认)']" @change="e => form.status = e.detail.value === '0' ? 'confirmed' : 'pending'">
          <view class="picker-val">
            <text :class="['tag', form.status === 'confirmed' ? 'badge-confirmed' : 'badge-pending']">
              {{ form.status === 'confirmed' ? '已到账' : '预告(待确认)' }}
            </text>
          </view>
        </picker>
      </view>
    </view>

    <view class="tip card">
      提交后系统将按「股权登记日」自动匹配你当时持有的买入批次，计算参与股数与税费（A股按持有时间 0/10%/20% 分档，美股 10%，港股通 20%）。
    </view>

    <view style="padding: 20rpx 24rpx">
      <button class="btn-primary" :loading="saving" @click="submit">保存并自动计算归属</button>
    </view>

    <!-- 计算结果弹层 -->
    <view v-if="result" class="mask" @click="result = null">
      <view class="sheet" @click.stop>
        <view class="sheet-title">归属计算结果</view>
        <view class="r-row"><text>登记日持仓</text><text class="r-bold">{{ result.shares }} 股</text></view>
        <view class="r-row"><text>税前分红</text><text class="r-bold">{{ sym(result.currency) }}{{ fmt(result.gross_amount) }}</text></view>
        <view class="r-row"><text>税费</text><text class="text-amber">{{ sym(result.currency) }}{{ fmt(result.tax) }}</text></view>
        <view class="r-row big"><text>税后到账</text><text class="text-emerald big">{{ sym(result.currency) }}{{ fmt(result.net_amount) }}</text></view>
        <view class="r-row" v-if="result.record_date_auto">
          <text class="text-muted">登记日为自动推断（A股=除权日前一天），如与实际不符可编辑修改</text>
        </view>
        <button class="btn-primary" style="margin-top: 30rpx" @click="done">完成</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { apiHoldings, apiCreateDividend } from '@/api'
import { currencyMap } from '@/utils/constants'

const today = new Date().toISOString().slice(0, 10)
const holdings = ref([])
const picked = ref(null)
const saving = ref(false)
const result = ref(null)
const form = reactive({
  ex_date: today, record_date: '', pay_date: today,
  dps: '', tax: '', status: 'confirmed',
})

const holdingNames = computed(() => holdings.value.map(h => `${h.name} (${h.code}) · ${h.shares_now}股`))
const pickedName = computed(() => {
  const h = holdings.value.find(x => x.id === picked.value)
  return h ? `${h.name} (${h.code}) · ${h.shares_now}股` : ''
})

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

async function loadHoldings(preselect) {
  const data = await apiHoldings()
  holdings.value = data.items
  if (preselect) picked.value = Number(preselect)
}

onLoad((q) => loadHoldings(q?.holding_id))

function onPickHolding(e) {
  picked.value = holdings.value[e.detail.value].id
}

async function submit() {
  if (!picked.value) return uni.showToast({ title: '请选择持仓', icon: 'none' })
  if (!form.dps || Number(form.dps) <= 0) return uni.showToast({ title: '请填写每股分红', icon: 'none' })
  saving.value = true
  try {
    const payload = {
      holding_id: picked.value,
      ex_date: form.ex_date,
      pay_date: form.pay_date,
      dps: Number(form.dps),
      status: form.status,
    }
    if (form.record_date) payload.record_date = form.record_date
    if (form.tax !== '') payload.tax = Number(form.tax)
    result.value = await apiCreateDividend(payload)
  } finally {
    saving.value = false
  }
}

function done() {
  result.value = null
  uni.navigateBack()
}
</script>

<style scoped>
.picker-val { text-align: right; font-size: 28rpx; color: #1e293b; }
.picker-val .text-muted, .text-muted { color: #94a3b8; font-size: 24rpx; }
.tip { font-size: 24rpx; color: #64748b; line-height: 1.7; background: #eff6ff; }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 99; display: flex; align-items: center; justify-content: center; }
.sheet { background: #fff; width: 600rpx; border-radius: 24rpx; padding: 40rpx; }
.sheet-title { font-size: 32rpx; font-weight: 700; text-align: center; margin-bottom: 24rpx; }
.r-row { display: flex; justify-content: space-between; padding: 16rpx 0; font-size: 28rpx; color: #475569; }
.r-bold { font-weight: 600; color: #1e293b; }
.r-row.big { font-size: 34rpx; border-top: 1rpx solid #f1f5f9; margin-top: 10rpx; padding-top: 24rpx; }
.big { font-size: 34rpx; font-weight: 700; }
</style>
