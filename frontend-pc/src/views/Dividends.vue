<template>
  <div>
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-select v-model="year" placeholder="全部年份" style="width: 120px" clearable @change="load">
        <el-option v-for="y in yearOptions" :key="y" :label="y + ' 年'" :value="y" />
      </el-select>
      <el-select v-model="market" placeholder="全部市场" style="width: 120px" clearable @change="load">
        <el-option v-for="m in MARKETS" :key="m.value" :label="m.label" :value="m.value" />
      </el-select>
      <el-select v-model="status" placeholder="全部状态" style="width: 120px" clearable @change="load">
        <el-option label="已到账" value="confirmed" />
        <el-option label="待确认" value="pending" />
      </el-select>
      <el-button type="primary" @click="openCreate">+ 记一笔分红</el-button>
    </div>

    <!-- 分红表格 -->
    <div class="card">
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="alloc-box">
              <div class="text-muted" style="margin-bottom: 8px">
                批次归属明细 · 按股权登记日 {{ row.record_date || row.ex_date }} 匹配当时持仓批次
              </div>
              <template v-if="row.allocations?.length">
                <div v-for="(a, i) in row.allocations" :key="i" class="alloc-line">
                  <span>{{ a.trade_date }} 买入 {{ fmt(a.lot_shares) }} 股</span>
                  <span>参与 {{ fmt(a.shares) }} 股</span>
                  <span>分红 {{ sym(row.currency) }}{{ fmt(a.gross) }}</span>
                  <span v-if="a.hold_days !== undefined" class="text-muted">持有 {{ a.hold_days }} 天</span>
                </div>
              </template>
              <div v-else class="text-muted">（手动记录，未展开批次明细）</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="持仓" min-width="160">
          <template #default="{ row }">
            <div class="bold">{{ row.holding_name }}</div>
            <div class="text-muted">{{ row.code }} · {{ marketMap[row.market]?.label }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="ex_date" label="除权日" width="110" />
        <el-table-column prop="pay_date" label="派息日" width="110" />
        <el-table-column label="每股分红" width="100" align="right">
          <template #default="{ row }">{{ sym(row.currency) }}{{ fmt(row.dps) }}</template>
        </el-table-column>
        <el-table-column prop="shares" label="参与股数" width="100" align="right" />
        <el-table-column label="税前" width="100" align="right">
          <template #default="{ row }">{{ sym(row.currency) }}{{ fmt(row.gross_amount) }}</template>
        </el-table-column>
        <el-table-column label="税费" width="90" align="right">
          <template #default="{ row }">{{ fmt(row.tax) }}</template>
        </el-table-column>
        <el-table-column label="税后(折CNY)" width="120" align="right">
          <template #default="{ row }"><span class="text-emerald bold">{{ fmtCNY(row.net_cny) }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'confirmed' ? 'success' : 'warning'" size="small">
              {{ row.status === 'confirmed' ? '已到账' : '待确认' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="80">
          <template #default="{ row }">{{ sourceText(row.source) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop>编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination background layout="prev, pager, next" :total="total"
                       :page-size="pageSize" :current-page="page" @current-change="onPage" />
      </div>
    </div>

    <!-- 记分红 -->
    <el-dialog v-model="createDlg" title="记一笔分红" width="520" :close-on-click-modal="false">
      <el-form label-width="100px">
        <el-form-item label="持仓">
          <el-select v-model="form.holding_id" style="width: 100%" placeholder="选择持仓">
            <el-option v-for="h in holdings" :key="h.id"
                       :label="`${h.name} (${h.code}) · ${h.shares_now}股`" :value="h.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="除权日">
          <el-date-picker v-model="form.ex_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="股权登记日">
          <el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD" style="width: 100%"
                          placeholder="不填自动推断（A股=除权日前一交易日）" />
        </el-form-item>
        <el-form-item label="派息日">
          <el-date-picker v-model="form.pay_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="每股分红">
          <el-input-number v-model="form.dps" :min="0" :precision="6" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="税费(选填)">
          <el-input-number v-model="form.tax" :min="0" :precision="2" :controls="false" style="width: 100%"
                           placeholder="留空按规则自动估算" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="confirmed">已到账</el-radio>
            <el-radio value="pending">预告(待确认)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存并自动计算归属</el-button>
      </template>
    </el-dialog>

    <!-- 归属计算结果 -->
    <el-dialog v-model="resultDlg" title="归属计算结果" width="420">
      <div class="result-box" v-if="result">
        <div class="r-row"><span>登记日持仓</span><b>{{ fmt(result.shares) }} 股</b></div>
        <div class="r-row"><span>税前分红</span><b>{{ sym(result.currency) }}{{ fmt(result.gross_amount) }}</b></div>
        <div class="r-row"><span>税费</span><b class="text-amber">{{ sym(result.currency) }}{{ fmt(result.tax) }}</b></div>
        <div class="r-row big"><span>税后到账</span><b class="text-emerald">{{ sym(result.currency) }}{{ fmt(result.net_amount) }}</b></div>
        <div class="text-muted" v-if="result.record_date_auto">登记日为自动推断，如与实际不符可联系管理员修正</div>
      </div>
      <template #footer>
        <el-button type="primary" @click="resultDlg = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiDividends, apiCreateDividend, apiHoldings } from '../api'
import { MARKETS, marketMap, fmt, fmtCNY, currencyMap } from '../utils/constants'

const route = useRoute()
const list = ref([])
const holdings = ref([])
const loading = ref(false)
const year = ref(route.query.year || '')
const market = ref('')
const status = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const createDlg = ref(false)
const resultDlg = ref(false)
const saving = ref(false)
const result = ref(null)

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 6 }, (_, i) => currentYear - i)

const form = reactive({ holding_id: null, ex_date: '', record_date: '', pay_date: '', dps: undefined, tax: undefined, status: 'confirmed' })

function sym(c) { return currencyMap[c]?.symbol || '' }
function sourceText(s) {
  return { manual: '手动', auto_match: '预案匹配', schedule: '预案', crawl: '爬取' }[s] || s
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (year.value) params.year = year.value
    if (market.value) params.market = market.value
    if (status.value) params.status = status.value
    const data = await apiDividends(params)
    list.value = data.items || []
    total.value = data.total || list.value.length
  } finally {
    loading.value = false
  }
}

function onPage(p) { page.value = p; load() }

async function openCreate() {
  if (!holdings.value.length) {
    const data = await apiHoldings()
    holdings.value = data.items || []
  }
  Object.assign(form, { holding_id: null, ex_date: today(), record_date: '', pay_date: today(), dps: undefined, tax: undefined, status: 'confirmed' })
  createDlg.value = true
}

function today() { return new Date().toISOString().slice(0, 10) }

async function save() {
  if (!form.holding_id) return ElMessage.warning('请选择持仓')
  if (!form.dps) return ElMessage.warning('请填写每股分红')
  saving.value = true
  try {
    const payload = {
      holding_id: form.holding_id, ex_date: form.ex_date, pay_date: form.pay_date,
      dps: Number(form.dps), status: form.status,
    }
    if (form.record_date) payload.record_date = form.record_date
    if (form.tax !== undefined && form.tax !== null) payload.tax = Number(form.tax)
    result.value = await apiCreateDividend(payload)
    createDlg.value = false
    resultDlg.value = true
    load()
  } catch (e) {
    /* toast 已统一 */
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.toolbar .el-button { margin-left: auto; }
.bold { font-weight: 500; }
.alloc-box { padding: 8px 16px 16px 48px; background: #f8fafc; }
.alloc-line { display: flex; gap: 24px; font-size: 13px; padding: 4px 0; color: #475569; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
.result-box { padding: 0 16px; }
.r-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f1f5f9; }
.r-row.big { font-size: 18px; border-bottom: none; }
</style>
