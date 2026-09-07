<template>
  <div v-loading="loading">
    <!-- 统计卡 -->
    <div class="stat-grid">
      <div class="card stat-card">
        <div class="stat-label">用户总数</div>
        <div class="stat-value">{{ ov.user_total || 0 }}</div>
        <div class="stat-foot text-muted">7 日新增 {{ ov.new_users_7d || 0 }} · 30 日新增 {{ ov.new_users_30d_total || (ov.new_users_30d || []).reduce((a, b) => a + b, 0) }}</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">活跃用户</div>
        <div class="stat-value">{{ ov.dau || 0 }} <span class="stat-unit">/ {{ ov.mau || 0 }}</span></div>
        <div class="stat-foot text-muted">DAU / MAU</div>
      </div>
      <div class="card stat-card">
        <div class="stat-label">持仓 / 批次 / 分红</div>
        <div class="stat-value sm">
          {{ ov.holding_total || 0 }} / {{ ov.lot_total || 0 }} / {{ ov.dividend_total || 0 }}
        </div>
        <div class="stat-foot text-muted">全平台数据量</div>
      </div>
      <div class="card stat-card" :class="ov.schedule_pending ? 'stat-pending' : ''">
        <div class="stat-label">预案待审核</div>
        <div class="stat-value" :class="ov.schedule_pending ? 'text-amber' : ''">{{ ov.schedule_pending || 0 }}</div>
        <div class="stat-foot text-muted">已发布 {{ ov.schedule_published_total || 0 }} · 已驳回 {{ ov.schedule_rejected_total || 0 }}</div>
      </div>
    </div>

    <!-- 趋势图 + 预案来源 -->
    <div class="row-grid-3 mt20">
      <div class="card col-2">
        <h3>近 30 天新增用户 / 活跃趋势</h3>
        <div ref="trendEl" class="chart-h280"></div>
      </div>
      <div class="card">
        <h3>预案数据来源</h3>
        <div ref="srcEl" class="chart-h200"></div>
        <div class="src-detail">
          <div class="src-line"><span>🕷️ 爬虫今日采集</span><b>{{ ov.crawl_today?.fetched || 0 }} 条</b></div>
          <div class="src-line"><span>✅ 今日已发布</span><b class="text-emerald">{{ ov.crawl_today?.published || 0 }} 条</b></div>
          <div class="src-line"><span>⚠️ 低置信度待人工</span><b class="text-amber">{{ ov.crawl_today?.need_manual || 0 }} 条</b></div>
        </div>
      </div>
    </div>

    <!-- 爬虫与快捷操作 -->
    <div class="row-grid mt20">
      <div class="card">
        <div class="card-head">
          <h3>预案数据源</h3>
          <el-button type="primary" size="small" :loading="crawling" @click="crawl">立即爬取</el-button>
        </div>
        <div class="src-row"><span class="text-muted">今日已爬取</span><b>{{ ov.crawl_today?.fetched || 0 }} 条</b></div>
        <div class="src-row"><span class="text-muted">自动发布</span><b class="text-emerald">{{ ov.crawl_today?.published || 0 }} 条</b></div>
        <div class="src-row"><span class="text-muted">待人工审核</span><b class="text-amber">{{ ov.crawl_today?.need_manual || 0 }} 条</b></div>
        <p class="hint-text">数据源：东方财富分红送配接口，每日 08:05 / 18:05 自动爬取并匹配持仓用户</p>
      </div>
      <div class="card">
        <h3>快捷操作</h3>
        <div class="quick-btns">
          <el-button @click="$router.push('/admin/schedules')">预案审核</el-button>
          <el-button @click="$router.push('/admin/users')">用户管理</el-button>
          <el-button @click="$router.push('/admin/config')">汇率税率</el-button>
          <el-button @click="$router.push('/admin/notice')">发公告</el-button>
        </div>
        <p class="hint-text">安全提示：管理员对用户业务数据只读，所有写操作均记录操作日志</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiAdminOverview, apiAdminCrawl } from '../../api'
import { useEchart } from '../../utils/echart'

const ov = ref({})
const loading = ref(false)
const crawling = ref(false)

const trendEl = ref(null)
const srcEl = ref(null)
const trendOpt = ref({})
const srcOpt = ref({})
const tc = useEchart(trendEl, trendOpt)
const sc = useEchart(srcEl, srcOpt)

async function load() {
  loading.value = true
  try {
    ov.value = await apiAdminOverview()
    renderCharts()
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  // 近30天趋势：柱状(新增用户) + 折线(日活)
  const nu = ov.value.new_users_30d || []
  const da = ov.value.dau_30d || []
  const days = nu.map((_, i) => `D-${29 - i}`)
  trendOpt.value = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['新增用户', '日活'], top: 0 },
    grid: { left: 45, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: days, axisLabel: { interval: 4, fontSize: 11 } },
    yAxis: { type: 'value' },
    series: [
      { name: '新增用户', type: 'bar', itemStyle: { color: '#0f172a', borderRadius: [3, 3, 0, 0] }, data: nu, barMaxWidth: 12 },
      { name: '日活', type: 'line', smooth: true, itemStyle: { color: '#f59e0b' }, lineStyle: { width: 2 }, data: da },
    ],
  }
  tc.render()

  // 预案来源饼图
  const ct = ov.value.crawl_today || {}
  const srcData = [
    { value: ct.published || 0, name: '已发布', itemStyle: { color: '#10b981' } },
    { value: ct.need_manual || 0, name: '待人工', itemStyle: { color: '#f59e0b' } },
    { value: Math.max(0, (ct.fetched || 0) - (ct.published || 0) - (ct.need_manual || 0)), name: '其他', itemStyle: { color: '#94a3b8' } },
  ].filter((d) => d.value > 0)
  srcOpt.value = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 条 ({d}%)' },
    series: [{
      type: 'pie', radius: ['50%', '72%'],
      data: srcData.length ? srcData : [{ value: 1, name: '暂无', itemStyle: { color: '#e2e8f0' } }],
      label: { fontSize: 11, formatter: '{b}\n{c} 条' },
    }],
  }
  sc.render()
}

async function crawl() {
  crawling.value = true
  try {
    const r = await apiAdminCrawl()
    ElMessage.success(`爬取完成：${r.fetched || 0} 条 fetched`)
    load()
  } catch (e) { /* toast 已统一 */ } finally { crawling.value = false }
}

onMounted(load)
onUnmounted(() => { tc.dispose(); sc.dispose() })
</script>

<style scoped>
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.stat-label { font-size: 13px; color: #64748b; }
.stat-value { font-size: 28px; font-weight: 700; margin: 8px 0; }
.stat-value.sm { font-size: 20px; }
.stat-unit { font-size: 14px; color: #94a3b8; font-weight: 400; }
.stat-foot { font-size: 12px; }
.stat-pending { border: 2px solid #fcd34d; }
.row-grid-3 { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
.row-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.col-2 { }
.mt20 { margin-top: 20px; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { margin: 0; }
.src-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f8fafc; font-size: 14px; }
.quick-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.quick-btns .el-button { margin: 0; }
.chart-h280 { height: 280px; }
.chart-h200 { height: 200px; }
.src-detail { margin-top: 12px; }
.src-line { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; color: #64748b; }
.hint-text { font-size: 12px; color: #94a3b8; margin-top: 12px; }
.text-muted { color: #64748b; }
.text-emerald { color: #059669; }
.text-amber { color: #d97706; }
</style>
