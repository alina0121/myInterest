<template>
  <div>
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索代码 / 名称" style="width: 220px" clearable @keyup.enter="load" />
      <el-select v-model="market" placeholder="全部市场" style="width: 130px" clearable @change="load">
        <el-option v-for="m in MARKETS" :key="m.value" :label="m.label" :value="m.value" />
      </el-select>
      <el-button type="primary" @click="addDlg = true">+ 添加持仓</el-button>
    </div>

    <!-- 持仓表格 -->
    <div class="card">
      <el-table :data="list" v-loading="loading" style="width: 100%" @row-click="goDetail">
        <el-table-column label="市场" width="80">
          <template #default="{ row }">
            <span class="badge" :class="'badge-' + row.market.replace('_stock', '')">{{ marketMap[row.market]?.label }}</span>
          </template>
        </el-table-column>
        <el-table-column label="代码 / 名称" min-width="150">
          <template #default="{ row }">
            <div class="bold">{{ row.code }}</div>
            <div class="text-muted">{{ row.name }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="shares_now" label="持仓数量" width="100" align="right" />
        <el-table-column label="平均成本" width="110" align="right">
          <template #default="{ row }">{{ sym(row.currency) }}{{ fmt(row.avg_cost, 4) }}</template>
        </el-table-column>
        <el-table-column label="币种" width="70" align="center">
          <template #default="{ row }">{{ row.currency }}</template>
        </el-table-column>
        <el-table-column prop="lot_count" label="批次" width="70" align="center" />
        <el-table-column label="本年分红" width="120" align="right">
          <template #default="{ row }">
            <span class="text-emerald bold">{{ fmtCNY(row.year_dividend_cny ?? row.year_dividend) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="累计分红" width="120" align="right">
          <template #default="{ row }">{{ fmtCNY(row.total_dividend_cny ?? row.total_dividend) }}</template>
        </el-table-column>
        <el-table-column label="股息率(TTM)" width="110" align="right">
          <template #default="{ row }">
            <span class="bold">{{ (row.yoc_ttm * 100).toFixed(2) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="派息频率" width="90" align="center">
          <template #default="{ row }">{{ freqMap[row.freq] || '未知' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="goDetail(row)">查看批次</el-button>
            <el-popconfirm title="删除该持仓及其所有批次和分红记录？" @confirm="delHolding(row)">
              <template #reference><el-button link type="danger" @click.stop>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!list.length && !loading" class="empty-tip">暂无持仓，点击右上角「+ 添加持仓」开始记录</div>
    </div>

    <!-- 添加持仓 -->
    <el-dialog v-model="addDlg" title="添加持仓（含首笔买入）" width="560">
      <el-form label-width="90px">
        <div class="form-grid">
          <el-form-item label="市场">
            <el-select v-model="form.market" style="width: 100%">
              <el-option v-for="m in MARKETS" :key="m.value" :label="m.label" :value="m.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="币种">
            <el-select v-model="form.currency" style="width: 100%">
              <el-option label="CNY 人民币" value="CNY" />
              <el-option label="USD 美元" value="USD" />
              <el-option label="HKD 港币" value="HKD" />
            </el-select>
          </el-form-item>
          <el-form-item label="代码">
            <el-input v-model="form.code" placeholder="如 600519 / AAPL" />
          </el-form-item>
          <el-form-item label="名称">
            <el-input v-model="form.name" placeholder="如 贵州茅台" />
          </el-form-item>
          <el-form-item label="账户">
            <el-input v-model="form.account" placeholder="选填，如 招商证券" />
          </el-form-item>
          <el-form-item label="派息频率">
            <el-select v-model="form.freq" style="width: 100%">
              <el-option v-for="f in FREQS" :key="f.value" :label="f.label" :value="f.value" />
            </el-select>
          </el-form-item>
        </div>
        <el-divider>首笔买入批次（选填，可稍后在详情页添加）</el-divider>
        <div class="form-grid">
          <el-form-item label="买入日期">
            <el-date-picker v-model="form.fl_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="买入数量">
            <el-input-number v-model="form.fl_shares" :min="0" :controls="false" style="width: 100%" placeholder="股数" />
          </el-form-item>
          <el-form-item label="买入单价">
            <el-input-number v-model="form.fl_price" :min="0" :precision="4" :controls="false" style="width: 100%" placeholder="每股价格" />
          </el-form-item>
          <el-form-item label="手续费">
            <el-input-number v-model="form.fl_fee" :min="0" :precision="2" :controls="false" style="width: 100%" placeholder="选填" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="addDlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiHoldings, apiCreateHolding, apiDeleteHolding } from '../api'
import { MARKETS, marketMap, freqMap, FREQS, fmt, fmtCNY, currencyMap } from '../utils/constants'

const router = useRouter()
const list = ref([])
const loading = ref(false)
const keyword = ref('')
const market = ref('')
const addDlg = ref(false)
const saving = ref(false)

const form = reactive({
  market: 'a_share', currency: 'CNY', code: '', name: '', account: '', freq: 'unknown',
  fl_date: '', fl_shares: undefined, fl_price: undefined, fl_fee: 0,
})

function sym(c) { return currencyMap[c]?.symbol || '' }

async function load() {
  loading.value = true
  try {
    const params = {}
    if (keyword.value) params.keyword = keyword.value
    if (market.value) params.market = market.value
    const data = await apiHoldings(params)
    list.value = data.items || []
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form.code || !form.name) return ElMessage.warning('请填写代码和名称')
  const payload = {
    market: form.market, code: form.code.trim(), name: form.name.trim(),
    currency: form.currency, account: form.account || null, freq: form.freq,
  }
  if (form.fl_date && form.fl_shares > 0) {
    payload.first_lot = {
      trade_date: form.fl_date, direction: 'buy',
      shares: Number(form.fl_shares), price: Number(form.fl_price || 0), fee: Number(form.fl_fee || 0),
    }
  }
  saving.value = true
  try {
    await apiCreateHolding(payload)
    ElMessage.success('持仓已创建')
    addDlg.value = false
    load()
  } catch (e) {
    /* toast 已统一 */
  } finally {
    saving.value = false
  }
}

function goDetail(row) { router.push(`/holdings/${row.id}`) }

async function delHolding(row) {
  try {
    await apiDeleteHolding(row.id)
    ElMessage.success('持仓已删除')
    load()
  } catch (e) { /* toast 已统一 */ }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; gap: 12px; margin-bottom: 16px; align-items: center; }
.toolbar .el-button { margin-left: auto; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.bold { font-weight: 500; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; column-gap: 16px; }
</style>
