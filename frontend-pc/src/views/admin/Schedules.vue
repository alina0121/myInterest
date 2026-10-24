<template>
  <div>
    <!-- 市场 Tab：分市场看「哪些数据没抓到」，pending=0 的市场说明爬虫没覆盖 -->
    <div class="market-tabs">
      <el-radio-group v-model="market" @change="onFilterChange">
        <el-radio-button value="all">
          全部 <span class="tab-count">{{ marketTotal('pending') }}</span>
        </el-radio-button>
        <el-radio-button v-for="m in MARKETS" :key="m.value" :value="m.value">
          {{ m.label }}
          <span class="tab-count" :class="{ 'tab-zero': marketPending(m.value) === 0 }">
            {{ marketPending(m.value) }}
          </span>
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 状态 Tab + 搜索 + 操作 -->
    <div class="toolbar">
      <el-radio-group v-model="status" @change="onFilterChange">
        <el-radio-button value="pending">待审核 ({{ statusCount('pending') }})</el-radio-button>
        <el-radio-button value="published">已发布 ({{ statusCount('published') }})</el-radio-button>
        <el-radio-button value="rejected">已驳回 ({{ statusCount('rejected') }})</el-radio-button>
      </el-radio-group>
      <div class="toolbar-search">
        <el-input v-model="keyword" placeholder="搜索代码/名称（如 000001 / 腾讯）" clearable
                  style="width: 240px" @keyup.enter="search" @clear="onClear">
          <template #append>
            <el-button @click="search">查询</el-button>
          </template>
        </el-input>
      </div>
      <div class="toolbar-right">
        <template v-if="status === 'pending'">
          <el-button type="primary" :disabled="!selectedIds.length" :loading="saving" @click="batchPublish">批量发布</el-button>
          <el-button type="danger" :disabled="!selectedIds.length" :loading="saving" @click="batchReject">批量驳回</el-button>
        </template>
        <el-button @click="crawlDlg = true">手动录入</el-button>
        <el-dropdown @command="onCrawlCmd" trigger="click" :disabled="crawling">
          <el-button type="primary" :loading="crawling">
            立即爬取<el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="all">全部市场</el-dropdown-item>
              <el-dropdown-item v-for="m in crawlMarkets" :key="m.value" :command="m.value">
                仅{{ m.label }}
              </el-dropdown-item>
              <el-dropdown-item command="one" divided>🎯 指定证券爬取</el-dropdown-item>
              <el-dropdown-item command="logs">📜 爬取日志</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 预案表格 -->
    <div class="card">
      <el-table ref="tableRef" :data="list" v-loading="loading" style="width: 100%" @selection-change="handleSelectionChange">
        <el-table-column v-if="status === 'pending'" type="selection" width="48" />
        <el-table-column label="市场" width="80">
          <template #default="{ row }">
            <span class="badge" :class="'badge-' + row.market.replace('_stock', '')">{{ marketMap[row.market]?.label }}</span>
          </template>
        </el-table-column>
        <el-table-column label="代码 / 名称" min-width="140">
          <template #default="{ row }">
            <div class="bold">{{ row.code }}</div>
            <div class="text-muted">{{ row.name }}</div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90" align="center">
          <template #default="{ row }">{{ row.div_type === 'cash' ? '现金分红' : '送股' }}</template>
        </el-table-column>
        <el-table-column label="每股分红" width="100" align="right">
          <template #default="{ row }">{{ row.dps != null ? `${row.currency} ${row.dps}` : '-' }}</template>
        </el-table-column>
        <el-table-column prop="record_date" label="登记日" width="110" />
        <el-table-column prop="ex_date" label="除权日" width="110" />
        <el-table-column prop="pay_date" label="派息日" width="110" />
        <el-table-column label="置信度" width="130" align="center">
          <template #default="{ row }">
            <div class="conf-cell">
              <div class="conf-bar">
                <div class="conf-fill" :class="confClass(row.confidence)" :style="{ width: (row.confidence * 100) + '%' }"></div>
              </div>
              <span :class="confidenceClass(row.confidence)">{{ (row.confidence * 100).toFixed(0) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="status === 'pending'" label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="success" @click="approve(row)">通过</el-button>
            <el-button link type="danger" @click="openReject(row)">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
                       :total="total" :page-size="pageSize" :current-page="page"
                       :page-sizes="[20, 50, 100]"
                       @size-change="onPageSizeChange" @current-change="onPageChange" />
      </div>
      <div v-if="!list.length && !loading" class="empty-tip">该状态下暂无预案</div>
    </div>
    <p class="conf-rule">🕷️ 置信度规则：交易所/公司公告原文 &gt;90% 自动待发布；财经媒体转载 70–90% 待审核；用户提交 &lt;70% 必须人工核对。</p>

    <!-- 手动录入 -->
    <el-dialog v-model="crawlDlg" title="手动录入分红预案" width="560">
      <el-form label-width="100px">
        <div class="form-grid">
          <el-form-item label="市场">
            <el-select v-model="form.market" style="width: 100%">
              <el-option v-for="m in MARKETS" :key="m.value" :label="m.label" :value="m.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="币种">
            <el-select v-model="form.currency" style="width: 100%">
              <el-option label="CNY" value="CNY" /><el-option label="USD" value="USD" /><el-option label="HKD" value="HKD" />
            </el-select>
          </el-form-item>
          <el-form-item label="代码"><el-input v-model="form.code" /></el-form-item>
          <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
          <el-form-item label="每股分红"><el-input-number v-model="form.dps" :min="0" :precision="6" :controls="false" style="width: 100%" /></el-form-item>
          <el-form-item label="类型">
            <el-select v-model="form.div_type" style="width: 100%">
              <el-option label="现金分红" value="cash" /><el-option label="送股" value="bonus_share" />
            </el-select>
          </el-form-item>
          <el-form-item label="登记日"><el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
          <el-form-item label="除权日"><el-date-picker v-model="form.ex_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
          <el-form-item label="派息日"><el-date-picker v-model="form.pay_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="crawlDlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="createSchedule">保存（直接发布）</el-button>
      </template>
    </el-dialog>

    <!-- 驳回原因 -->
    <el-dialog v-model="rejectDlg" title="驳回预案" width="420">
      <el-input v-model="rejectReason" type="textarea" :rows="3" placeholder="请填写驳回原因（必填）" />
      <template #footer>
        <el-button @click="rejectDlg = false">取消</el-button>
        <el-button type="danger" :loading="saving" @click="confirmReject">确认驳回</el-button>
      </template>
    </el-dialog>

    <!-- 指定证券爬取 -->
    <el-dialog v-model="oneDlg" title="指定证券爬取" width="480">
      <el-form label-width="80px">
        <el-form-item label="市场">
          <el-select v-model="oneMarket" style="width: 100%" placeholder="先选市场和类型" @change="oneCode = ''; loadSecOptions()">
            <el-option v-for="m in crawlMarkets" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="证券">
          <el-select v-model="oneCode" filterable :loading="secLoading"
                     :placeholder="oneMarket ? '搜索代码或名称' : '请先选择市场'" :disabled="!oneMarket" style="width: 100%">
            <el-option v-for="s in secOptions" :key="s.id" :label="`${s.code} ${s.name}`" :value="s.code" />
          </el-select>
        </el-form-item>
      </el-form>
      <p class="conf-rule" style="margin-top: 0">💡 仅列出该市场已入库证券；债券无爬虫数据源，请用「手动录入」。</p>
      <template #footer>
        <el-button @click="oneDlg = false">取消</el-button>
        <el-button type="primary" :loading="crawling" :disabled="!oneMarket || !oneCode" @click="crawlOne">开始爬取</el-button>
      </template>
    </el-dialog>

    <!-- 爬取日志 -->
    <el-dialog v-model="logDlg" title="🕷️ 爬取日志" width="640" @closed="stopLogPoll">
      <div class="log-head">
        <el-tag :type="logStatus.running ? 'warning' : 'info'" size="small">
          {{ logStatus.running ? '爬取进行中…' : '空闲' }}
        </el-tag>
        <span class="text-muted log-time">
          {{ logStatus.started_at ? `开始 ${logStatus.started_at.slice(11, 19)}` : '尚未运行' }}<template v-if="logStatus.finished_at"> · 结束 {{ logStatus.finished_at.slice(11, 19) }}</template>
        </span>
      </div>
      <div ref="logBox" class="log-box">
        <div v-for="(l, i) in logStatus.logs" :key="i" class="log-line">{{ l }}</div>
        <div v-if="!logStatus.logs.length" class="log-empty">暂无日志，点「立即爬取」后此处实时显示过程</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowDown } from '@element-plus/icons-vue'
import { apiAdminSchedules, apiAdminCreateSchedule, apiAdminApproveSchedule, apiAdminRejectSchedule, apiAdminCrawl, apiCrawlStatus, apiAdminBatchApprove, apiAdminSecurities } from '../../api'
import { MARKETS, marketMap } from '../../utils/constants'

const market = ref('all')        // 'all' | 'a_share' | 'us_stock' | 'hk_stock' | 'fund'
const status = ref('pending')
const list = ref([])
const counts = ref({})           // 全局 status_counts（不分市场）
const marketCounts = ref({})     // {a_share: {pending,published,rejected}, ...}
const loading = ref(false)
const crawling = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const crawlDlg = ref(false)
const saving = ref(false)
const rejectDlg = ref(false)
const rejectRow = ref(null)
const rejectReason = ref('')
const tableRef = ref()
const selectedIds = ref([])
const keyword = ref('')

const form = reactive({
  market: 'a_share', code: '', name: '', dps: undefined, currency: 'CNY',
  div_type: 'cash', record_date: '', ex_date: '', pay_date: '',
})

function statusText(s) { return { pending: '待审核', published: '已发布', rejected: '已驳回' }[s] || s }
function statusType(s) { return { pending: 'warning', published: 'success', rejected: 'danger' }[s] || 'info' }
function confidenceClass(c) {
  if (c >= 0.85) return 'text-emerald'
  if (c >= 0.7) return 'text-amber'
  return 'conf-low'
}
function confClass(c) {
  if (c >= 0.85) return 'fill-high'
  if (c >= 0.7) return 'fill-mid'
  return 'fill-low'
}

// 某市场 pending 数（市场 tab 标签用，0 时标红，提示「爬虫没覆盖到」）
function marketPending(m) {
  return marketCounts.value[m]?.pending || 0
}
// 所有市场该状态总数（「全部」tab 标签用）
function marketTotal(st) {
  return counts.value[st] || 0
}
// 当前选中市场该状态计数（状态 tab 标签用）
function statusCount(st) {
  if (market.value === 'all') return counts.value[st] || 0
  return marketCounts.value[market.value]?.[st] || 0
}

// 切换市场或状态都重新拉数据（回到第 1 页）
function onFilterChange() {
  tableRef.value?.clearSelection?.()
  page.value = 1
  load()
}

function onPageChange(p) { page.value = p; load() }
function onPageSizeChange(s) { pageSize.value = s; page.value = 1; load() }

// 搜索：按代码/名称过滤，回到第 1 页
function search() {
  tableRef.value?.clearSelection?.()
  page.value = 1
  load()
}

// 清空搜索框：恢复全量列表
function onClear() {
  keyword.value = ''
  page.value = 1
  load()
}

async function load() {
  loading.value = true
  try {
    const params = { status: status.value, page: page.value, page_size: pageSize.value }
    if (market.value !== 'all') params.market = market.value
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const data = await apiAdminSchedules(params)
    list.value = data.items || []
    total.value = data.total || 0
    counts.value = data.status_counts || {}
    marketCounts.value = data.market_counts || {}
  } finally {
    loading.value = false
  }
}

async function crawl(m = 'all') {
  crawling.value = true
  try {
    const r = await apiAdminCrawl(m)
    const label = m === 'all' ? '全部市场' : marketMap[m]?.label || m
    const extra = r.message ? `（${r.message}）` : ''
    ElMessage.success(`${label} 爬取完成：新增 ${r.new_pending || 0} 条${extra}`)
    load()
  } catch (e) { /* toast 已统一 */ } finally { crawling.value = false }
}

// 可爬市场（债券无爬虫数据源）
const crawlMarkets = MARKETS.filter(m => m.value !== 'bond')

// ── 指定证券爬取 ──
const oneDlg = ref(false)
const oneMarket = ref('')
const oneCode = ref('')
const secOptions = ref([])
const secLoading = ref(false)

async function loadSecOptions() {
  if (!oneMarket.value) { secOptions.value = []; return }
  secLoading.value = true
  try {
    const d = await apiAdminSecurities({ market: oneMarket.value, page_size: 200 })
    secOptions.value = d.items || []
  } finally { secLoading.value = false }
}

function onCrawlCmd(cmd) {
  if (cmd === 'one') {
    oneDlg.value = true
    if (!secOptions.value.length) loadSecOptions()
  } else if (cmd === 'logs') {
    openLogDlg()
  } else {
    crawl(cmd)
  }
}

async function crawlOne() {
  crawling.value = true
  try {
    const r = await apiAdminCrawl(oneMarket.value, oneCode.value)
    if (r.message && !r.new_pending) ElMessage.warning(r.message)
    else ElMessage.success(`${oneCode.value} 爬取完成：新增 ${r.new_pending || 0} 条`)
    oneDlg.value = false
    load()
  } catch (e) { /* toast 已统一 */ } finally { crawling.value = false }
}

// ── 爬取日志（轮询后端内存缓冲） ──
const logDlg = ref(false)
const logStatus = ref({ running: false, logs: [], started_at: null, finished_at: null, result: null })
const logBox = ref(null)
let logTimer = null

async function pollLog() {
  try {
    logStatus.value = await apiCrawlStatus()
    nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight })
  } catch (e) { /* toast 已统一 */ }
}

function openLogDlg() {
  logDlg.value = true
  pollLog()
  stopLogPoll()
  logTimer = setInterval(pollLog, 1500)
}

function stopLogPoll() { if (logTimer) { clearInterval(logTimer); logTimer = null } }
onBeforeUnmount(stopLogPoll)

async function createSchedule() {
  if (!form.code || !form.name) return ElMessage.warning('请填写代码和名称')
  saving.value = true
  try {
    const payload = {
      market: form.market, code: form.code.trim(), name: form.name.trim(),
      currency: form.currency, div_type: form.div_type, source: 'manual',
    }
    if (form.dps) payload.dps = Number(form.dps)
    if (form.record_date) payload.record_date = form.record_date
    if (form.ex_date) payload.ex_date = form.ex_date
    if (form.pay_date) payload.pay_date = form.pay_date
    await apiAdminCreateSchedule(payload)
    ElMessage.success('预案已发布并自动匹配持仓用户')
    crawlDlg.value = false
    status.value = 'published'
    load()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}

async function approve(row) {
  saving.value = true
  try {
    await apiAdminApproveSchedule(row.id)
    ElMessage.success('已通过并发布')
    load()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}

function openReject(row) {
  rejectRow.value = row
  rejectReason.value = ''
  rejectDlg.value = true
}

async function confirmReject() {
  if (!rejectReason.value.trim()) return ElMessage.warning('请填写驳回原因')
  saving.value = true
  try {
    await apiAdminRejectSchedule(rejectRow.value.id, rejectReason.value.trim())
    ElMessage.success('已驳回')
    rejectDlg.value = false
    load()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}

function handleSelectionChange(rows) {
  selectedIds.value = rows.map(r => r.id)
}

async function batchPublish() {
  if (!selectedIds.value.length) return
  saving.value = true
  try {
    const r = await apiAdminBatchApprove(selectedIds.value, 'publish')
    ElMessage.success(`已发布 ${r.handled} 条`)
    tableRef.value?.clearSelection()
    load()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}

async function batchReject() {
  if (!selectedIds.value.length) return
  let reason
  try {
    const res = await ElMessageBox.prompt('请输入驳回理由', '批量驳回', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '驳回理由（必填）',
    })
    reason = res.value
  } catch (e) {
    return // 用户取消
  }
  if (!reason || !reason.trim()) return ElMessage.warning('请填写驳回理由')
  saving.value = true
  try {
    const r = await apiAdminBatchApprove(selectedIds.value, 'reject', reason.trim())
    ElMessage.success(`已驳回 ${r.handled} 条`)
    tableRef.value?.clearSelection()
    load()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.market-tabs { margin-bottom: 12px; }
.market-tabs :deep(.el-radio-button__inner) { padding: 8px 16px; }
/* tab 上的 pending 数字徽章；0 时标红，提示爬虫没覆盖该市场 */
.tab-count {
  display: inline-block;
  min-width: 18px;
  padding: 0 6px;
  margin-left: 4px;
  background: #e2e8f0;
  color: #475569;
  border-radius: 10px;
  font-size: 12px;
  line-height: 16px;
}
.tab-zero {
  background: #fee2e2;
  color: #dc2626;
}
.toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; flex-wrap: wrap; }
.toolbar-search { flex: 0 0 auto; }
.toolbar-right { margin-left: auto; display: flex; gap: 12px; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.bold { font-weight: 500; }
.conf-low { color: #ef4444; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
.pager { display: flex; justify-content: center; padding: 16px 0 4px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; column-gap: 16px; }
/* 置信度进度条 */
.conf-cell { display: flex; align-items: center; gap: 6px; }
.conf-bar { width: 56px; height: 6px; background: #f1f5f9; border-radius: 4px; overflow: hidden; }
.conf-fill { height: 100%; border-radius: 4px; }
.fill-high { background: #10b981; }
.fill-mid { background: #f59e0b; }
.fill-low { background: #ef4444; }
.text-emerald { color: #059669; }
.text-amber { color: #d97706; }
.conf-rule { font-size: 12px; color: #94a3b8; margin-top: 12px; }

/* 爬取日志弹窗 */
.log-head { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.log-time { font-size: 12px; }
.log-box {
  max-height: 380px; overflow-y: auto; background: #0f172a;
  border-radius: 8px; padding: 12px 14px;
}
.log-line {
  font-family: Consolas, Monaco, monospace; font-size: 12px; line-height: 1.7;
  color: #a5f3fc; white-space: pre-wrap; word-break: break-all;
}
.log-empty { padding: 24px; text-align: center; font-size: 12px; color: #64748b; }
</style>
