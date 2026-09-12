<template>
  <div>
    <h1 class="page-title">汇率与税率配置</h1>

    <!-- 汇率大数字卡片 -->
    <div class="rate-cards">
      <div class="card rate-card" v-for="cur in ['USD', 'HKD']" :key="cur">
        <div class="rate-head">
          <h3>{{ curName[cur] }} 汇率</h3>
          <el-button size="small" :loading="refreshing && cur === 'USD'" @click="refreshRates">🔄 自动获取</el-button>
        </div>
        <div class="rate-big">
          <span class="rate-num">{{ latestRate(cur) || '-' }}</span>
          <span class="rate-unit">CNY / {{ cur }}</span>
        </div>
        <div class="rate-meta">更新于 {{ latestDate(cur) || '-' }} · 每日自动更新，历史分红按派息日汇率折算</div>
      </div>
    </div>

    <!-- 汇率明细 + 手动录入 -->
    <div class="card mt20">
      <div class="card-head">
        <h3>汇率明细</h3>
        <el-button @click="addRateDlg = true">+ 手动录入</el-button>
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
    </div>

    <!-- 税率规则 -->
    <div class="card mt20">
      <div class="card-head"><h3>各市场股息税率（用于税后到账估算）</h3></div>
      <el-table :data="taxRules" v-loading="taxLoading" style="width: 100%">
        <el-table-column label="市场" width="90">
          <template #default="{ row }">
            <span class="badge" :class="'badge-' + row.market.replace('_stock', '')">{{ marketMap[row.market]?.label }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="condition" label="税务情形" min-width="160" />
        <el-table-column label="税率" width="100" align="right">
          <template #default="{ row }">
            <el-input-number v-if="editing === row.id" v-model="editRate" :min="0" :max="1" :step="0.05"
                             :precision="2" :controls="false" size="small" style="width: 90px" />
            <span v-else class="bold">{{ (row.rate * 100).toFixed(0) }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '生效中' : '已停用' }}</el-tag>
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
      <p class="hint-text">税率变更需超级管理员权限，修改后自动重算相关分红税费</p>
    </div>

    <!-- 系统参数（元数据驱动：后端 config_service.SPECS 定义，前端按 type 渲染） -->
    <div class="card mt20">
      <div class="card-head">
        <h3>系统参数</h3>
        <el-button v-if="canWrite" type="primary" :loading="cfgSaving" @click="saveConfig">保存修改</el-button>
      </div>
      <p v-if="!canWrite" class="hint-text" style="color:#d97706;margin-top:0">
        当前角色为管理员，系统参数只读；修改需超级管理员。
      </p>
      <div v-loading="configLoading">
        <div v-for="g in configGroups" :key="g.category" class="cfg-group">
          <div class="cfg-group-title">{{ g.category }}</div>
          <div v-for="item in g.items" :key="item.key" class="cfg-item">
            <div class="cfg-label">
              <span>{{ item.label }}</span>
              <el-tag v-if="item.overridden" type="warning" size="small" effect="plain">已自定义</el-tag>
              <el-button v-if="canWrite && item.overridden" link type="danger" size="small"
                         @click="resetCfg(item)">恢复默认</el-button>
            </div>
            <div class="cfg-ctrl">
              <!-- 布尔：开关 -->
              <el-switch v-if="item.type === 'bool'" v-model="formModel[item.key]" :disabled="!canWrite"
                         active-text="开" inactive-text="关" inline-prompt />
              <!-- 整数：数字输入（范围来自后端元数据 min/max） -->
              <el-input-number v-else-if="item.type === 'int'" v-model="formModel[item.key]"
                               :min="item.min ?? undefined" :max="item.max ?? undefined" :step="1"
                               :controls="false" :disabled="!canWrite" style="width: 200px" />
              <!-- 小数：数字输入（兜底汇率等） -->
              <el-input-number v-else-if="item.type === 'float'" v-model="formModel[item.key]"
                               :min="item.min ?? undefined" :max="item.max ?? undefined" :step="0.01"
                               :precision="4" :controls="false" :disabled="!canWrite" style="width: 200px" />
              <!-- 标签式多选（白名单等逗号分隔列表） -->
              <el-select v-else-if="item.widget === 'tags'" v-model="formModel[item.key]"
                         multiple filterable allow-create default-first-option
                         :disabled="!canWrite" style="width: 360px"
                         placeholder="输入代码后回车添加，点 × 删除">
              </el-select>
              <!-- 敏感字符串：脱敏展示，留空保存=不修改原值 -->
              <el-input v-else-if="sensitiveOf(item)" v-model="formModel[item.key]"
                        :placeholder="item.has_value ? `当前 ${item.mask}（留空表示不修改）` : '未配置，请填写'"
                        :disabled="!canWrite" show-password autocomplete="new-password" style="width: 320px" />
              <!-- 普通字符串 -->
              <el-input v-else v-model="formModel[item.key]" :disabled="!canWrite" style="width: 320px" />
            </div>
            <div class="cfg-help">{{ item.help }}</div>
          </div>
        </div>
      </div>
      <p class="hint-text">
        修改保存后 60 秒内全局生效（多数开关立即生效）；敏感信息脱敏显示，所有修改记录操作日志。
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
import { onMounted, reactive, ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiAdminRates, apiAdminCreateRate, apiAdminRefreshRates, apiAdminTaxRules, apiAdminUpdateTaxRule,
  apiAdminConfig, apiAdminUpdateConfig, apiAdminResetConfig } from '../../api'
import { marketMap } from '../../utils/constants'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
// 仅超级管理员可写系统参数；普通管理员进来只读
const canWrite = computed(() => userStore.user?.role === 'super_admin')

const rates = ref([])
const taxRules = ref([])
const rateLoading = ref(false)
const taxLoading = ref(false)
const refreshing = ref(false)
const addRateDlg = ref(false)
const saving = ref(false)
const editing = ref(null)
const editRate = ref(0)
const curName = { USD: '美元', HKD: '港币' }

// ── 系统参数（后端 groups 结构 + 本地表单模型） ──
const configGroups = ref([])          // [{ category, items: [{key,label,help,type,min,max,overridden,value,...}] }]
const configLoading = ref(false)
const cfgSaving = ref(false)
const formModel = reactive({})        // key → 当前编辑值（敏感项初始为空串）
const sensitiveKeys = new Set()       // 敏感配置 key（av_api_key/wx_secret）

function sensitiveOf(item) {
  return sensitiveKeys.has(item.key)
}

async function loadConfig() {
  configLoading.value = true
  try {
    const { groups } = await apiAdminConfig()
    applyGroups(groups)
  } finally { configLoading.value = false }
}

// 用后端返回的 groups 回填表单
function applyGroups(groups) {
  configGroups.value = groups || []
  sensitiveKeys.clear()
  for (const g of configGroups.value) {
      for (const item of g.items) {
        // 后端对敏感项返回 mask 字段（非敏感项无此字段），据此识别并清空本地输入
        if (item.mask !== undefined) sensitiveKeys.add(item.key)
        if (sensitiveOf(item)) {
          formModel[item.key] = ''
        } else if (item.widget === 'tags') {
          // 逗号分隔字符串 → 数组，供 el-select 多选绑定
          formModel[item.key] = (item.value || '').split(',').map((s) => s.trim()).filter(Boolean)
        } else {
          formModel[item.key] = item.value
        }
      }
    }
}

async function saveConfig() {
  // 只提交「真正变化」的项：否则未改项也会被写成 DB 覆盖值，错误地显示「已自定义」
  const items = {}
  for (const g of configGroups.value) {
    for (const item of g.items) {
      const v = formModel[item.key]
      if (sensitiveOf(item)) {
        // 敏感项：输入非空才提交（空串 = 保持原值，后端同约定）
        const t = (v || '').trim()
        if (t) items[item.key] = t
      } else if (item.widget === 'tags') {
        // 标签式：数组 → 逗号分隔字符串
        const arr = Array.isArray(v) ? v.map((s) => String(s).trim()).filter(Boolean) : []
        if (!arr.length) return ElMessage.warning(`「${item.label}」至少保留一项`)
        const joined = arr.join(',')
        if (joined !== item.value) items[item.key] = joined
      } else if (v === null || v === undefined || v === '') {
        return ElMessage.warning(`「${item.label}」不能留空`)
      } else if (JSON.stringify(v) !== JSON.stringify(item.value)) {
        items[item.key] = v
      }
    }
  }
  if (!Object.keys(items).length) return ElMessage.info('没有需要保存的修改')
  cfgSaving.value = true
  try {
    const { groups } = await apiAdminUpdateConfig(items)
    applyGroups(groups)
    ElMessage.success('配置已保存')
  } catch (e) { /* toast 已统一 */ } finally { cfgSaving.value = false }
}

async function resetCfg(item) {
  try {
    await ElMessageBox.confirm(`将「${item.label}」恢复为环境变量/默认值？`, '恢复默认', { type: 'warning' })
  } catch { return }
  try {
    const { groups } = await apiAdminResetConfig(item.key)
    applyGroups(groups)
    ElMessage.success('已恢复默认')
  } catch (e) { /* toast 已统一 */ }
}

const rateForm = reactive({ base: 'USD', rate: undefined, rate_date: '' })

function latestRate(cur) {
  const r = rates.value.find((x) => x.base === cur)
  return r ? Number(r.rate).toFixed(4) : null
}
function latestDate(cur) {
  const r = rates.value.find((x) => x.base === cur)
  return r ? (r.rate_date || r.created_at?.slice(0, 16)) : null
}

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

onMounted(() => { loadRates(); loadTax(); loadConfig() })
</script>

<style scoped>
.page-title { font-size: 18px; font-weight: 700; color: #1e293b; margin: 0 0 16px; }
.rate-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.rate-card .rate-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.rate-card .rate-head h3 { margin: 0; font-size: 15px; font-weight: 600; }
.rate-big { display: flex; align-items: flex-end; gap: 8px; }
.rate-num { font-size: 30px; font-weight: 700; color: #1e293b; }
.rate-unit { font-size: 13px; color: #94a3b8; margin-bottom: 4px; }
.rate-meta { font-size: 12px; color: #94a3b8; margin-top: 8px; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.card-head h3 { margin: 0; }
.mt20 { margin-top: 20px; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.bold { font-weight: 600; }
.hint-text { font-size: 12px; color: #94a3b8; margin-top: 12px; }
.cfg-group { margin-bottom: 8px; }
.cfg-group-title { font-size: 13px; font-weight: 600; color: #0f766e; margin: 14px 0 6px;
  padding-left: 8px; border-left: 3px solid #14b8a6; }
.cfg-item { display: grid; grid-template-columns: 250px 340px 1fr; gap: 12px; align-items: center;
  padding: 9px 4px; border-bottom: 1px dashed #e2e8f0; }
.cfg-label { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #334155; font-weight: 500; }
.cfg-help { font-size: 12px; color: #94a3b8; line-height: 1.5; }
</style>
