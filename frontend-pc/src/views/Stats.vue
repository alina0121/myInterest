<template>
  <div>
    <!-- 年度分红总额 -->
    <div class="card">
      <div class="card-head">
        <h3>年度分红总额</h3>
        <span class="text-muted">税后折人民币</span>
      </div>
      <div ref="yearEl" class="chart-h300"></div>
    </div>

    <!-- 市场占比 + Top10 -->
    <div class="row-grid mt20">
      <div class="card">
        <h3>各市场累计分红</h3>
        <div ref="marketEl" class="chart-h300"></div>
      </div>
      <div class="card">
        <h3>持仓分红贡献 Top10</h3>
        <div ref="topEl" class="chart-h300"></div>
      </div>
    </div>

    <!-- 股息率排行 -->
    <div class="card mt20">
      <div class="card-head">
        <h3>股息率排行</h3>
        <span class="text-muted">成本股息率 = 近12月每股分红 ÷ 平均成本</span>
      </div>
      <el-table :data="yieldList" style="width: 100%">
        <el-table-column label="排名" width="70" align="center">
          <template #default="{ $index }">
            <span :class="['rank-num', $index < 3 ? 'rank-top' : '']">{{ $index + 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="持仓" min-width="180">
          <template #default="{ row }">
            <span class="bold">{{ row.name }}</span>
            <span class="text-muted" style="margin-left: 8px">{{ row.market ? (marketMap[row.market]?.label) : '' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="持仓市值" width="140" align="right">
          <template #default="{ row }">{{ fmtCNY(row.market_value_cny) }}</template>
        </el-table-column>
        <el-table-column label="本年分红" width="130" align="right">
          <template #default="{ row }">{{ fmtCNY(row.year_dividend_cny) }}</template>
        </el-table-column>
        <el-table-column label="成本股息率" width="120" align="right">
          <template #default="{ row }">
            <span class="text-emerald bold">{{ (row.yoc_ttm * 100).toFixed(2) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="现价股息率" width="120" align="right">
          <template #default="{ row }">
            {{ row.yield_price ? (row.yield_price * 100).toFixed(2) + '%' : '-' }}
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!yieldList.length" class="empty-tip">暂无数据</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { apiMonthlyTrend, apiByMarket, apiTopHoldings, apiYieldRanking } from '../api'
import { fmtCNY, marketMap } from '../utils/constants'
import { useEchart } from '../utils/echart'

const yearEl = ref(null)
const marketEl = ref(null)
const topEl = ref(null)
const yearOpt = ref({})
const marketOpt = ref({})
const topOpt = ref({})
const yc = useEchart(yearEl, yearOpt)
const mc = useEchart(marketEl, marketOpt)
const tc = useEchart(topEl, topOpt)

const yieldList = ref([])

onMounted(async () => {
  const [trend, market, top, yld] = await Promise.all([
    apiMonthlyTrend('24m'), apiByMarket(), apiTopHoldings(10), apiYieldRanking(),
  ])

  // 年度聚合
  const yearMap = {}
  trend.months?.forEach((mo, i) => {
    const y = mo.slice(0, 4)
    yearMap[y] = (yearMap[y] || 0) + (trend.amounts_cny?.[i] || 0)
  })
  const years = Object.entries(yearMap).sort(([a], [b]) => a - b)
  yearOpt.value = {
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: years.map(([y]) => y + '年') },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar', data: years.map(([, v]) => Number(v.toFixed(2))), barMaxWidth: 44,
      itemStyle: { color: '#10b981', borderRadius: [6, 6, 0, 0] },
    }],
  }
  yc.render()

  // 市场占比
  const mItems = (market.items || []).map((m) => ({
    name: marketMap[m.market]?.label || m.market, value: Number(m.amount_cny),
  }))
  marketOpt.value = {
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
      label: { formatter: '{b}\n{d}%' }, data: mItems,
    }],
  }
  mc.render()

  // Top10 横向条形
  const tops = (top.items || []).slice(0, 10).reverse()
  topOpt.value = {
    tooltip: { trigger: 'axis', formatter: '{b}: ¥{c}' },
    grid: { left: 110, right: 40, top: 10, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: tops.map((t) => t.name), axisLabel: { fontSize: 12 } },
    series: [{
      type: 'bar', data: tops.map((t) => Number(t.amount_cny)), barMaxWidth: 18,
      itemStyle: { color: '#3b82f6', borderRadius: [0, 6, 6, 0] },
    }],
  }
  tc.render()

  yieldList.value = (yld.items || []).slice(0, 10)
})

onUnmounted(() => { yc.dispose(); mc.dispose(); tc.dispose() })
</script>

<style scoped>
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { margin: 0; }
.chart-h300 { height: 300px; }
.row-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.mt20 { margin-top: 20px; }
.rank-num {
  display: inline-flex; width: 24px; height: 24px; border-radius: 50%;
  background: #f1f5f9; color: #64748b; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
}
.rank-num.rank-top { background: #f59e0b; color: #fff; }
.bold { font-weight: 500; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
</style>
