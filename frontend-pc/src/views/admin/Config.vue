<template>
  <div>
    <!-- 汇率 -->
    <div class="card">
      <div class="card-head">
        <h3>汇率管理（折 CNY）</h3>
        <div>
          <el-button @click="addRateDlg = true">+ 手动录入</el-button>
          <el-button type="primary" :loading="refreshing" @click="refreshRates">从数据源刷新</el-button>
        </div>
      </div>
      <el-table :data="rates" v-loading="rateLoading" style="width: 100%">
        <el-table-column label="货币对" width="140">
          <template #default="{ row }"><b>{{ row.base }} → {{ row.quote }}</b></template>
        </el-table-column>
        <el-table-column label="汇率" width="140" align="right">
          <template #default="{ row }">{{ row.rate }}</template>
        </el-table-column>
        <el-table-column prop="rate_date" label="日期" width="120" />
        <el-table-column prop="source" label="数据源" width="140" />
        <el-table-column prop="created_at" label="录入时间" width="180" />
      </el-table>
      <p class="text-muted" style="font-size: 12px; margin-top: 12px">
        每日自动从 frankfurter 拉取 USD/HKD 兑 CNY 汇率；分红按到账日汇率折算
      </p>
    </div>

    <!-- 税率规则 -->
    <div class="card mt20">
      <h3>分红税率规则</h3>
      <el-table :data="taxRules" v-loading="taxLoading" style="width: 100%">
        <el-table-column label="市场" width="80">
          <template #default="{ row }">
            <span class="badge" :class="'badge-' + row.market.replace('_stock', '')">{{ marketMap[row.market]?.label }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="condition" label="条件" min-width="160" />
        <el-table-column label="税率" width="100" align="right">
          <template #default="{ row }">
            <el-input-number v-if="editing === row.id" v-model="editRate" :min="0" :max="1" :step="0.05"
                             :precision="2" :controls="false" size="small" style="width: 90px" />
            <span v-else class="bold">{{ (row.rate * 100).toFixed(0) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="持有天数" width="130" align="center">
          <template #default="{ row }">
            {{ row.hold_min_days ?? 0 }} ~ {{ row.hold_max_days ?? '∞' }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="启用" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <template v-if="editing === row.id">
              <el-button link type="success" @click="saveTax(row)">保存</el-button>
              <el-button link @click="editing = null">取消</el-button>
            </template>
            <template v-else>
              <el-button link type="primary" @click="startEdit(row)">改税率</el-button>
              <el-button link :type="row.enabled ? 'danger' : 'success'" @click="toggleTax(row)">
                {{ row.enabled ? '停用' : '启用' }}
              </el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <p class="text-muted" style="font-size: 12px; margin-top: 12px">
        税率变更需超级管理员权限，修改后自动重算相关分红税费
      </p>
    </div>

    <!-- 手动录入汇率 -->
    <el-dialog v-model="addRateDlg" title="手动录入汇率" width="420">
      <el-form label-width="80px">
        <el-form-item label="货币">
          <el-select v-model="rateForm.base" style="width: 100%">
            <el-option label="USD 美元" value="USD" />
            <el-option label="HKD 港币" value="HKD" />
          </el-select>
        </el-form-item>
        <el-form-item label="汇率">
          <el-input-number v-model="rateForm.rate" :min="0" :precision="6" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="rateForm.rate_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addRateDlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiAdminRates, apiAdminCreateRate, apiAdminRefreshRates, apiAdminTaxRules, apiAdminUpdateTaxRule } from '../../api'
import { marketMap } from '../../utils/constants'

const rates = ref([])
const taxRules = ref([])
const rateLoading = ref(false)
const taxLoading = ref(false)
const refreshing = ref(false)
const addRateDlg = ref(false)
const saving = ref(false)
const editing = ref(null)
const editRate = ref(0)

const rateForm = reactive({ base: 'USD', rate: undefined, rate_date: '' })

async function loadRates() {
  rateLoading.value = true
  try {
    rates.value = (await apiAdminRates()).items || []
  } finally { rateLoading.value = false }
}
async function loadTax() {
  taxLoading.value = true
  try {
    taxRules.value = (await apiAdminTaxRules()).items || []
  } finally { taxLoading.value = false }
}

async function refreshRates() {
  refreshing.value = true
  try {
    await apiAdminRefreshRates()
    ElMessage.success('汇率已刷新')
    loadRates()
  } catch (e) { /* toast 已统一 */ } finally { refreshing.value = false }
}

async function saveRate() {
  if (!rateForm.rate) return ElMessage.warning('请填写汇率')
  saving.value = true
  try {
    await apiAdminCreateRate({ ...rateForm, rate: Number(rateForm.rate), rate_date: rateForm.rate_date })
    ElMessage.success('汇率已录入')
    addRateDlg.value = false
    loadRates()
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
}

function startEdit(row) {
  editing.value = row.id
  editRate.value = row.rate
}

async function saveTax(row) {
  try {
    await apiAdminUpdateTaxRule(row.id, { rate: editRate.value })
    ElMessage.success('税率已更新')
    editing.value = null
    loadTax()
  } catch (e) { /* toast 已统一 */ }
}

async function toggleTax(row) {
  try {
    await apiAdminUpdateTaxRule(row.id, { enabled: row.enabled ? 0 : 1 })
    ElMessage.success(row.enabled ? '已停用' : '已启用')
    loadTax()
  } catch (e) { /* toast 已统一 */ }
}

onMounted(() => { loadRates(); loadTax() })
</script>

<style scoped>
.card h3 { font-size: 15px; font-weight: 600; margin: 0; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.mt20 { margin-top: 20px; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.bold { font-weight: 600; }
</style>
