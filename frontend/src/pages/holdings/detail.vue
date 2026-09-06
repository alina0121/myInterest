<template>
  <view class="page">
    <!-- 持仓头部 -->
    <view class="hero">
      <view class="hero-top">
        <text class="tag" :style="{ background: marketMap[h.market]?.color }">{{ marketMap[h.market]?.label }}</text>
        <text class="hero-name">{{ h.name }}</text>
        <text class="hero-code">{{ h.code }}</text>
      </view>
      <view class="hero-stats">
        <view class="hs-cell">
          <view class="hs-val">{{ h.shares_now }}</view>
          <view class="hs-label">持仓数量</view>
        </view>
        <view class="hs-cell">
          <view class="hs-val">{{ sym(h.currency) }}{{ fmt(h.avg_cost) }}</view>
          <view class="hs-label">平均成本</view>
        </view>
        <view class="hs-cell">
          <view class="hs-val">{{ (h.yoc_ttm * 100).toFixed(2) }}%</view>
          <view class="hs-label">TTM成本股息率</view>
        </view>
        <view class="hs-cell">
          <view class="hs-val">¥{{ fmt(h.year_dividend) }}</view>
          <view class="hs-label">今年分红</view>
        </view>
      </view>
    </view>

    <!-- Tab 切换 -->
    <view class="tabs">
      <view :class="['tab', tab === 'lots' ? 'on' : '']" @click="tab = 'lots'">买入批次 ({{ lots.length }})</view>
      <view :class="['tab', tab === 'divs' ? 'on' : '']" @click="tab = 'divs'">分红记录 ({{ divs.length }})</view>
    </view>

    <!-- 批次列表 -->
    <block v-if="tab === 'lots'">
      <view v-for="l in lots" :key="l.id" class="card lot-card">
        <view class="lot-head">
          <text class="tag" :style="{ background: directionMap[l.direction]?.color }">{{ directionMap[l.direction]?.label }}</text>
          <text class="lot-date">{{ l.trade_date }}</text>
          <text class="lot-amt" :class="l.direction === 'sell' ? 'text-income' : ''">{{ sym(h.currency) }}{{ fmt(l.amount) }}</text>
        </view>
        <view class="lot-grid">
          <text>{{ l.shares }} 股</text>
          <text>单价 {{ sym(h.currency) }}{{ fmt(l.price) }}</text>
          <text v-if="l.direction === 'buy'">费用 {{ sym(h.currency) }}{{ fmt(l.fee) }}</text>
          <text v-if="l.lot_dividend > 0" class="text-income">累计收息 ¥{{ fmt(l.lot_dividend) }}</text>
        </view>
      </view>
      <view style="padding: 10rpx 24rpx">
        <button class="btn-primary" @click="openLot">＋ 添加批次</button>
      </view>
    </block>

    <!-- 分红列表 -->
    <block v-if="tab === 'divs'">
      <view v-if="!divs.length" class="empty card">暂无分红记录</view>
      <view v-for="d in divs" :key="d.id" class="card div-card" @click="toggle(d.id)">
        <view class="div-head">
          <text class="div-date">{{ d.pay_date }} 派息</text>
          <text class="tag" :style="{ background: d.status === 'confirmed' ? '#16a34a' : '#f59e0b' }">
            {{ d.status === 'confirmed' ? '已到账' : '预告' }}
          </text>
        </view>
        <view class="div-grid">
          <text>每股 {{ sym(d.currency) }}{{ fmt(d.dps) }}</text>
          <text>参与 {{ d.shares }} 股</text>
          <text>税前 {{ sym(d.currency) }}{{ fmt(d.gross_amount) }}</text>
          <text class="text-pending" v-if="d.tax > 0">税 {{ sym(d.currency) }}{{ fmt(d.tax) }}</text>
          <text class="text-income">到账 {{ sym(d.currency) }}{{ fmt(d.net_amount) }}</text>
        </view>
        <!-- 批次归属明细 -->
        <view v-if="openId === d.id && d.allocations && d.allocations.length" class="alloc">
          <view class="alloc-title">批次归属明细</view>
          <view v-for="(a, i) in d.allocations" :key="i" class="alloc-row">
            <text>{{ a.lot_date }} 买入的批次</text>
            <text>{{ a.shares }} 股</text>
            <text class="text-income">{{ sym(d.currency) }}{{ fmt(a.net) }}</text>
          </view>
        </view>
        <view v-else-if="openId === d.id" class="alloc">
          <view class="alloc-title text-muted">暂无归属明细</view>
        </view>
      </view>
    </block>

    <!-- 添加批次弹层 -->
    <view v-if="showLot" class="mask" @click="showLot = false">
      <view class="sheet" @click.stop>
        <view class="sheet-title">添加批次</view>
        <view class="form-row">
          <text class="form-label">类型</text>
          <picker :range="dirLabels" @change="e => lotForm.direction = DIRS[e.detail.value].value">
            <view class="picker-val">{{ dirLabel }}</view>
          </picker>
        </view>
        <view class="form-row">
          <text class="form-label">日期</text>
          <picker mode="date" :value="lotForm.trade_date" @change="e => lotForm.trade_date = e.detail.value">
            <view class="picker-val">{{ lotForm.trade_date }}</view>
          </picker>
        </view>
        <view class="form-row">
          <text class="form-label">数量</text>
          <input class="form-input" type="digit" v-model="lotForm.shares" placeholder="股数" />
        </view>
        <view class="form-row">
          <text class="form-label">成交价</text>
          <input class="form-input" type="digit" v-model="lotForm.price" placeholder="买入必填，卖出为卖出价，送转填 0" />
        </view>
        <view class="form-row">
          <text class="form-label">手续费</text>
          <input class="form-input" type="digit" v-model="lotForm.fee" placeholder="默认 0" />
        </view>
        <button class="btn-primary" style="margin-top: 30rpx" :loading="saving" @click="saveLot">保 存</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { apiHoldingDetail, apiLots, apiDividends, apiCreateLot } from '@/api'
import { marketMap, currencyMap, directionMap, DIRECTIONS as DIRS } from '@/utils/constants'

const id = ref(null)
const h = ref({})
const lots = ref([])
const divs = ref([])
const tab = ref('lots')
const openId = ref(null)
const showLot = ref(false)
const saving = ref(false)
const today = new Date().toISOString().slice(0, 10)
const lotForm = reactive({ trade_date: today, direction: 'buy', shares: '', price: '', fee: '' })

const dirLabels = DIRS.map(d => d.label)
const dirLabel = computed(() => DIRS.find(d => d.value === lotForm.direction)?.label)

function fmt(n) {
  return Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}
function sym(c) { return currencyMap[c]?.symbol || '' }

async function load() {
  h.value = await apiHoldingDetail(id.value)
  const [l, d] = await Promise.all([
    apiLots(id.value),
    apiDividends({ holding_id: id.value, page_size: 50, expand: 'allocations' }),
  ])
  lots.value = l.items
  divs.value = d.items
}

onLoad((q) => { id.value = Number(q.id) })
onShow(() => { if (id.value) load() })

function toggle(did) { openId.value = openId.value === did ? null : did }
function openLot() {
  Object.assign(lotForm, { trade_date: today, direction: 'buy', shares: '', price: '', fee: '' })
  showLot.value = true
}
async function saveLot() {
  if (!lotForm.shares || (lotForm.direction !== 'bonus_share' && !lotForm.price)) {
    return uni.showToast({ title: '请填写数量和价格（送转价格可为 0）', icon: 'none' })
  }
  saving.value = true
  try {
    await apiCreateLot(id.value, {
      trade_date: lotForm.trade_date,
      direction: lotForm.direction,
      shares: Number(lotForm.shares),
      price: Number(lotForm.price || 0),
      fee: Number(lotForm.fee || 0),
    })
    showLot.value = false
    uni.showToast({ title: '已保存，分红已自动重算', icon: 'none' })
    await load()
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.hero {
  background: linear-gradient(135deg, #1668dc, #3b82f6);
  margin: 20rpx 24rpx; border-radius: 20rpx; padding: 30rpx; color: #fff;
}
.hero-top { display: flex; align-items: center; gap: 12rpx; flex-wrap: wrap; }
.hero-name { font-size: 36rpx; font-weight: 700; }
.hero-code { font-size: 24rpx; opacity: 0.8; }
.hero-stats { display: flex; margin-top: 30rpx; }
.hs-cell { flex: 1; }
.hs-val { font-size: 30rpx; font-weight: 700; }
.hs-label { font-size: 20rpx; opacity: 0.8; margin-top: 8rpx; }
.tabs { display: flex; background: #fff; margin: 0 24rpx; border-radius: 16rpx; overflow: hidden; }
.tab { flex: 1; text-align: center; padding: 26rpx 0; font-size: 28rpx; color: #64748b; }
.tab.on { color: #1668dc; font-weight: 600; border-bottom: 4rpx solid #1668dc; }
.lot-card { padding: 24rpx 28rpx; }
.lot-head { display: flex; align-items: center; gap: 16rpx; }
.lot-date { font-size: 26rpx; color: #475569; flex: 1; }
.lot-amt { font-size: 30rpx; font-weight: 600; }
.lot-grid { display: flex; gap: 28rpx; flex-wrap: wrap; margin-top: 16rpx; font-size: 24rpx; color: #64748b; }
.div-card { padding: 24rpx 28rpx; }
.div-head { display: flex; justify-content: space-between; align-items: center; }
.div-date { font-size: 28rpx; font-weight: 600; }
.div-grid { display: flex; gap: 24rpx; flex-wrap: wrap; margin-top: 14rpx; font-size: 24rpx; color: #64748b; }
.alloc { margin-top: 18rpx; background: #f8fafc; border-radius: 12rpx; padding: 18rpx 20rpx; }
.alloc-title { font-size: 24rpx; font-weight: 600; color: #475569; margin-bottom: 10rpx; }
.alloc-row { display: flex; justify-content: space-between; font-size: 24rpx; color: #64748b; padding: 6rpx 0; }
.mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 99;
  display: flex; align-items: flex-end;
}
.sheet {
  background: #fff; width: 100%; border-radius: 28rpx 28rpx 0 0;
  padding: 36rpx 40rpx 60rpx;
}
.sheet-title { font-size: 32rpx; font-weight: 700; text-align: center; margin-bottom: 10rpx; }
.picker-val { text-align: right; font-size: 28rpx; }
</style>
