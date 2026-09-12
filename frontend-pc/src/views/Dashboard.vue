<template>
  <div>
    <!-- ========== 深色主卡 ========== -->
    <div class="hero-card">
      <div class="hero-top">
        <div>
          <div class="hero-label">{{ mainMetricName }}</div>
          <div class="hero-value">
            <span v-if="mainMetric?.format === 'currency'" class="hero-currency">{{ curSymbol }}</span>
            {{ formatMetricValue(mainMetric, enhanced[mainMetricKey]) }}
          </div>
          <div class="hero-sub" v-if="enhanced.year_growth !== null && enhanced.year_growth !== undefined">
            <span :class="enhanced.year_growth >= 0 ? 'up' : 'down'">
              {{ enhanced.year_growth >= 0 ? '↑' : '↓' }}
              {{ Math.abs(enhanced.year_growth * 100).toFixed(1) }}%
            </span>
            较去年同期
          </div>
        </div>
        <div class="hero-actions">
          <!-- 币种切换：仅总览看板生效，聚合多币种持仓统一折算 -->
          <el-dropdown trigger="click" @command="onCurrencyChange">
            <div class="hero-edit">
              <span class="cur-symbol">{{ curSymbol }}</span>
              <span>{{ curLabel }}</span>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="c in currencyOptions" :key="c.value"
                                  :command="c.value"
                                  :class="{ 'is-active': userStore.displayCurrency === c.value }">
                  {{ c.label }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div class="hero-edit" @click="showSettings = true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            自定义指标
          </div>
        </div>
      </div>

      <!-- 指标网格 -->
      <div class="metric-grid">
        <div
          v-for="(key, idx) in selectedMetrics"
          :key="key"
          class="metric-item"
          :class="{ 'metric-item--main': idx === 0 }"
          @click="idx === 0 ? null : setMainMetric(key)"
        >
          <div class="metric-label">{{ getMetricDef(key)?.name }}</div>
          <div class="metric-value" :class="valueColorClass(key, enhanced[key])">
            {{ formatMetricValue(getMetricDef(key), enhanced[key]) }}
          </div>
          <div class="metric-sub">{{ getMetricDef(key)?.desc }}</div>
        </div>
      </div>
    </div>

    <!-- ========== 图表区域 ========== -->
    <div class="row-grid mt24">
      <div class="card">
        <div class="card-head">
          <h3>未来 12 个月分红预测</h3>
          <span class="text-muted">已公告预案 + 历史派息推算</span>
        </div>
        <div ref="forecastEl" class="chart-h260"></div>
      </div>
      <div class="card">
        <h3>持仓快照</h3>
        <div class="info-list">
          <div class="info-row">
            <span class="label">持仓只数</span>
            <span class="value">{{ enhanced.holding_count || 0 }} 只</span>
          </div>
          <div class="info-row">
            <span class="label">累计收息</span>
            <span class="value">{{ fmtDisplay(enhanced.total_received, enhanced.display_currency) }}</span>
          </div>
          <div class="info-row">
            <span class="label">总市值</span>
            <span class="value">{{ enhanced.market_value > 0 ? fmtDisplay(enhanced.market_value, enhanced.display_currency) : '—' }}</span>
          </div>
          <div class="info-row">
            <span class="label">浮动盈亏</span>
            <span class="value" :class="pnlClass(enhanced.floating_pnl)">
              {{ enhanced.market_value > 0 ? (enhanced.floating_pnl >= 0 ? '+' : '-') + fmtDisplay(Math.abs(enhanced.floating_pnl), enhanced.display_currency) : '—' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">盈亏率</span>
            <span class="value" :class="pnlClass(enhanced.pnl_rate)">
              {{ enhanced.pnl_rate !== null && enhanced.pnl_rate !== undefined ? (enhanced.pnl_rate >= 0 ? '+' : '') + (enhanced.pnl_rate * 100).toFixed(2) + '%' : '—' }}
            </span>
          </div>
          <div class="info-row">
            <span class="label">净投入</span>
            <span class="value">{{ fmtDisplay(enhanced.net_investment, enhanced.display_currency) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 分红趋势 + 市场占比 -->
    <div class="row-grid mt20">
      <div class="card">
        <div class="card-head">
          <h3>分红趋势（近 12 个月）</h3>
          <el-select v-model="trendRange" size="small" style="width: 130px" @change="loadTrend">
            <el-option label="近 12 个月" value="12m" />
            <el-option label="近 24 个月" value="24m" />
          </el-select>
        </div>
        <div ref="trendEl" class="chart-h300"></div>
      </div>
      <div class="card">
        <h3>各市场分红占比</h3>
        <div ref="marketEl" class="chart-h300"></div>
      </div>
    </div>

    <!-- ========== 指标设置弹窗 ========== -->
    <el-dialog
      v-model="showSettings"
      title="汇总指标设置"
      width="520px"
      :close-on-click-modal="false"
      :append-to-body="true"
    >
      <div class="setting-hint">
        <span>已选 {{ tempSelected.length }} / {{ maxSelect }} · 点击可加入或取消</span>
        <span class="hint-tip">提示：第 1 个为主指标，显示在主卡顶部大字</span>
      </div>

      <!-- 已选指标 -->
      <div class="setting-group-title">已选指标（{{ tempSelected.length }}）</div>
      <div class="metric-setting-list">
        <div
          v-for="(key, idx) in tempSelected"
          :key="key"
          class="metric-setting-row selected"
          @click="tempSelected.splice(idx, 1)"
        >
          <div class="metric-setting-num">{{ idx + 1 }}</div>
          <div class="metric-setting-info">
            <div class="metric-setting-name">
              {{ getMetricDef(key)?.name }}
              <span v-if="idx === 0" class="main-tag">主指标</span>
            </div>
            <div class="metric-setting-desc">{{ getMetricDef(key)?.desc }}</div>
          </div>
          <div class="metric-setting-val">{{ formatMetricValue(getMetricDef(key), enhanced[key]) }}</div>
        </div>
      </div>

      <!-- 可选指标 -->
      <div class="setting-group-title">可选指标（{{ availableMetrics.length }}）</div>
      <div class="metric-setting-list">
        <div
          v-for="m in availableMetrics"
          :key="m.key"
          class="metric-setting-row available"
          @click="addMetric(m.key)"
        >
          <div class="metric-setting-plus">+</div>
          <div class="metric-setting-info">
            <div class="metric-setting-name">{{ m.name }}</div>
            <div class="metric-setting-desc">{{ m.desc }}</div>
          </div>
          <div class="metric-setting-val">{{ formatMetricValue(m, enhanced[m.key]) }}</div>
        </div>
        <div v-if="tempSelected.length >= maxSelect" class="metric-setting-empty">
          已达最大可选数量（{{ maxSelect }}），请先取消不需要的指标
        </div>
      </div>

      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveMetrics">确认保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  apiEnhancedSummary, apiDashboardMetrics, apiSaveDashboardMetrics,
  apiMonthlyTrend, apiByMarket, apiDividends, apiUpcoming, apiSaveSettings,
} from '../api'
import { fmt, fmtDisplay, currencyMap, marketMap } from '../utils/constants'
import { useEchart } from '../utils/echart'
import { useUserStore } from '../store/user'

const userStore = useUserStore()

// ---------- 数据 ----------
const enhanced = ref({})
const registry = ref([])
const selectedMetrics = ref([])        // 用户已选（持久化）
const tempSelected = ref([])           // 设置弹窗中的临时副本
const maxSelect = ref(9)
const showSettings = ref(false)
const trendRange = ref('12m')

const forecastEl = ref(null)
const trendEl = ref(null)
const marketEl = ref(null)
const forecastOpt = ref({})
const trendOpt = ref({})
const marketOpt = ref({})
const fc = useEchart(forecastEl, forecastOpt)
const tr = useEchart(trendEl, trendOpt)
const mk = useEchart(marketEl, marketOpt)

// ---------- 计算属性 ----------
// v8：当前显示币种符号（¥ / $ / HK$），跟随 userStore.displayCurrency
const curSymbol = computed(() => {
  const c = currencyMap[userStore.displayCurrency]
  return c?.symbol || '¥'
})
// 币种切换下拉的标签
const curLabel = computed(() => {
  const labels = { CNY: '人民币', USD: '美元', HKD: '港币', ORIGINAL: '本币' }
  return labels[userStore.displayCurrency] || '人民币'
})
// 币种选项（仅总览看板用，其他页按原币种显示）
const currencyOptions = [
  { value: 'CNY', label: '¥ 人民币（统一折算）' },
  { value: 'USD', label: '$ 美元' },
  { value: 'HKD', label: 'HK$ 港币' },
  { value: 'ORIGINAL', label: '本币（按原币种）' },
]
// 切换币种后重新加载数据（仅总览看板生效，持久化到后端）
async function onCurrencyChange(cur) {
  userStore.setDisplayCurrency(cur)
  try { await apiSaveSettings({ display_currency: cur }) } catch (e) { /* 静默 */ }
  await loadAll()
}
const mainMetricKey = computed(() => selectedMetrics.value[0] || 'forecast_year')
const mainMetric = computed(() => getMetricDef(mainMetricKey.value))
const mainMetricName = computed(() => mainMetric.value?.name || '预测年度分红')

// 设置弹窗中未选的指标
const availableMetrics = computed(() => {
  const sel = new Set(tempSelected.value)
  return registry.value.filter((m) => !sel.has(m.key))
})

// ---------- 指标工具 ----------
function getMetricDef(key) {
  return registry.value.find((m) => m.key === key)
}

function formatMetricValue(def, val) {
  if (val === null || val === undefined || val === 0) return '—'
  if (!def) return fmt(val)
  // v8：货币类按当前显示币种带符号
  const dispCur = enhanced.value.display_currency || 'CNY'
  switch (def.format) {
    case 'currency': return fmtDisplay(val, dispCur)
    case 'percent': return (val * 100).toFixed(2) + '%'
    case 'number': return val + ' 只'
    default: return fmt(val)
  }
}

function valueColorClass(key, val) {
  if (val === null || val === undefined || val === 0) return ''
  // 盈亏类：正值绿色，负值红色（字段名已去掉 _cny 后缀）
  if (key === 'floating_pnl' || key === 'pnl_rate') {
    return val >= 0 ? 'positive' : 'negative'
  }
  return ''
}

function pnlClass(val) {
  if (val === null || val === undefined || val === 0) return ''
  return val >= 0 ? 'positive' : 'negative'
}

// ---------- 指标设置 ----------
function setMainMetric(key) {
  // 将该指标移到第一位
  const idx = selectedMetrics.value.indexOf(key)
  if (idx > 0) {
    selectedMetrics.value.splice(idx, 1)
    selectedMetrics.value.unshift(key)
  }
}

watch(showSettings, (v) => {
  if (v) {
    tempSelected.value = [...selectedMetrics.value]
  }
})

function addMetric(key) {
  if (tempSelected.value.length >= maxSelect.value) return
  tempSelected.value.push(key)
}

async function saveMetrics() {
  if (!tempSelected.value.length) return
  await apiSaveDashboardMetrics(tempSelected.value)
  selectedMetrics.value = [...tempSelected.value]
  showSettings.value = false
}

// ---------- 图表 ----------
async function loadTrend() {
  // v8：账户跟随 + 显示币种转换
  const params = {}
  if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
    params.account = userStore.currentAccount
  }
  if (userStore.displayCurrency && userStore.displayCurrency !== 'CNY') {
    params.display_currency = userStore.displayCurrency
  }
  const t = await apiMonthlyTrend(trendRange.value, params)
  // v8：后端统一返回固定字段 amounts，附带 display_currency 标识
  trendOpt.value = {
    tooltip: { trigger: 'axis', valueFormatter: (v) => fmtDisplay(v, t.display_currency || 'CNY') },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: t.months, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar', data: t.amounts || [], barMaxWidth: 28,
      itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
    }],
  }
  tr.render()
}

function renderForecast(f) {
  forecastOpt.value = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['已公告', '推算预估'], top: 0 },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: f.forecast_months || f.months, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [
      { name: '已公告', type: 'bar', stack: 'total', data: f.forecast_published || f.published, itemStyle: { color: '#10b981' }, barMaxWidth: 28 },
      { name: '推算预估', type: 'bar', stack: 'total', data: f.forecast_estimated || f.estimated, itemStyle: { color: '#93c5fd', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 28 },
    ],
  }
  fc.render()
}

function renderMarket(items) {
  // v8：后端统一返回固定字段 amount，用 display_currency 决定符号
  const dispCur = enhanced.value.display_currency || 'CNY'
  const sym = currencyMap[dispCur]?.symbol || '¥'
  marketOpt.value = {
    tooltip: { trigger: 'item', formatter: `{b}: ${sym}{c} ({d}%)` },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      label: { formatter: '{b}\n{d}%' },
      data: items.map((m) => ({
        name: marketMap[m.market]?.label || m.market,
        value: Number(m.amount),
      })),
    }],
  }
  mk.render()
}

// ---------- 加载 ----------
// v8：币种转换仅在总览看板生效，其他页按原币种显示
async function loadAll() {
  const params = {}
  if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
    params.account = userStore.currentAccount
  }
  if (userStore.displayCurrency && userStore.displayCurrency !== 'CNY') {
    params.display_currency = userStore.displayCurrency
  }
  const [enh, fm, mkData] = await Promise.all([
    apiEnhancedSummary(params),
    apiDashboardMetrics(),
    apiByMarket(params),
    loadTrend(),
  ])
  enhanced.value = enh
  registry.value = fm.registry
  selectedMetrics.value = fm.selected
  maxSelect.value = fm.max_select

  renderForecast(enh)
  renderMarket(mkData.items || [])
}

onMounted(() => loadAll())

onUnmounted(() => { fc.dispose(); tr.dispose(); mk.dispose() })
</script>

<style scoped>
/* ========== 深色主卡 ========== */
.hero-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 16px;
  padding: 32px;
  color: #fff;
  position: relative;
  overflow: hidden;
}
.hero-card::before {
  content: '';
  position: absolute;
  top: -50%; right: -20%;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(255,165,0,0.15) 0%, transparent 70%);
  border-radius: 50%;
  pointer-events: none;
}
.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 28px;
  position: relative;
  z-index: 1;
}
.hero-label {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  letter-spacing: 2px;
}
.hero-value {
  font-size: 48px;
  font-weight: 700;
  letter-spacing: 1px;
  margin-top: 6px;
}
.hero-currency {
  font-size: 20px;
  font-weight: 400;
  margin-right: 4px;
  opacity: 0.7;
}
.hero-sub {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  margin-top: 4px;
}
.hero-sub .up { color: #4ade80; margin-right: 4px; }
.hero-sub .down { color: #f87171; margin-right: 4px; }

.hero-edit {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(255,255,255,0.6);
  cursor: pointer;
  padding: 8px 14px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.2);
  transition: all 0.2s;
  z-index: 1;
  white-space: nowrap;
  outline: none;
}
.hero-edit:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
}
.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 1;
}
.cur-symbol {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255,255,255,0.9);
}

/* 指标网格：自适应 3~4 列 */
.metric-grid {
  display: grid;
  gap: 0;
  position: relative;
  z-index: 1;
}
/* 1~2 个指标：每行 1 个 */
.metric-grid:has(> .metric-item:nth-child(1):last-child) { grid-template-columns: repeat(1, 1fr); }
.metric-grid:has(> .metric-item:nth-child(2):last-child) { grid-template-columns: repeat(2, 1fr); }
/* 3 个：每行 3 个 */
.metric-grid:has(> .metric-item:nth-child(3):last-child) { grid-template-columns: repeat(3, 1fr); }
/* 4+ 个：每行 3 个，自动换行 */
.metric-grid:not(:has(> .metric-item:nth-child(1):last-child)):not(:has(> .metric-item:nth-child(2):last-child)):not(:has(> .metric-item:nth-child(3):last-child)) { grid-template-columns: repeat(3, 1fr); }

.metric-item {
  padding: 18px 12px;
  border-top: 1px solid rgba(255,255,255,0.1);
  cursor: pointer;
  transition: background 0.15s;
}
.metric-item:hover {
  background: rgba(255,255,255,0.04);
}
/* 同一行内非首列加左边框分隔 */
.metric-item:not(:nth-child(3n+1)):not(:first-child) {
  border-left: 1px solid rgba(255,255,255,0.06);
}
.metric-label {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  margin-bottom: 6px;
}
.metric-value {
  font-size: 22px;
  font-weight: 600;
  color: #fff;
}
.metric-value.positive { color: #4ade80; }
.metric-value.negative { color: #f87171; }
.metric-sub {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  margin-top: 4px;
}

/* ========== 原有卡片区 ========== */
.row-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
.mt20 { margin-top: 20px; }
.mt24 { margin-top: 24px; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { margin: 0; }
.chart-h260 { height: 260px; }
.chart-h300 { height: 300px; }

/* 持仓快照 */
.info-list { display: flex; flex-direction: column; }
.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;
}
.info-row:last-child { border-bottom: none; }
.info-row .label { color: #999; }
.info-row .value { font-weight: 500; color: #333; }
.info-row .value.positive { color: #16a34a; }
.info-row .value.negative { color: #dc2626; }

.text-muted { color: #94a3b8; font-size: 12px; }

/* ========== 设置弹窗 ========== */
.setting-hint {
  background: #f8f8f8;
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #666;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hint-tip { font-size: 11px; color: #999; }

.setting-group-title {
  font-size: 13px;
  color: #999;
  margin: 16px 0 8px;
}
.metric-setting-list {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
}
.metric-setting-row {
  display: flex;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #f5f5f5;
  cursor: pointer;
  transition: background 0.15s;
}
.metric-setting-row:last-child { border-bottom: none; }
.metric-setting-row:hover { background: #fafafa; }
.metric-setting-row.selected { background: #fafafa; }
.metric-setting-num {
  width: 26px;
  height: 26px;
  background: #1a1a2e;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  margin-right: 12px;
  flex-shrink: 0;
}
.metric-setting-plus {
  width: 26px;
  height: 26px;
  background: #f0f0f0;
  color: #999;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-right: 12px;
  flex-shrink: 0;
}
.metric-setting-info { flex: 1; min-width: 0; }
.metric-setting-name {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
}
.metric-setting-name .main-tag {
  display: inline-block;
  font-size: 11px;
  color: #1a1a2e;
  background: #fef3c7;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 6px;
  font-weight: 400;
}
.metric-setting-desc {
  font-size: 12px;
  color: #999;
  margin-top: 2px;
}
.metric-setting-val {
  font-size: 13px;
  color: #1a1a1a;
  font-weight: 500;
  white-space: nowrap;
  margin-left: 12px;
}
.metric-setting-empty {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}
</style>
