<template>
  <div class="login-screen">
    <div class="login-card">
      <!-- 品牌区 -->
      <div class="brand">
        <div class="logo">攒</div>
        <div>
          <div class="brand-name">攒息</div>
          <div class="brand-sub">时间的朋友 · 分红记录助手</div>
        </div>
      </div>

      <!-- Tab 切换：密码 / 邮箱验证码 -->
      <div class="tabs">
        <div :class="['tab', mode === 'pwd' ? 'active' : '']" @click="mode = 'pwd'">密码登录</div>
        <div :class="['tab', mode === 'email' ? 'active' : '']" @click="mode = 'email'">邮箱验证码</div>
      </div>

      <!-- 密码登录 / 注册 -->
      <el-form v-if="mode === 'pwd'" @submit.prevent="submit">
        <el-input v-model="form.account" placeholder="用户名 / 邮箱" size="large" class="mb12" @keyup.enter="submit" />
        <el-input v-model="form.password" type="password" placeholder="密码（注册至少 8 位）" size="large" show-password class="mb12" @keyup.enter="submit" />
        <template v-if="subMode === 'register'">
          <el-input v-model="form.email" placeholder="邮箱（选填）" size="large" class="mb12" />
          <el-input v-model="form.nickname" placeholder="昵称（选填）" size="large" class="mb12" />
        </template>
        <div v-if="subMode === 'login'" class="login-extra">
          <el-checkbox v-model="remember">记住我</el-checkbox>
          <el-link type="primary" :underline="false" style="font-size: 12px" @click="openReset">忘记密码？</el-link>
        </div>

        <div class="sub-mode-switch" v-if="mode === 'pwd'">
          <span v-if="subMode === 'login'">
            还没有账号？<el-link type="primary" :underline="false" @click="subMode = 'register'">立即注册</el-link>
          </span>
          <span v-else>
            已有账号？<el-link type="primary" :underline="false" @click="subMode = 'login'">返回登录</el-link>
          </span>
        </div>

        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">
          {{ subMode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <!-- 邮箱验证码登录 / 注册 -->
      <el-form v-else @submit.prevent="submitEmail">
        <el-input v-model="emailForm.email" placeholder="邮箱地址" size="large" class="mb12" />
        <div class="code-row mb12">
          <el-input v-model="emailForm.code" placeholder="6 位验证码" size="large" @keyup.enter="submitEmail" />
          <el-button size="large" :disabled="cooldown > 0 || sendingCode" :loading="sendingCode" @click="sendCode('login')">
            {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
          </el-button>
        </div>
        <template v-if="subMode === 'register'">
          <el-input v-model="emailForm.nickname" placeholder="昵称（选填）" size="large" class="mb12" />
          <el-input v-model="emailForm.password" type="password" placeholder="密码（选填，便于后续密码登录）" size="large" show-password class="mb12" />
        </template>
        <div class="sub-mode-switch">
          <span v-if="subMode === 'login'">
            还没有账号？<el-link type="primary" :underline="false" @click="subMode = 'register'">立即注册</el-link>
          </span>
          <span v-else>
            已有账号？<el-link type="primary" :underline="false" @click="subMode = 'login'">返回登录</el-link>
          </span>
        </div>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submitEmail">
          {{ subMode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <!-- 其他方式登录 -->
      <div class="divider"><span>其他方式登录</span></div>
      <el-button class="wx-btn" size="large" disabled>💬 微信一键登录（小程序端）</el-button>

      <p class="foot-tip">数据按用户隔离 · 仅本人可见</p>
    </div>

    <!-- 找回密码弹窗 -->
    <el-dialog v-model="resetDlg" title="找回密码" width="420">
      <el-form label-width="80px">
        <el-form-item label="邮箱">
          <el-input v-model="resetForm.email" placeholder="请输入注册邮箱" />
        </el-form-item>
        <el-form-item label="验证码">
          <div class="code-row">
            <el-input v-model="resetForm.code" placeholder="6 位验证码" />
            <el-button :disabled="resetCooldown > 0 || sendingCode" :loading="sendingCode" @click="sendCode('reset')">
              {{ resetCooldown > 0 ? `${resetCooldown}s` : '获取' }}
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetForm.newPassword" type="password" show-password placeholder="新密码（至少 8 位）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDlg = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="submitReset">重置密码</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  apiLogin, apiRegister,
  apiSendCode, apiEmailLogin, apiEmailRegister, apiResetPassword,
} from '../api'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// pwd / email 两种登录方式；subMode 为 login / register
const mode = ref('pwd')
const subMode = ref('login')
const loading = ref(false)
const remember = ref(true)
const form = reactive({ account: '', password: '', email: '', nickname: '' })

// 邮箱验证码表单
const emailForm = reactive({ email: '', code: '', nickname: '', password: '' })
const cooldown = ref(0)
const sendingCode = ref(false)

// 找回密码弹窗
const resetDlg = ref(false)
const resetting = ref(false)
const resetForm = reactive({ email: '', code: '', newPassword: '' })
const resetCooldown = ref(0)

async function submit() {
  if (!form.account || !form.password) {
    return ElMessage.warning('请填写账号和密码')
  }
  if (subMode.value === 'register' && form.password.length < 8) {
    return ElMessage.warning('密码至少 8 位')
  }
  loading.value = true
  try {
    let data
    if (subMode.value === 'login') {
      data = await apiLogin(form.account, form.password)
    } else {
      data = await apiRegister({
        username: form.account,
        email: form.email || null,
        password: form.password,
        nickname: form.nickname || form.account,
      })
    }
    userStore.setAuth(data.access_token, data.user)
    ElMessage.success(subMode.value === 'login' ? '登录成功' : '注册成功')
    router.push(route.query.redirect || '/')
  } catch (e) {
    /* 错误 toast 已统一处理 */
  } finally {
    loading.value = false
  }
}

async function submitEmail() {
  if (!emailForm.email || !emailForm.code) {
    return ElMessage.warning('请填写邮箱和验证码')
  }
  loading.value = true
  try {
    let data
    if (subMode.value === 'login') {
      data = await apiEmailLogin(emailForm.email, emailForm.code)
    } else {
      data = await apiEmailRegister({
        email: emailForm.email,
        code: emailForm.code,
        nickname: emailForm.nickname || null,
        password: emailForm.password || null,
      })
    }
    userStore.setAuth(data.access_token, data.user)
    ElMessage.success(subMode.value === 'login' ? '登录成功' : '注册成功')
    router.push(route.query.redirect || '/')
  } catch (e) {
    /* 错误已统一处理 */
  } finally {
    loading.value = false
  }
}

/** 发送验证码：purpose 为 login（登录/注册）或 reset（找回密码） */
async function sendCode(purpose) {
  // purpose=login 走 emailForm，purpose=reset 走 resetForm
  const email = purpose === 'reset' ? resetForm.email : emailForm.email
  if (!email) return ElMessage.warning('请先填写邮箱')
  // login purpose 在 subMode=register 时也用 register
  const realPurpose = purpose === 'login'
    ? (subMode.value === 'register' ? 'register' : 'login')
    : 'reset'
  sendingCode.value = true
  try {
    await apiSendCode('email', email, realPurpose)
    ElMessage.success('验证码已发送')
    // 倒计时
    const seconds = 60
    if (purpose === 'reset') {
      resetCooldown.value = seconds
      const timer = setInterval(() => {
        resetCooldown.value -= 1
        if (resetCooldown.value <= 0) clearInterval(timer)
      }, 1000)
    } else {
      cooldown.value = seconds
      const timer = setInterval(() => {
        cooldown.value -= 1
        if (cooldown.value <= 0) clearInterval(timer)
      }, 1000)
    }
  } catch (e) {
    /* 错误已统一处理 */
  } finally {
    sendingCode.value = false
  }
}

function openReset() {
  resetForm.email = ''
  resetForm.code = ''
  resetForm.newPassword = ''
  resetCooldown.value = 0
  resetDlg.value = true
}

async function submitReset() {
  if (!resetForm.email || !resetForm.code || !resetForm.newPassword) {
    return ElMessage.warning('请填写邮箱、验证码和新密码')
  }
  if (resetForm.newPassword.length < 8) {
    return ElMessage.warning('新密码至少 8 位')
  }
  resetting.value = true
  try {
    await apiResetPassword(resetForm.email, resetForm.code, resetForm.newPassword)
    ElMessage.success('密码已重置，请用新密码登录')
    resetDlg.value = false
    // 自动带出邮箱和空密码，方便用户继续
    form.account = resetForm.email
    form.password = ''
    mode.value = 'pwd'
    subMode.value = 'login'
  } catch (e) {
    /* 错误已统一处理 */
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.login-screen {
  position: fixed; inset: 0; background: #f1f5f9;
  display: flex; align-items: center; justify-content: center; z-index: 40;
}
.login-card {
  background: #fff; border-radius: 12px; padding: 32px; width: 384px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.brand { display: flex; align-items: center; gap: 12px; justify-content: center; margin-bottom: 24px; }
.logo {
  width: 40px; height: 40px; border-radius: 8px; background: var(--primary);
  color: #fff; font-weight: 700; font-size: 20px;
  display: flex; align-items: center; justify-content: center;
}
.brand-name { font-weight: 700; font-size: 18px; }
.brand-sub { font-size: 12px; color: #94a3b8; }
.tabs { display: flex; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px; }
.tab {
  flex: 1; text-align: center; padding-bottom: 8px; font-size: 14px;
  color: #94a3b8; cursor: pointer; border-bottom: 2px solid transparent;
}
.tab.active { color: var(--primary); font-weight: 500; border-bottom-color: var(--primary); }
.mb12 { margin-bottom: 12px; }
.login-extra { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.sub-mode-switch { text-align: center; font-size: 12px; color: #64748b; margin-bottom: 12px; }
.submit-btn { width: 100%; margin-top: 4px; background: var(--primary); border-color: var(--primary); }
.code-row { display: flex; gap: 8px; }
.code-row .el-input { flex: 1; }
.divider {
  display: flex; align-items: center; gap: 8px; margin: 20px 0 12px;
  color: #cbd5e1; font-size: 12px;
}
.divider::before, .divider::after { content: ''; flex: 1; border-top: 1px solid #e2e8f0; }
.wx-btn { width: 100%; }
.foot-tip { text-align: center; font-size: 12px; color: #94a3b8; margin-top: 16px; }
</style>
