<template>
  <div class="settings-grid">
    <!-- 账户信息 -->
    <div class="card">
      <h3>账户信息</h3>
      <div class="info-row"><span class="text-muted">用户名</span><span>{{ userStore.user?.username }}</span></div>
      <div class="info-row"><span class="text-muted">昵称</span><span>{{ userStore.user?.nickname || '-' }}</span></div>
      <div class="info-row"><span class="text-muted">邮箱</span><span>{{ userStore.user?.email || '-' }}</span></div>
      <div class="info-row"><span class="text-muted">角色</span><span>{{ roleText }}</span></div>
      <el-button type="danger" plain style="margin-top: 16px" @click="logout">退出登录</el-button>
    </div>

    <!-- 今日汇率 -->
    <div class="card">
      <h3>今日汇率 <span class="text-muted" style="font-size: 12px">（{{ rates.date }}，折 CNY）</span></h3>
      <div class="info-row"><span class="text-muted">USD 美元</span><b>1 USD = {{ rates.rates?.USD }} CNY</b></div>
      <div class="info-row"><span class="text-muted">HKD 港币</span><b>1 HKD = {{ rates.rates?.HKD }} CNY</b></div>
      <p class="text-muted" style="font-size: 12px; margin-top: 12px">分红到账日按当日汇率折算人民币，由运营后台每日自动刷新</p>
    </div>

    <!-- 提醒设置 -->
    <div class="card">
      <h3>提醒设置</h3>
      <div class="info-row">
        <span class="text-muted">派息日前提醒</span>
        <el-switch v-model="settings.remind_on_payday" />
      </div>
      <div class="info-row">
        <span class="text-muted">提前提醒天数</span>
        <el-input-number v-model="settings.remind_before_days" :min="1" :max="15" size="small" />
      </div>
      <div class="info-row">
        <span class="text-muted">自动匹配分红预案</span>
        <el-switch v-model="settings.auto_match_schedule" />
      </div>
      <div class="info-row">
        <span class="text-muted">微信订阅消息推送</span>
        <el-switch v-model="settings.push_enabled" disabled />
      </div>
      <el-button type="primary" style="margin-top: 16px" :loading="saving" @click="saveSettings">保存设置</el-button>
    </div>

    <!-- 数据与反馈 -->
    <div class="card">
      <h3>数据与反馈</h3>
      <div class="action-row">
        <el-button @click="exportCSV" :disabled="true">导出 CSV（即将上线）</el-button>
        <el-button @click="importCSV" :disabled="true">导入 CSV（即将上线）</el-button>
      </div>
      <el-divider>意见反馈</el-divider>
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
import { apiRates, apiSettings, apiSaveSettings, apiCreateFeedback, apiMyFeedback } from '../api'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()

const rates = ref({})
const settings = reactive({ remind_before_days: 3, remind_on_payday: true, auto_match_schedule: true, push_enabled: false })
const saving = ref(false)
const feedback = ref('')
const fbSaving = ref(false)
const myFeedback = ref([])

const roleText = computed(() =>
  ({ super_admin: '超级管理员', admin: '管理员', user: '普通用户' }[userStore.user?.role] || '普通用户'))

async function load() {
  const [r, s, fb] = await Promise.all([apiRates(), apiSettings(), apiMyFeedback()])
  rates.value = r
  Object.assign(settings, {
    remind_before_days: s.remind_before_days,
    remind_on_payday: s.remind_on_payday,
    auto_match_schedule: s.auto_match_schedule,
    push_enabled: s.push_enabled,
  })
  myFeedback.value = fb.items || []
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
.action-row { display: flex; gap: 12px; }
.fb-list { margin-top: 16px; }
.fb-item { padding: 10px 0; border-bottom: 1px solid #f8fafc; }
.fb-content { font-size: 14px; margin-bottom: 4px; }
.fb-reply {
  margin-top: 6px; font-size: 13px; color: #475569;
  background: #f8fafc; border-radius: 6px; padding: 8px 10px;
}
</style>
