<template>
  <div>
    <!-- 状态 Tab + 操作 -->
    <div class="toolbar">
      <el-radio-group v-model="status" @change="load">
        <el-radio-button value="pending">待审核 ({{ counts.pending || 0 }})</el-radio-button>
        <el-radio-button value="published">已发布 ({{ counts.published || 0 }})</el-radio-button>
        <el-radio-button value="rejected">已驳回 ({{ counts.rejected || 0 }})</el-radio-button>
      </el-radio-group>
      <div class="toolbar-right">
        <template v-if="status === 'pending'">
          <el-button type="primary" :disabled="!selectedIds.length" :loading="saving" @click="batchPublish">批量发布</el-button>
          <el-button type="danger" :disabled="!selectedIds.length" :loading="saving" @click="batchReject">批量驳回</el-button>
        </template>
        <el-button @click="crawlDlg = true">手动录入</el-button>
        <el-button type="primary" :loading="crawling" @click="crawl">立即爬取</el-button>
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
        <el-table-column label="来源" width="90">
          <template #default="{ row }">{{ sourceText(row.source) }}</template>
        </el-table-column>
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
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiAdminSchedules, apiAdminCreateSchedule, apiAdminApproveSchedule, apiAdminRejectSchedule, apiAdminCrawl, apiAdminBatchApprove } from '../../api'
import { MARKETS, marketMap } from '../../utils/constants'

const status = ref('pending')
const list = ref([])
const counts = ref({})
const loading = ref(false)
const crawling = ref(false)
const crawlDlg = ref(false)
const saving = ref(false)
const rejectDlg = ref(false)
const rejectRow = ref(null)
const rejectReason = ref('')
const tableRef = ref()
const selectedIds = ref([])

const form = reactive({
  market: 'a_share', code: '', name: '', dps: undefined, currency: 'CNY',
  div_type: 'cash', record_date: '', ex_date: '', pay_date: '',
})

function sourceText(s) { return { crawl: '爬取', manual: '手动录入', admin: '后台' }[s] || s }
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

async function load() {
  loading.value = true
  try {
    const data = await apiAdminSchedules({ status: status.value, page: 1, page_size: 50 })
    list.value = data.items || []
    counts.value = data.status_counts || {}
  } finally {
    loading.value = false
  }
}

async function crawl() {
  crawling.value = true
  try {
    const r = await apiAdminCrawl()
    ElMessage.success(`爬取完成：${r.fetched || 0} 条`)
    load()
  } catch (e) { /* toast 已统一 */ } finally { crawling.value = false }
}

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
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.toolbar-right { display: flex; gap: 12px; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.bold { font-weight: 500; }
.conf-low { color: #ef4444; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
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
</style>
