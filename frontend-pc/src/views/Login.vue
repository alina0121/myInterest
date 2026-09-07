<template>
  <div class="login-screen">
    <div class="login-card">
      <!-- 品牌区 -->
      <div class="brand">
        <div class="logo">息</div>
        <div>
          <div class="brand-name">息计</div>
          <div class="brand-sub">多用户分红记录助手</div>
        </div>
      </div>

      <!-- Tab 切换 -->
      <div class="tabs">
        <div :class="['tab', mode === 'login' ? 'active' : '']" @click="mode = 'login'">登录</div>
        <div :class="['tab', mode === 'register' ? 'active' : '']" @click="mode = 'register'">注册</div>
      </div>

      <el-form @submit.prevent="submit">
        <el-input v-model="form.account" placeholder="用户名 / 邮箱" size="large" class="mb12" @keyup.enter="submit" />
        <el-input v-model="form.password" type="password" placeholder="密码（注册至少 8 位）" size="large" show-password class="mb12" @keyup.enter="submit" />
        <template v-if="mode === 'register'">
          <el-input v-model="form.email" placeholder="邮箱（选填）" size="large" class="mb12" />
          <el-input v-model="form.nickname" placeholder="昵称（选填）" size="large" class="mb12" />
        </template>
        <div v-if="mode === 'login'" class="login-extra">
          <el-checkbox v-model="remember">记住我</el-checkbox>
          <el-link type="primary" :underline="false" style="font-size: 12px">忘记密码？</el-link>
        </div>

        <el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <!-- 其他方式登录 -->
      <div class="divider"><span>其他方式登录</span></div>
      <el-button class="wx-btn" size="large" disabled>💬 微信一键登录（小程序端）</el-button>

      <p class="foot-tip">数据按用户隔离 · 仅本人可见</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiLogin, apiRegister } from '../api'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const mode = ref('login')
const loading = ref(false)
const remember = ref(true)
const form = reactive({ account: '', password: '', email: '', nickname: '' })

async function submit() {
  if (!form.account || !form.password) {
    return ElMessage.warning('请填写账号和密码')
  }
  if (mode.value === 'register' && form.password.length < 8) {
    return ElMessage.warning('密码至少 8 位')
  }
  loading.value = true
  try {
    let data
    if (mode.value === 'login') {
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
    ElMessage.success(mode.value === 'login' ? '登录成功' : '注册成功')
    router.push(route.query.redirect || '/')
  } catch (e) {
    /* 错误 toast 已统一处理 */
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
.tabs { display: flex; border-bottom: 1px solid #e2e8f0; margin-bottom: 20px; }
.tab {
  flex: 1; text-align: center; padding-bottom: 8px; font-size: 14px;
  color: #94a3b8; cursor: pointer; border-bottom: 2px solid transparent;
}
.tab.active { color: var(--primary); font-weight: 500; border-bottom-color: var(--primary); }
.mb12 { margin-bottom: 12px; }
.login-extra { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.submit-btn { width: 100%; margin-top: 4px; background: var(--primary); border-color: var(--primary); }
.divider {
  display: flex; align-items: center; gap: 8px; margin: 20px 0 12px;
  color: #cbd5e1; font-size: 12px;
}
.divider::before, .divider::after { content: ''; flex: 1; border-top: 1px solid #e2e8f0; }
.wx-btn { width: 100%; }
.foot-tip { text-align: center; font-size: 12px; color: #94a3b8; margin-top: 16px; }
</style>
