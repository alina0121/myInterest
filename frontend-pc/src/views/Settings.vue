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

      <!-- 账户管理 -->
      <div class="card">
        <h3>🏦 账户管理</h3>
        <div v-if="accounts.length" class="acct-list">
          <div v-for="a in accounts" :key="a" class="acct-row">
            <span>{{ a }}</span>
            <el-link type="primary" :underline="false" style="font-size: 12px">编辑</el-link>
          </div>
        </div>
        <div v-else class="empty-tip">暂无券商账户，可在持仓中填写账户名</div>
        <el-link type="primary" :underline="false" style="margin-top: 12px" disabled>+ 添加账户</el-link>
        <el-divider />
        <div class="info-row"><span class="text-muted">用户名</span><span>{{ userStore.user?.username }}</span></div>
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
        <div class="info-row">
          <span class="text-muted">每周分红汇总推送</span>
          <el-switch v-model="settings.weekly_summary" disabled />
        </div>
        <el-button type="primary" style="margin-top: 16px" :loading="saving" @click="saveSettings">保存设置</el-button>
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiRates, apiSettings, apiSaveSettings, apiCreateFeedback, apiMyFeedback, apiHoldings } from '../api'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()

const rates = ref({})
const settings = reactive({
  remind_before_days: 3, remind_on_payday: true, remind_on_exday: true,
  auto_match_schedule: true, push_enabled: false, weekly_summary: false,
})
const autoRate = ref(true)
const saving = ref(false)
const feedback = ref('')
const fbSaving = ref(false)
const myFeedback = ref([])
const accounts = ref([])

const roleText = computed(() =>
  ({ super_admin: '超级管理员', admin: '管理员', user: '普通用户' }[userStore.user?.role] || '普通用户'))

async function load() {
  const [r, s, fb, h] = await Promise.all([apiRates(), apiSettings(), apiMyFeedback(), apiHoldings()])
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
  // 从持仓中提取去重账户名
  const items = h.items || h || []
  accounts.value = [...new Set(items.map((x) => x.account).filter(Boolean))]
}

async function saveSettings() {
  saving.value = true
  try {
    await apiSaveSettings({ ...settings })
    ElMessage.success('设置已保存')
  } catch (e) { /* toast 已统一 */ } finally { saving.value = false }
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
.info-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 0; border-bottom: 1px solid #f8fafc; font-size: 14px;
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
.acct-list { margin-bottom: 4px; }
.acct-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 14px;
}
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
</style>
