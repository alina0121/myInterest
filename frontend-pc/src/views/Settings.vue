<template>
  <div>
    <!-- 4 卡片 2x2 布局 -->
    <div class="settings-grid">
      <!-- 数据导入导出 -->
      <div class="card">
        <h3>📁 数据导入导出</h3>
        <div class="imp-list">
          <button class="imp-btn" @click="importCSV('holding')" disabled>
            <div class="imp-title">导入 CSV 持仓（含多批次）</div>
            <div class="imp-desc">支持东方财富/同花顺导出 · 一次导入同一股票的多笔买入批次</div>
          </button>
          <button class="imp-btn" @click="importCSV('dividend')" disabled>
            <div class="imp-title">导入 CSV 分红记录</div>
            <div class="imp-desc">批量导入历史分红 · 自动按除权日匹配归属批次</div>
          </button>
          <button class="imp-btn" @click="downloadTemplate" disabled>
            <div class="imp-title">下载多批次导入模板</div>
            <div class="imp-desc">字段：代码 / 批次日期 / 方向 / 数量 / 价格 / 费用</div>
          </button>
          <button class="imp-btn" @click="exportCSV" disabled>
            <div class="imp-title">导出全部数据</div>
            <div class="imp-desc">备份为 CSV / JSON 文件</div>
          </button>
        </div>
      </div>

      <!-- 汇率设置 -->
      <div class="card">
        <h3>💱 汇率设置</h3>
        <div class="info-row">
          <span class="text-muted">美元 USD → 人民币</span>
          <b>1 USD = {{ rates.rates?.USD || '-' }} CNY</b>
        </div>
        <div class="info-row">
          <span class="text-muted">港币 HKD → 人民币</span>
          <b>1 HKD = {{ rates.rates?.HKD || '-' }} CNY</b>
        </div>
        <div class="info-row">
          <span class="text-muted">汇率日期</span>
          <span>{{ rates.date || '-' }}</span>
        </div>
        <div class="auto-rate">
          <el-checkbox v-model="autoRate" disabled>自动获取实时汇率</el-checkbox>
        </div>
        <p class="hint-text">分红到账日按当日汇率折算人民币，由运营后台每日自动刷新</p>
      </div>

      <!-- 账户管理（v8：交互式） -->
      <div class="card">
        <div class="card-head-row">
          <h3>🏦 账户管理</h3>
          <el-button size="small" type="primary" @click="openAddAccount">+ 添加</el-button>
        </div>
        <div class="tip-text">账户由你持仓时填写的「账户」字段聚合而来；这里可调整颜色/排序/归档，不影响持仓数据。</div>
        <div v-if="accounts.length" class="acct-list">
          <div v-for="a in accounts" :key="a.name" class="acct-row">
            <span class="acct-dot" :style="{ background: a.color || '#94a3b8' }"></span>
            <div class="acct-info">
              <div class="acct-name">
                {{ a.name }}
                <el-tag v-if="a.archived" size="small" type="info">已归档</el-tag>
              </div>
              <div class="acct-meta">
                <span v-if="a.broker">{{ a.broker }} · </span>
                <span>{{ a.holding_count }} 只持仓</span>
              </div>
            </div>
            <div class="acct-actions">
              <el-button link type="primary" size="small" @click="openEditAccount(a)">编辑</el-button>
              <el-button link :type="a.archived ? 'success' : 'warning'" size="small" @click="toggleArchive(a)">
                {{ a.archived ? '取消归档' : '归档' }}
              </el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-tip">暂无券商账户，可在持仓中填写账户名</div>
        <el-divider />
        <div class="info-row"><span class="text-muted">用户名</span><span>{{ userStore.user?.username }}</span></div>
        <div class="info-row">
          <span class="text-muted">邮箱</span>
          <span>{{ userStore.user?.email || '未绑定' }}</span>
          <el-button link type="primary" size="small" @click="bindDlg = true">
            {{ userStore.user?.email ? '修改' : '绑定' }}
          </el-button>
        </div>
        <div class="info-row"><span class="text-muted">角色</span><span>{{ roleText }}</span></div>
        <el-button type="danger" plain style="margin-top: 16px" @click="logout">退出登录</el-button>
      </div>

      <!-- 提醒设置 -->
      <div class="card">
        <h3>🔔 提醒设置</h3>
        <div class="info-row">
          <span class="text-muted">分红到账日前提醒</span>
          <el-switch v-model="settings.remind_on_payday" />
        </div>
        <div class="info-row">
          <span class="text-muted">提前提醒天数</span>
          <el-input-number v-model="settings.remind_before_days" :min="1" :max="15" size="small" />
        </div>
        <div class="info-row">
          <span class="text-muted">除权除息日提醒</span>
          <el-switch v-model="settings.remind_on_exday" />
        </div>
        <el-button type="primary" style="margin-top: 12px" :loading="savingSettings" @click="saveSettings">保存设置</el-button>
      </div>
    </div>

    <!-- 意见反馈（全宽） -->
    <div class="card mt20">
      <h3>💬 意见反馈</h3>
      <el-input v-model="feedback" type="textarea" :rows="2" placeholder="说说你的建议或遇到的问题" />
      <el-button type="primary" style="margin-top: 12px" :loading="fbSaving" @click="submitFeedback">提交反馈</el-button>
      <div v-if="myFeedback.length" class="fb-list">
        <div v-for="f in myFeedback" :key="f.id" class="fb-item">
          <div class="fb-content">{{ f.content }}</div>
          <div class="text-muted">
            {{ f.created_at?.slice(0, 10) }} ·
            <span :class="f.status === 'resolved' ? 'text-emerald' : 'text-amber'">
              {{ f.status === 'resolved' ? '已回复' : '处理中' }}
            </span>
          </div>
          <div v-if="f.reply" class="fb-reply">管理员回复：{{ f.reply }}</div>
        </div>
      </div>
    </div>

    <!-- 账户编辑弹窗 -->
    <el-dialog v-model="acctDlg" :title="acctForm.origName ? '编辑账户' : '添加账户'" width="420">
      <el-form label-width="80px">
        <el-form-item label="账户名">
          <el-input v-model="acctForm.name" :disabled="!!acctForm.origName"
            placeholder="如 招商证券 / 雪球组合A" />
        </el-form-item>
        <el-form-item label="券商/备注">
          <el-input v-model="acctForm.broker" placeholder="选填" />
        </el-form-item>
        <el-form-item label="颜色">
          <div class="color-row">
            <span v-for="c in ACCOUNT_COLORS" :key="c" class="color-dot"
                  :class="{ active: acctForm.color === c }"
                  :style="{ background: c }" @click="acctForm.color = c"></span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="acctDlg = false">取消</el-button>
        <el-button type="primary" :loading="acctSaving" @click="saveAccount">保存</el-button>
      </template>
    </el-dialog>

    <!-- 绑定邮箱弹窗 -->
    <el-dialog v-model="bindDlg" :title="userStore.user?.email ? '修改绑定邮箱' : '绑定邮箱'" width="420">
      <div v-if="!userStore.user?.email" class="tip-text" style="margin-bottom: 12px">
        绑定后可用邮箱验证码登录、找回密码；若邮箱已被其他账号使用，将合并数据到该账号下。
      </div>
      <el-form label-width="80px">
        <el-form-item label="邮箱">
          <el-input v-model="bindForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="验证码">
          <div class="code-row">
            <el-input v-model="bindForm.code" placeholder="6 位验证码" />
            <el-button :disabled="bindCooldown > 0 || bindSending" :loading="bindSending" @click="sendBindCode">
              {{ bindCooldown > 0 ? `${bindCooldown}s` : '获取' }}
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindDlg = false">取消</el-button>
        <el-button type="primary" :loading="bindLoading" @click="confirmBind">确认绑定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  apiRates, apiSettings, apiSaveSettings, apiCreateFeedback, apiMyFeedback,
  apiAccounts, apiAccountsMeta, apiSendCode, apiBindEmail,
} from '../api'
import { useUserStore } from '../store/user'
import { CURRENCIES } from '../utils/constants'
// 注：v8 显示币种改用本地 DISPLAY_CURRENCIES（含 ORIGINAL 本币选项），CURRENCIES 保留给其他用途

const router = useRouter()
const userStore = useUserStore()

const rates = ref({})
const settings = reactive({
  remind_before_days: 3, remind_on_payday: true, remind_on_exday: true,
  auto_match_schedule: true, push_enabled: false, weekly_summary: false,
})
const autoRate = ref(true)
const savingSettings = ref(false)
const feedback = ref('')
const fbSaving = ref(false)
const myFeedback = ref([])

// v8：账户列表（来自后端聚合）
const accounts = ref([])
const acctDlg = ref(false)
const acctSaving = ref(false)
const acctForm = reactive({ name: '', broker: '', color: '#94a3b8', origName: '' })
const ACCOUNT_COLORS = ['#94a3b8', '#dc2626', '#2563eb', '#059669', '#d97706', '#7c3aed', '#db2777', '#0891b2']

// 绑定邮箱
const bindDlg = ref(false)
const bindLoading = ref(false)
const bindSending = ref(false)
const bindCooldown = ref(0)
const bindForm = reactive({ email: '', code: '' })

const roleText = computed(() =>
  ({ super_admin: '超级管理员', admin: '管理员', user: '普通用户' }[userStore.user?.role] || '普通用户'))

async function load() {
  const [r, s, fb, accts] = await Promise.all([apiRates(), apiSettings(), apiMyFeedback(), apiAccounts()])
  rates.value = r
  Object.assign(settings, {
    remind_before_days: s.remind_before_days,
    remind_on_payday: s.remind_on_payday,
    remind_on_exday: s.remind_on_exday ?? true,
    auto_match_schedule: s.auto_match_schedule,
    push_enabled: s.push_enabled,
    weekly_summary: s.weekly_summary ?? false,
  })
  myFeedback.value = fb.items || []
  accounts.value = accts.items || []
}

async function saveSettings() {
  savingSettings.value = true
  try {
    await apiSaveSettings(settings)
    ElMessage.success('设置已保存')
  } catch (e) { /* toast 已统一 */ } finally { savingSettings.value = false }
}

// ── 账户管理 ──
function openAddAccount() {
  acctForm.name = ''; acctForm.broker = ''; acctForm.color = '#94a3b8'; acctForm.origName = ''
  acctDlg.value = true
}

function openEditAccount(a) {
  acctForm.name = a.name; acctForm.broker = a.broker || ''
  acctForm.color = a.color || '#94a3b8'; acctForm.origName = a.name
  acctDlg.value = true
}

async function saveAccount() {
  if (!acctForm.name) return ElMessage.warning('请填写账户名')
  // 构造 meta：基于当前列表，新增或更新一项
  const meta = accounts.value.map(a => ({
    name: a.name, broker: a.broker || '', color: a.color,
    sort: a.sort || 0, archived: a.archived || false,
  }))
  if (acctForm.origName) {
    // 编辑：找原 name 替换 broker/color（不改名）
    const i = meta.findIndex(m => m.name === acctForm.origName)
    if (i >= 0) {
      meta[i] = { ...meta[i], broker: acctForm.broker, color: acctForm.color }
    }
  } else {
    // 新增
    if (meta.some(m => m.name === acctForm.name)) {
      return ElMessage.warning('账户名已存在')
    }
    meta.push({
      name: acctForm.name, broker: acctForm.broker,
      color: acctForm.color, sort: meta.length, archived: false,
    })
  }
  acctSaving.value = true
  try {
    await apiAccountsMeta(meta)
    ElMessage.success('保存成功')
    acctDlg.value = false
    load()
  } catch (e) { /* toast 已统一 */ } finally { acctSaving.value = false }
}

async function toggleArchive(a) {
  const meta = accounts.value.map(x => ({
    name: x.name, broker: x.broker || '', color: x.color,
    sort: x.sort || 0, archived: x.name === a.name ? !x.archived : (x.archived || false),
  }))
  try {
    await apiAccountsMeta(meta)
    ElMessage.success(a.archived ? '已取消归档' : '已归档')
    load()
  } catch (e) { /* toast 已统一 */ }
}

// ── 绑定邮箱 ──
async function sendBindCode() {
  if (!bindForm.email) return ElMessage.warning('请先填写邮箱')
  bindSending.value = true
  try {
    await apiSendCode('email', bindForm.email, 'bind')
    ElMessage.success('验证码已发送')
    bindCooldown.value = 60
    const timer = setInterval(() => {
      bindCooldown.value -= 1
      if (bindCooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) { /* toast 已统一 */ } finally { bindSending.value = false }
}

async function confirmBind() {
  if (!bindForm.email || !bindForm.code) return ElMessage.warning('请填写邮箱和验证码')
  bindLoading.value = true
  try {
    const data = await apiBindEmail(bindForm.email, bindForm.code)
    // 合并场景：后端返回 merged=true 时表示数据已迁移到邮箱账号下
    userStore.setAuth(data.access_token, data.user)
    ElMessage.success('绑定成功')
    bindDlg.value = false
    bindForm.email = ''; bindForm.code = ''
    load()
  } catch (e) { /* toast 已统一 */ } finally { bindLoading.value = false }
}

async function submitFeedback() {
  if (!feedback.value.trim()) return ElMessage.warning('请填写反馈内容')
  fbSaving.value = true
  try {
    await apiCreateFeedback(feedback.value.trim())
    ElMessage.success('反馈已提交，感谢支持')
    feedback.value = ''
    load()
  } catch (e) { /* toast 已统一 */ } finally { fbSaving.value = false }
}

function exportCSV() {}
function importCSV() {}
function downloadTemplate() {}

function logout() {
  userStore.clear()
  router.push('/login')
}

onMounted(load)
</script>

<style scoped>
.settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.card-head-row h3 { margin: 0; }
.tip-text { font-size: 12px; color: #94a3b8; line-height: 1.5; margin-bottom: 12px; }
.info-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 0; border-bottom: 1px solid #f8fafc; font-size: 14px;
  gap: 8px;
}
.imp-list { display: flex; flex-direction: column; gap: 12px; }
.imp-btn {
  width: 100%; text-align: left; padding: 12px 16px;
  border: 1px solid #e2e8f0; border-radius: 8px; background: #fff;
  cursor: pointer; transition: background 0.15s;
}
.imp-btn:hover:not(:disabled) { background: #f8fafc; }
.imp-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.imp-title { font-size: 14px; font-weight: 500; color: #334155; }
.imp-desc { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.auto-rate { padding: 10px 0; }
.hint-text { font-size: 12px; color: #94a3b8; margin-top: 12px; }
.acct-list { margin-bottom: 8px; }
.acct-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-size: 14px;
}
.acct-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.acct-info { flex: 1; }
.acct-name { font-weight: 500; display: flex; align-items: center; gap: 6px; }
.acct-meta { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.acct-actions { display: flex; gap: 4px; }
.cur-list { display: flex; flex-direction: column; gap: 4px; }
.cur-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 4px; border-bottom: 1px solid #f8fafc;
  cursor: pointer; font-size: 14px;
}
.cur-row:hover { background: #f8fafc; }
.cur-symbol { width: 36px; font-weight: 600; color: #475569; }
.cur-label { flex: 1; color: #334155; }
.mt20 { margin-top: 20px; }
.fb-list { margin-top: 16px; }
.fb-item { padding: 10px 0; border-bottom: 1px solid #f8fafc; }
.fb-content { font-size: 14px; margin-bottom: 4px; }
.fb-reply {
  margin-top: 6px; font-size: 13px; color: #475569;
  background: #f8fafc; border-radius: 6px; padding: 8px 10px;
}
.empty-tip { color: #94a3b8; text-align: center; padding: 20px 0; font-size: 13px; }
.text-muted { color: #64748b; }
.text-emerald { color: #059669; }
.text-amber { color: #d97706; }
.color-row { display: flex; gap: 8px; }
.color-dot {
  width: 24px; height: 24px; border-radius: 50%; cursor: pointer;
  border: 2px solid transparent; transition: border-color 0.15s;
}
.color-dot.active { border-color: #1e293b; }
.code-row { display: flex; gap: 8px; width: 100%; }
.code-row .el-input { flex: 1; }
</style>
