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

      <!-- 邮箱验证码：登录 / 注册合一 -->
      <el-form @submit.prevent="submitEmail">
        <el-input v-model="emailForm.email" placeholder="邮箱地址" size="large" class="mb12" />
        <div class="code-row mb12">
          <el-input v-model="emailForm.code" placeholder="6 位验证码" size="large" @keyup.enter="submitEmail" />
          <el-button size="large" :disabled="cooldown > 0 || sendingCode" :loading="sendingCode" @click="sendCode">
            {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
          </el-button>
        </div>
        <p class="hint">未注册的邮箱验证通过后将自动创建账号</p>
        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submitEmail">
          登录 / 注册
        </el-button>
      </el-form>

      <p class="foot-tip">数据按用户隔离 · 仅本人可见</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiSendCode, apiEmailLogin } from '../api'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const emailForm = reactive({ email: '', code: '' })
const cooldown = ref(0)
const sendingCode = ref(false)
const loading = ref(false)

async function sendCode() {
  if (!emailForm.email) return ElMessage.warning('请先填写邮箱')
  sendingCode.value = true
  try {
    await apiSendCode('email', emailForm.email, 'login')
    ElMessage.success('验证码已发送')
    cooldown.value = 60
    const timer = setInterval(() => {
      cooldown.value -= 1
      if (cooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) {
    /* 错误 toast 已统一处理 */
  } finally {
    sendingCode.value = false
  }
}

async function submitEmail() {
  if (!emailForm.email || !emailForm.code) {
    return ElMessage.warning('请填写邮箱和验证码')
  }
  loading.value = true
  try {
    const data = await apiEmailLogin(emailForm.email, emailForm.code)
    userStore.setAuth(data.access_token, data.user)
    ElMessage.success(data.is_new_user ? '已自动注册并登录' : '登录成功')
    // 管理员常从顶栏下拉「运营后台」进入；带 redirect 时按 redirect 回跳
    router.push(route.query.redirect || '/')
  } catch (e) {
    /* 错误已统一处理 */
  } finally {
    loading.value = false
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
.mb12 { margin-bottom: 12px; }
.hint { font-size: 12px; color: #94a3b8; margin: -4px 0 12px; }
.submit-btn { width: 100%; margin-top: 4px; background: var(--primary); border-color: var(--primary); }
.code-row { display: flex; gap: 8px; }
.code-row .el-input { flex: 1; }
.foot-tip { text-align: center; font-size: 12px; color: #94a3b8; margin-top: 16px; }
</style>
