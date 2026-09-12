<template>
  <div>
    <!-- 年度分红总额 + 各市场累计分红 -->
    <div class="row-grid">
      <div class="card">
        <h3>年度分红总额</h3>
        <div ref="yearEl" class="chart-h300"></div>
      </div>
      <div class="card">
        <h3>各市场累计分红</h3>
        <div ref="marketEl" class="chart-h300"></div>
      </div>
    </div>

    <!-- Top10 + 股息率排行 -->
    <div class="row-grid mt20">
      <div class="card">
        <h3>持仓分红贡献 Top10</h3>
        <div ref="topEl" class="chart-h300"></div>
      </div>
      <div class="card">
        <div class="card-head">
          <h3>股息率排行（年化）</h3>
        </div>
        <el-table :data="yieldList" style="width: 100%" max-height="300">
          <el-table-column label="持仓" min-width="140">
            <template #default="{ row }">
              <span class="bold">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column label="市值" width="120" align="right">
            <template #default="{ row }">{{ fmtDisplay(row.market_value, row.display_currency) }}</template>
          </el-table-column>
          <el-table-column label="年分红" width="110" align="right">
            <template #default="{ row }">{{ fmtDisplay(row.year_dividend, row.display_currency) }}</template>
          </el-table-column>
          <el-table-column label="股息率(现价)" width="120" align="right">
            <template #default="{ row }">
              <span class="text-emerald bold">{{ row.yield_price ? (row.yield_price * 100).toFixed(2) + '%' : '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="股息率(TTM成本)" width="130" align="right">
            <template #default="{ row }">
              <span class="text-muted">{{ (row.yoc_ttm * 100).toFixed(2) }}%</span>
            </template>
          </el-table-column>
        </el-table>
        <p class="hint-text">TTM成本股息率 = 近12月每股分红 ÷ 你的加权平均成本，分批买入后成本被摊薄/抬高会实时反映</p>
      </div>
    </div>

    <!-- 成本股息率 vs 现价股息率 + 派息频率分布 -->
    <div class="row-grid mt20">
      <div class="card">
        <h3>成本股息率 vs 现价股息率</h3>
        <p class="hint-text">衡量「按买入成本躺收」的真实收益率（参考 Simply Safe Dividends）</p>
        <div ref="yieldEl" class="chart-h300"></div>
      </div>
      <div class="card">
        <h3>派息频率分布</h3>
        <p class="hint-text">月派越多，现金流越平滑；年派集中在特定月份</p>
        <div ref="freqEl" class="chart-h300"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { apiMonthlyTrend, apiByMarket, apiTopHoldings, apiYieldRanking, apiHoldings } from '../api'
import { fmtDisplay, marketMap, freqMap, currencyMap } from '../utils/constants'
import { useEchart } from '../utils/echart'
import { useUserStore } from '../store/user'

const userStore = useUserStore()

const yearEl = ref(null)
const marketEl = ref(null)
const topEl = ref(null)
const yieldEl = ref(null)
const freqEl = ref(null)
const yearOpt = ref({})
const marketOpt = ref({})
const topOpt = ref({})
const yieldOpt = ref({})
const freqOpt = ref({})
const yc = useEchart(yearEl, yearOpt)
const mc = useEchart(marketEl, marketOpt)
const tc = useEchart(topEl, topOpt)
const ylc = useEchart(yieldEl, yieldOpt)
const fc = useEchart(freqEl, freqOpt)

const yieldList = ref([])

onMounted(async () => {
  // v8：币种转换仅在总览看板生效，统计页按 CNY 显示
  const params = {}
  if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
    params.account = userStore.currentAccount
  }
  const [trend, market, top, yld, holdings] = await Promise.all([
    apiMonthlyTrend('24m', params), apiByMarket(params), apiTopHoldings(10, params),
    apiYieldRanking(params), apiHoldings(params),
  ])

  // 后端返回 display_currency=CNY（不传 display_currency 时默认）
  const dispCur = trend.display_currency || market.display_currency || 'CNY'
  const sym = currencyMap[dispCur]?.symbol || '¥'

  // 年度聚合
  const yearMap = {}
  trend.months?.forEach((mo, i) => {
    const y = mo.slice(0, 4)
    yearMap[y] = (yearMap[y] || 0) + (trend.amounts?.[i] || 0)
  })
  const years = Object.entries(yearMap).sort(([a], [b]) => a - b)
  yearOpt.value = {
    tooltip: { trigger: 'axis', valueFormatter: (v) => fmtDisplay(v, dispCur) },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: years.map(([y]) => y + '年') },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar', data: years.map(([, v]) => Number(v.toFixed(2))), barMaxWidth: 44,
      itemStyle: { color: '#10b981', borderRadius: [6, 6, 0, 0] },
    }],
  }
  yc.render()

  // 各市场累计分红（横向条形，更接近原型 bar 形态）
  const mItems = (market.items || [])

  marketOpt.value = {
    tooltip: { trigger: 'axis', formatter: `{b}: ${sym}{c}` },
    grid: { left: 80, right: 30, top: 20, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: mItems.map((m) => marketMap[m.market]?.label || m.market) },
    series: [{
      type: 'bar', data: mItems.map((m) => Number((m.amount || 0).toFixed(2))), barMaxWidth: 24,
      itemStyle: { color: '#3b82f6', borderRadius: [0, 6, 6, 0] },
      label: { show: true, position: 'right', formatter: `${sym}{c}` },
    }],
  }
  mc.render()

  // Top10 横向条形
  const tops = (top.items || []).slice(0, 10).reverse()
  topOpt.value = {
    tooltip: { trigger: 'axis', formatter: `{b}: ${sym}{c}` },
    grid: { left: 110, right: 40, top: 10, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: tops.map((t) => t.name), axisLabel: { fontSize: 12 } },
    series: [{
      type: 'bar', data: tops.map((t) => Number(t.amount)), barMaxWidth: 18,
      itemStyle: { color: '#3b82f6', borderRadius: [0, 6, 6, 0] },
    }],
  }
  tc.render()

  // 股息率排行表格
  yieldList.value = (yld.items || []).slice(0, 10)

  // 成本股息率 vs 现价股息率（双柱状图）
  const yItems = (yld.items || []).slice(0, 10)
  yieldOpt.value = {
    tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '-' : v + '%') },
    legend: { data: ['股息率(TTM成本)', '股息率(现价)'], top: 0 },
    grid: { left: 40, right: 20, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: yItems.map((y) => y.name), axisLabel: { interval: 0, rotate: 30, fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: '股息率(TTM成本)', type: 'bar',
        itemStyle: { color: '#059669', borderRadius: [4, 4, 0, 0] },
        data: yItems.map((y) => Number(((y.yoc_ttm || 0) * 100).toFixed(2))),
        label: { show: true, position: 'top', formatter: '{c}%', fontSize: 10 },
      },
      {
        name: '股息率(现价)', type: 'bar',
        itemStyle: { color: '#94a3b8', borderRadius: [4, 4, 0, 0] },
        data: yItems.map((y) => Number(((y.yield_price || 0) * 100).toFixed(2))),
      },
    ],
  }
  ylc.render()

  // 派息频率分布（环形饼图）
  const freqCount = {}
  ;(holdings.items || holdings || []).forEach((h) => {
    const f = h.freq || 'irregular'
    freqCount[f] = (freqCount[f] || 0) + 1
  })
  const colorMap = { monthly: '#f59e0b', quarterly: '#3b82f6', semi_annual: '#10b981', annual: '#1e3a8a', irregular: '#94a3b8' }
  const freqData = Object.entries(freqCount).map(([f, c]) => ({
    value: c, name: freqMap[f] || f, itemStyle: { color: colorMap[f] || '#94a3b8' },
  }))
  freqOpt.value = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 只 ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      label: { formatter: '{b}\n{c} 只' },
      data: freqData.length ? freqData : [{ value: 1, name: '暂无', itemStyle: { color: '#e2e8f0' } }],
    }],
  }
  fc.render()
})

onUnmounted(() => { yc.dispose(); mc.dispose(); tc.dispose(); ylc.dispose(); fc.dispose() })
</script>

<style scoped>
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 8px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { margin: 0; }
.hint-text { font-size: 12px; color: #94a3b8; margin: 0 0 12px; }
.chart-h300 { height: 300px; }
.row-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.mt20 { margin-top: 20px; }
.bold { font-weight: 500; }
.text-emerald { color: #059669; }
.text-muted { color: #64748b; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
</style>
