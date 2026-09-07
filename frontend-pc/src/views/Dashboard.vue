<template>
  <div>
    <!-- 统计卡片 -->
    <div class="stat-grid">
      <div class="card stat-card">
        <div class="stat-label">{{ year }} 年度分红</div>
        <div class="stat-value">{{ fmtCNY(summary.year_dividend_cny) }}</div>
        <div class="stat-foot" :class="growth >= 0 ? 'text-emerald' : 'text-amber'">
          {{ growth === null ? '暂无同比数据' : `${growth >= 0 ? '↑' : '↓'} ${Math.abs(growth * 100).toFixed(1)}% 较去年` }}
        </div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">本月到账</div>
        <div class="stat-value">{{ fmtCNY(summary.month_dividend_cny) }}</div>
        <div class="stat-foot text-muted">{{ summary.month_count || 0 }} 笔分红</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">累计分红总额</div>
        <div class="stat-value">{{ fmtCNY(summary.total_dividend_cny) }}</div>
        <div class="stat-foot text-muted">{{ summary.since_year ? `自 ${summary.since_year} 年起` : '暂无记录' }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">持仓数量</div>
        <div class="stat-value">{{ summary.holding_count || 0 }} 只</div>
        <div class="stat-foot text-muted">{{ marketDist }}</div>
      </div>
    </div>

    <!-- 未来12个月预测 + 派息节奏 -->
    <div class="row-grid mt20">
      <div class="card">
        <div class="card-head">
          <h3>未来 12 个月分红预测</h3>
          <span class="text-muted">已公告预案 + 近 12 个月派息推算</span>
        </div>
        <div ref="forecastEl" class="chart-h260"></div>
      </div>
      <div class="card">
        <h3>派息节奏</h3>
        <div class="freq-row" v-for="f in freqRows" :key="f.label">
          <span class="text-muted">{{ f.label }}</span><span class="freq-val">{{ f.count }} 只</span>
        </div>
        <div class="freq-divider"></div>
        <div class="text-muted">TTM 分红（近 12 个月已到账）</div>
        <div class="ttm-val text-emerald">{{ fmtCNY(summary.year_dividend_cny) }}</div>
        <div class="text-muted">下月预告 {{ fmtCNY(summary.next_month_forecast_cny) }}</div>
        <div class="text-muted" v-if="summary.year_dividend_cny > 0">折合月均 {{ fmtCNY(summary.year_dividend_cny / 12) }}</div>
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

    <!-- 最近到账 + 即将到账 -->
    <div class="row-grid mt20">
      <div class="card">
        <h3>最近到账分红</h3>
        <div v-if="!recent.length" class="empty-tip">暂无分红记录</div>
        <div v-for="(d, i) in recent" :key="d.id" :class="['recent-row', i < recent.length - 1 ? 'bordered' : '']">
          <div>
            <div class="recent-name">{{ d.holding_name }} ({{ d.code }})</div>
            <div class="text-muted">{{ d.pay_date }} 派息</div>
          </div>
          <div class="text-right">
            <div class="recent-amt text-emerald">+{{ sym(d.currency) }}{{ fmt(d.net_amount) }}</div>
            <div class="text-muted">{{ d.shares }} 股 × {{ sym(d.currency) }}{{ fmt(d.dps) }}</div>
          </div>
        </div>
      </div>
      <div class="card">
        <h3>即将到账分红</h3>
        <div v-if="!upcoming.length" class="empty-tip">暂无即将到账的分红</div>
        <div v-for="(u, i) in upcoming" :key="u.id" :class="['recent-row', i < upcoming.length - 1 ? 'bordered' : '']">
          <div>
            <div class="recent-name">{{ u.name }} ({{ u.code }})</div>
            <div class="text-amber">预计 {{ u.pay_date }} 到账（{{ u.days_to_pay }} 天后）</div>
          </div>
          <div class="text-right">
            <div class="recent-amt">约 {{ fmtCNY(u.est_net) }}</div>
            <div class="text-muted">{{ u.my_shares }} 股 × {{ sym(u.currency) }}{{ fmt(u.dps) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import {
  apiSummary, apiMonthlyTrend, apiByMarket, apiForecast, apiDividends, apiUpcoming,
} from '../api'
import { fmt, fmtCNY, currencyMap, marketMap, FREQS } from '../utils/constants'
import { useEchart } from '../utils/echart'

const year = new Date().getFullYear()
const summary = ref({})
const upcoming = ref([])
const recent = ref([])
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

const growth = computed(() => {
  const g = summary.value.year_growth
  return g === null || g === undefined ? null : Number(g)
})

const marketDist = computed(() => {
  const ms = summary.value.market_dist
  if (!ms) return ''
  return Object.entries(ms)
    .map(([k, v]) => `${marketMap[k]?.label || k} ${v}`)
    .join(' · ')
})

const freqRows = computed(() => {
  const fs = summary.value.freq_summary || {}
  return FREQS.filter((f) => fs[f.value]).map((f) => ({ label: f.label, count: fs[f.value] }))
})

function sym(c) { return currencyMap[c]?.symbol || '' }

async function loadTrend() {
  const t = await apiMonthlyTrend(trendRange.value)
  trendOpt.value = {
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: t.months, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar', data: t.amounts_cny, barMaxWidth: 28,
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
    xAxis: { type: 'category', data: f.months, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 } },
    series: [
      { name: '已公告', type: 'bar', stack: 'total', data: f.published, itemStyle: { color: '#10b981' }, barMaxWidth: 28 },
      { name: '推算预估', type: 'bar', stack: 'total', data: f.estimated, itemStyle: { color: '#93c5fd', borderRadius: [4, 4, 0, 0] }, barMaxWidth: 28 },
    ],
  }
  fc.render()
}

function renderMarket(items) {
  marketOpt.value = {
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      label: { formatter: '{b}\n{d}%' },
      data: items.map((m) => ({
        name: marketMap[m.market]?.label || m.market,
        value: Number(m.amount_cny),
      })),
    }],
  }
  mk.render()
}

onMounted(async () => {
  const [s, f, m, ups, rec] = await Promise.all([
    apiSummary(), apiForecast(), apiByMarket(), apiUpcoming(),
    apiDividends({ page: 1, page_size: 5, status: 'confirmed' }),
  ])
  summary.value = s
  renderForecast(f)
  renderMarket(m.items || [])
  upcoming.value = (ups.items || []).slice(0, 4)
  recent.value = rec.items || []
  loadTrend()
})

onUnmounted(() => { fc.dispose(); tr.dispose(); mk.dispose() })
</script>

<style scoped>
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.stat-label { font-size: 13px; color: #64748b; }
.stat-value { font-size: 28px; font-weight: 700; margin: 8px 0; }
.stat-foot { font-size: 12px; }
.row-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
.mt20 { margin-top: 20px; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { margin: 0; }
.chart-h260 { height: 260px; }
.chart-h300 { height: 300px; }
.freq-row { display: flex; justify-content: space-between; font-size: 14px; padding: 6px 0; }
.freq-val { font-weight: 500; }
.freq-divider { border-top: 1px solid #f1f5f9; margin: 12px 0; }
.ttm-val { font-size: 24px; font-weight: 700; margin: 4px 0; }
.recent-row { display: flex; align-items: center; justify-content: space-between; padding: 12px 0; }
.recent-row.bordered { border-bottom: 1px solid #f1f5f9; }
.recent-name { font-weight: 500; }
.recent-amt { font-weight: 600; }
.text-right { text-align: right; }
.empty-tip { color: #94a3b8; text-align: center; padding: 32px 0; font-size: 13px; }
</style>
