<template>
  <div>
    <!-- 市场筛选 + 新增 -->
    <div class="toolbar">
      <el-radio-group v-model="market" @change="onFilterChange">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button v-for="m in MARKETS" :key="m.value" :value="m.value">{{ m.label }}</el-radio-button>
      </el-radio-group>
      <div class="toolbar-right">
        <el-input v-model="keyword" placeholder="搜索代码/名称" clearable style="width: 200px"
                  @keyup.enter="load" @clear="load" />
        <el-button type="primary" @click="addDlg = true">+ 新增证券</el-button>
      </div>
    </div>

    <!-- 证券表格 -->
    <div class="card">
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column label="市场" width="80">
          <template #default="{ row }">
            <span class="badge" :class="'badge-' + row.market.replace('_stock', '')">{{ marketMap[row.market]?.label }}</span>
          </template>
        </el-table-column>
        <el-table-column label="代码" width="120">
          <template #default="{ row }"><span class="bold">{{ row.code }}</span></template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="币种" width="80" align="center">
          <template #default="{ row }">{{ row.currency }}</template>
        </el-table-column>
        <el-table-column label="派息频率" width="100" align="center">
          <template #default="{ row }">{{ freqText(row.freq) }}</template>
        </el-table-column>
        <el-table-column label="最新价" width="130" align="right">
          <template #default="{ row }">
            <div v-if="row.latest_price != null" class="bold">{{ row.currency }} {{ row.latest_price }}</div>
            <div v-else class="text-muted">-</div>
            <div class="text-muted" style="font-size: 11px">
              {{ row.price_updated_at ? row.price_updated_at.slice(0, 10) : '未更新' }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="爬虫白名单" width="120" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.crawl_enabled"
                       :loading="togglingId === row.id"
                       @change="(v) => toggle(row, v)" />
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170">
          <template #default="{ row }">{{ row.updated_at?.slice(0, 16) }}</template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination background layout="total, prev, pager, next"
                       :total="total" :page-size="pageSize" :current-page="page"
                       @current-change="onPage" />
      </div>
      <div v-if="!list.length && !loading" class="empty-tip">暂无证券，点击「新增证券」添加白名单</div>
    </div>

    <p class="hint">
      💡 美股/港股：开启「爬虫白名单」后，该标的会被纳入定时采集；A股/基金走全量列表接口，此标记暂不影响采集。
    </p>

    <!-- 新增证券弹窗 -->
    <el-dialog v-model="addDlg" title="新增证券" width="460">
      <el-form :model="form" label-width="80px">
        <el-form-item label="市场">
          <el-select v-model="form.market" style="width: 100%">
            <el-option v-for="m in MARKETS" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="代码">
          <el-input v-model="form.code" placeholder="如 00700 / VOO" />
        </el-form-item>
        <el-form-item label="名称">
          <el-input v-model="form.name" placeholder="证券名称" />
        </el-form-item>
        <el-form-item label="币种">
          <el-select v-model="form.currency" style="width: 100%">
            <el-option label="CNY 人民币" value="CNY" />
            <el-option label="USD 美元" value="USD" />
            <el-option label="HKD 港币" value="HKD" />
          </el-select>
        </el-form-item>
        <el-form-item label="白名单">
          <el-switch v-model="form.crawl_enabled" active-text="加入爬虫白名单" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiAdminSecurities, apiAdminCreateSecurity, apiAdminToggleCrawlEnabled } from '../../api'
import { MARKETS, marketMap } from '../../utils/constants'

const FREQ_TEXT = {
  monthly: '月派', quarterly: '季派', semi_annual: '半年派',
  annual: '年派', irregular: '不定期', unknown: '未知',
}

const market = ref('all')
const keyword = ref('')
const list = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 50
const total = ref(0)
const togglingId = ref(null)
const addDlg = ref(false)
const saving = ref(false)
const form = reactive({ market: 'us_stock', code: '', name: '', currency: 'USD', crawl_enabled: true })

function freqText(f) { return FREQ_TEXT[f] || f || '-' }

function onFilterChange() { page.value = 1; load() }
function onPage(p) { page.value = p; load() }

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (market.value !== 'all') params.market = market.value
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const data = await apiAdminSecurities(params)
    list.value = data.items || []
    total.value = data.total || 0
  } finally { loading.value = false }
}

async function toggle(row, enabled) {
  togglingId.value = row.id
  try {
    await apiAdminToggleCrawlEnabled(row.id, enabled)
    row.crawl_enabled = enabled
    ElMessage.success(`${enabled ? '已加入' : '已移出'}爬虫白名单`)
  } catch (e) { /* toast 已统一 */ } finally { togglingId.value = null }
}

async function create() {
  if (!form.code.trim() || !form.name.trim()) return ElMessage.warning('请填写代码和名称')
  saving.value = true
  try {
    await apiAdminCreateSecurity({
      market: form.market, code: form.code.trim(), name: form.name.trim(),
      currency: form.currency, crawl_enabled: form.crawl_enabled,
    })
    ElMessage.success('证券已添加')
    addDlg.value = false
    form.code = ''; form.name = ''
    load()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.toolbar-right { display: flex; gap: 12px; align-items: center; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.bold { font-weight: 600; }
.text-muted { color: #94a3b8; }
.pager { display: flex; justify-content: center; padding: 16px 0 4px; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
.hint { font-size: 12px; color: #94a3b8; margin-top: 12px; }
</style>
