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
              <template v-if="row.batches?.length">
                <div v-for="(a, i) in row.batches" :key="i" class="alloc-line">
                  <span>{{ a.lot_date }} 买入 {{ fmt(a.shares) }} 股参与</span>
                  <span>分红 {{ sym(row.currency) }}{{ fmt(a.gross) }}</span>
                  <span class="text-muted">税率 {{ fmt(a.rate * 100) }}% · 税费 {{ fmt(a.tax) }}</span>
                </div>
              </template>
              <div v-else class="text-muted">无参与批次（当前无符合条件持仓）</div>
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
        <el-table-column label="税后" width="120" align="right">
          <template #default="{ row }"><span class="text-emerald bold">{{ fmtDisplay(row.net_display ?? row.net_cny, row.display_currency, row.currency) }}</span></template>
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
      </el-table>
      <div class="pager">
        <el-pagination background layout="prev, pager, next" :total="total"
                       :page-size="pageSize" :current-page="page" @current-change="onPage" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { apiDividends } from '../api'
import { MARKETS, marketMap, fmt, fmtDisplay, currencyMap } from '../utils/constants'
import { useUserStore } from '../store/user'

const userStore = useUserStore()

const route = useRoute()
const list = ref([])
const loading = ref(false)
const year = ref(route.query.year || '')
const market = ref('')
const status = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 6 }, (_, i) => currentYear - i)

function sym(c) { return currencyMap[c]?.symbol || '' }
function sourceText(s) {
  return { manual: '手动', auto_match: '预案匹配', schedule: '预案', crawl: '爬取' }[s] || s
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize, expand: 'batches' }
    if (year.value) params.year = year.value
    if (market.value) params.market = market.value
    if (status.value) params.status = status.value
    // v8：账户跟随 + 显示币种转换
    if (userStore.currentAccount && userStore.currentAccount !== '__all__') {
      params.account = userStore.currentAccount
    }
    // v8：币种转换仅在总览看板生效，分红页按 CNY 显示
    const data = await apiDividends(params)
    list.value = data.items || []
    total.value = data.total || list.value.length
  } finally {
    loading.value = false
  }
}

function onPage(p) { page.value = p; load() }

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.toolbar .el-select { flex-shrink: 0; }
.bold { font-weight: 500; }
.alloc-box { padding: 8px 16px 16px 48px; background: #f8fafc; }
.alloc-line { display: flex; gap: 24px; font-size: 13px; padding: 4px 0; color: #475569; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
