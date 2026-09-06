<template>
  <div v-loading="loading">
    <!-- 统计卡 -->
    <div class="stat-grid">
      <div class="card stat-card">
        <div class="stat-label">用户总数</div>
        <div class="stat-value">{{ ov.user_total || 0 }}</div>
        <div class="stat-foot text-muted">7 日新增 {{ ov.new_users_7d || 0 }} · 30 日新增 {{ ov.new_users_30d || 0 }}</div>
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
      <div class="card stat-card">
        <div class="stat-label">预案待审核</div>
        <div class="stat-value" :class="ov.schedule_pending ? 'text-amber' : ''">{{ ov.schedule_pending || 0 }}</div>
        <div class="stat-foot text-muted">已发布 {{ ov.schedule_published_total || 0 }} · 已驳回 {{ ov.schedule_rejected_total || 0 }}</div>
      </div>
    </div>

    <!-- 爬虫与预案 -->
    <div class="row-grid mt20">
      <div class="card">
        <div class="card-head">
          <h3>预案数据源</h3>
          <el-button type="primary" size="small" :loading="crawling" @click="crawl">立即爬取</el-button>
        </div>
        <div class="src-row"><span class="text-muted">今日已爬取</span><b>{{ ov.crawl_today?.fetched || 0 }} 条</b></div>
        <div class="src-row"><span class="text-muted">自动发布</span><b class="text-emerald">{{ ov.crawl_today?.published || 0 }} 条</b></div>
        <div class="src-row"><span class="text-muted">待人工审核</span><b class="text-amber">{{ ov.crawl_today?.need_manual || 0 }} 条</b></div>
        <p class="text-muted" style="font-size: 12px; margin-top: 12px">
          数据源：东方财富分红送配接口，每日 08:05 / 18:05 自动爬取并匹配持仓用户
        </p>
      </div>
      <div class="card">
        <h3>快捷操作</h3>
        <div class="quick-btns">
          <el-button @click="$router.push('/admin/schedules')">预案审核</el-button>
          <el-button @click="$router.push('/admin/users')">用户管理</el-button>
          <el-button @click="$router.push('/admin/config')">汇率税率</el-button>
          <el-button @click="$router.push('/admin/notice')">发公告</el-button>
        </div>
        <p class="text-muted" style="font-size: 12px; margin-top: 16px">
          安全提示：管理员对用户业务数据只读，所有写操作均记录操作日志
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiAdminOverview, apiAdminCrawl } from '../../api'

const ov = ref({})
const loading = ref(false)
const crawling = ref(false)

async function load() {
  loading.value = true
  try {
    ov.value = await apiAdminOverview()
  } finally {
    loading.value = false
  }
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
</script>

<style scoped>
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }
.stat-label { font-size: 13px; color: #64748b; }
.stat-value { font-size: 28px; font-weight: 700; margin: 8px 0; }
.stat-value.sm { font-size: 20px; }
.stat-unit { font-size: 14px; color: #94a3b8; font-weight: 400; }
.stat-foot { font-size: 12px; }
.row-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.mt20 { margin-top: 20px; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head h3 { margin: 0; }
.src-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f8fafc; font-size: 14px; }
.quick-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.quick-btns .el-button { margin: 0; }
</style>
