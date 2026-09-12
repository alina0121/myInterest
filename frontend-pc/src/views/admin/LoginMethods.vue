<template>
  <div>
    <h1 class="page-title">系统参数配置</h1>
    <p class="hint-intro">
      邮箱/短信/微信三类登录与验证码参数集中配置；开关关闭后前端入口自动隐藏。
      敏感信息（密钥/授权码）脱敏显示，留空保存表示不修改。
    </p>

    <!-- 登录方式总览 -->
    <div class="overview-cards">
      <div class="card overview-card" :class="{ on: loginState.mail }">
        <div class="ov-head">
          <h3>📧 邮箱验证码</h3>
          <el-tag :type="loginState.mail ? 'success' : 'info'" size="small">
            {{ loginState.mail ? '已启用' : '未启用' }}
          </el-tag>
        </div>
        <div class="ov-body">
          <div v-if="loginState.smtp_host" class="ov-row">
            SMTP：{{ loginState.smtp_host }}:{{ loginState.smtp_port }}
            <span class="text-muted">({{ loginState.smtp_use_ssl ? 'SSL' : 'STARTTLS' }})</span>
          </div>
          <div v-else class="ov-row text-muted">未配置 SMTP 服务器</div>
          <div v-if="loginState.smtp_user" class="ov-row">发件账号：{{ loginState.smtp_user }}</div>
          <div v-else class="ov-row text-muted">未配置发件账号</div>
        </div>
      </div>

      <div class="card overview-card" :class="{ on: loginState.sms }">
        <div class="ov-head">
          <h3>📱 短信验证码</h3>
          <el-tag :type="loginState.sms ? 'success' : 'info'" size="small">
            {{ loginState.sms ? '已启用' : '未启用' }}
          </el-tag>
        </div>
        <div class="ov-body">
          <div class="ov-row">服务商：{{ loginState.sms_provider || '—' }}</div>
          <div class="ov-row text-muted">V2 SDK 接入前的开关；默认关闭，前端隐藏短信入口</div>
        </div>
      </div>

      <div class="card overview-card" :class="{ on: loginState.wx }">
        <div class="ov-head">
          <h3>💬 微信小程序</h3>
          <el-tag :type="loginState.wx ? 'success' : 'info'" size="small">
            {{ loginState.wx ? '已配置' : '未配置' }}
          </el-tag>
        </div>
        <div class="ov-body">
          <div class="ov-row">AppID：{{ loginState.wx_appid ? maskOf(loginState.wx_appid) : '未配置' }}</div>
          <div class="ov-row text-muted">AppID 与 Secret 均配置后启用真实微信登录，否则为 mock 模式</div>
        </div>
      </div>
    </div>

    <!-- 配置项详情（按"登录方式"分组，元数据驱动渲染） -->
    <div class="card mt20">
      <div class="card-head">
        <h3>配置详情</h3>
        <el-button v-if="canWrite" type="primary" :loading="cfgSaving" @click="saveConfig">保存修改</el-button>
      </div>
      <p v-if="!canWrite" class="hint-text" style="color:#d97706;margin-top:0">
        当前角色为管理员，登录设置只读；修改需超级管理员。
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
              <!-- 整数 -->
              <el-input-number v-else-if="item.type === 'int'" v-model="formModel[item.key]"
                               :min="item.min ?? undefined" :max="item.max ?? undefined" :step="1"
                               :controls="false" :disabled="!canWrite" style="width: 200px" />
              <!-- 敏感字符串：脱敏展示，留空保存=不修改原值 -->
              <el-input v-else-if="sensitiveOf(item)" v-model="formModel[item.key]"
                        :placeholder="item.has_value ? `当前 ${item.mask}（留空表示不修改）` : '未配置，请填写'"
                        :disabled="!canWrite" show-password autocomplete="new-password" style="width: 360px" />
              <!-- 普通字符串 -->
              <el-input v-else v-model="formModel[item.key]" :disabled="!canWrite" style="width: 360px" />
            </div>
            <div class="cfg-help">{{ item.help }}</div>
          </div>
        </div>
      </div>
      <p class="hint-text">
        修改保存后 60 秒内全局生效（开关立即生效）；敏感信息脱敏显示，所有修改记录操作日志。
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiAdminConfig, apiAdminUpdateConfig, apiAdminResetConfig } from '../../api'
import { useUserStore } from '../../store/user'

const userStore = useUserStore()
const canWrite = computed(() => userStore.user?.role === 'super_admin')

// 配置表单
const configGroups = ref([])
const configLoading = ref(false)
const cfgSaving = ref(false)
const formModel = reactive({})
const sensitiveKeys = new Set()

function sensitiveOf(item) { return sensitiveKeys.has(item.key) }

function maskOf(text) {
  if (!text) return ''
  return ('*'.repeat(Math.max(text.length - 4, 4))) + text.slice(-4)
}

// 总览状态：mail / sms / wx 各项汇总（保存后回填）
const loginState = reactive({
  mail: false, smtp_host: '', smtp_port: 465, smtp_user: '', smtp_use_ssl: true,
  sms: false, sms_provider: 'aliyun',
  wx: false, wx_appid: '',
})

async function loadConfig() {
  configLoading.value = true
  try {
    const { groups } = await apiAdminConfig()
    applyGroups(groups || [])
    applyOverview()
  } finally { configLoading.value = false }
}

function applyGroups(groups) {
  configGroups.value = groups
  sensitiveKeys.clear()
  for (const g of configGroups.value) {
    for (const item of g.items) {
      if (item.mask !== undefined) sensitiveKeys.add(item.key)
      if (sensitiveOf(item)) {
        formModel[item.key] = ''
      } else {
        formModel[item.key] = item.value
      }
    }
  }
}

function applyOverview() {
  // 从 formModel 同步总览显示
  loginState.mail = !!formModel.mail_enabled
  loginState.smtp_host = formModel.smtp_host || ''
  loginState.smtp_port = formModel.smtp_port || 465
  loginState.smtp_user = formModel.smtp_user || ''
  loginState.smtp_use_ssl = formModel.smtp_use_ssl
  loginState.sms = !!formModel.sms_enabled
  loginState.sms_provider = formModel.sms_provider || 'aliyun'
  // wx_appid 是敏感项前端拿不到原文，只能从 has_value 判断
  const wxItem = findItem('wx_appid')
  loginState.wx_appid = wxItem?.has_value ? wxItem.mask || '(已配置)' : ''
  loginState.wx = !!loginState.wx_appid
}

function findItem(key) {
  for (const g of configGroups.value) {
    for (const item of g.items) {
      if (item.key === key) return item
    }
  }
  return null
}

async function saveConfig() {
  const items = {}
  for (const g of configGroups.value) {
    for (const item of g.items) {
      const v = formModel[item.key]
      if (sensitiveOf(item)) {
        const t = (v || '').trim()
        if (t) items[item.key] = t
      } else if (v === null || v === undefined || v === '') {
        // 字符串空值允许（如未配置 SMTP），但布尔/整数不应当空
        if (item.type === 'bool' || item.type === 'int') {
          return ElMessage.warning(`「${item.label}」不能留空`)
        }
        if (JSON.stringify(v) !== JSON.stringify(item.value)) items[item.key] = ''
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
    applyOverview()
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
    applyOverview()
    ElMessage.success('已恢复默认')
  } catch (e) { /* toast 已统一 */ }
}

onMounted(loadConfig)
</script>

<style scoped>
.page-title { font-size: 18px; font-weight: 700; color: #1e293b; margin: 0 0 8px; }
.hint-intro { font-size: 13px; color: #64748b; margin: 0 0 20px; line-height: 1.6; }
.overview-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
.overview-card { padding: 16px 20px; transition: all 0.2s; }
.overview-card.on { border-left: 3px solid #10b981; }
.ov-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.ov-head h3 { margin: 0; font-size: 14px; font-weight: 600; }
.ov-body { font-size: 13px; }
.ov-row { padding: 4px 0; color: #334155; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 16px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.card-head h3 { margin: 0; }
.mt20 { margin-top: 20px; }
.hint-text { font-size: 12px; color: #94a3b8; margin-top: 12px; }
.cfg-group { margin-bottom: 8px; }
.cfg-group-title { font-size: 13px; font-weight: 600; color: #0f766e; margin: 14px 0 6px;
  padding-left: 8px; border-left: 3px solid #14b8a6; }
.cfg-item { display: grid; grid-template-columns: 260px 380px 1fr; gap: 12px; align-items: center;
  padding: 9px 4px; border-bottom: 1px dashed #e2e8f0; }
.cfg-label { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #334155; font-weight: 500; }
.cfg-help { font-size: 12px; color: #94a3b8; line-height: 1.5; }
.text-muted { color: #94a3b8; }
</style>
