<template>
  <view class="login-page">
    <view class="hero">
      <view class="logo">攒</view>
      <view class="brand">攒息</view>
      <view class="slogan">时间的朋友 · 记录每一笔分红</view>
    </view>

    <view class="login-card">
      <view class="tabs">
        <view :class="['tab', mode === 'pwd' ? 'active' : '']" @click="mode = 'pwd'">密码登录</view>
        <view :class="['tab', mode === 'email' ? 'active' : '']" @click="mode = 'email'">邮箱验证码</view>
        <!-- #ifdef MP-WEIXIN -->
        <view :class="['tab', mode === 'wx' ? 'active' : '']" @click="mode = 'wx'">微信</view>
        <!-- #endif -->
      </view>

      <!-- 密码登录 / 注册 -->
      <view v-if="mode === 'pwd'" class="form">
        <view class="field">
          <text class="f-label">{{ subMode === 'login' ? '账号' : '用户名' }}</text>
          <input class="f-input" v-model="pwdForm.account" placeholder="用户名 / 邮箱（注册时为用户名）" />
        </view>
        <view v-if="subMode === 'register'" class="field">
          <text class="f-label">邮箱</text>
          <input class="f-input" v-model="pwdForm.email" placeholder="选填" />
        </view>
        <view class="field">
          <text class="f-label">密码</text>
          <input class="f-input" v-model="pwdForm.password" password placeholder="至少 8 位" />
        </view>
        <view v-if="subMode === 'register'" class="field">
          <text class="f-label">昵称</text>
          <input class="f-input" v-model="pwdForm.nickname" placeholder="选填" />
        </view>
        <button class="btn-primary submit" :loading="loading" @click="submitPwd">
          {{ subMode === 'login' ? '登 录' : '注 册' }}
        </button>
        <view class="hint">
          <text v-if="subMode === 'login'">还没有账号？<text class="link" @click="subMode = 'register'">立即注册</text></text>
          <text v-else>已有账号？<text class="link" @click="subMode = 'login'">返回登录</text></text>
        </view>
      </view>

      <!-- 邮箱验证码登录 / 注册 -->
      <view v-else-if="mode === 'email'" class="form">
        <view class="field">
          <text class="f-label">邮箱</text>
          <input class="f-input" v-model="emailForm.email" placeholder="请输入邮箱地址" />
        </view>
        <view class="field code-field">
          <text class="f-label">验证码</text>
          <view class="code-row">
            <input class="f-input code-input" v-model="emailForm.code" placeholder="6 位验证码" />
            <button class="btn-code" :disabled="cooldown > 0" @click="sendCode('email')">
              {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
            </button>
          </view>
        </view>
        <view v-if="subMode === 'register'" class="field">
          <text class="f-label">昵称（选填）</text>
          <input class="f-input" v-model="emailForm.nickname" placeholder="留空则用邮箱前缀" />
        </view>
        <view v-if="subMode === 'register'" class="field">
          <text class="f-label">密码（选填）</text>
          <input class="f-input" v-model="emailForm.password" password placeholder="设密码后可用密码登录" />
        </view>
        <button class="btn-primary submit" :loading="loading" @click="submitEmail">
          {{ subMode === 'login' ? '登 录' : '注 册' }}
        </button>
        <view class="hint">
          <text v-if="subMode === 'login'">没有账号？<text class="link" @click="subMode = 'register'">立即注册</text></text>
          <text v-else>已有账号？<text class="link" @click="subMode = 'login'">返回登录</text></text>
        </view>
      </view>

      <!-- 微信小程序端：一键登录（docs/05 §3 微信登录，必须用户点击触发） -->
      <!-- #ifdef MP-WEIXIN -->
      <view v-else class="form">
        <view class="wx-tip">点击下方按钮使用微信一键登录</view>
        <button class="btn-wx" :loading="wxLoading" @click="onWxLogin">
          <text class="wx-icon">✦</text> 微信一键登录
        </button>
        <view class="hint">登录后可在「我的」中绑定邮箱</view>
      </view>
      <!-- #endif -->

      <!-- 切换其他登录方式 -->
      <view class="divider" v-if="mode !== 'wx'"><text class="divider-text">其他方式</text></view>
      <view class="other-methods" v-if="mode !== 'wx'">
        <!-- #ifdef MP-WEIXIN -->
        <text class="link-small" @click="mode = 'wx'">微信登录</text>
        <!-- #endif -->
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import {
  apiLogin, apiRegister, apiWxLogin,
  apiSendCode, apiEmailLogin, apiEmailRegister,
} from '@/api'
import { setAuth } from '@/store/user'

const mode = ref('pwd')        // pwd / email / wx
const subMode = ref('login')   // login / register
const loading = ref(false)
const wxLoading = ref(false)
const cooldown = ref(0)

const pwdForm = reactive({ account: '', email: '', password: '', nickname: '' })
const emailForm = reactive({ email: '', code: '', nickname: '', password: '' })

// ---------- 密码登录/注册 ----------
async function submitPwd() {
  if (!pwdForm.account || !pwdForm.password) {
    return uni.showToast({ title: '请填写账号和密码', icon: 'none' })
  }
  if (subMode.value === 'register' && pwdForm.password.length < 8) {
    return uni.showToast({ title: '密码至少 8 位', icon: 'none' })
  }
  loading.value = true
  try {
    let data
    if (subMode.value === 'login') {
      data = await apiLogin(pwdForm.account, pwdForm.password)
    } else {
      data = await apiRegister({
        username: pwdForm.account,
        email: pwdForm.email || null,
        password: pwdForm.password,
        nickname: pwdForm.nickname || pwdForm.account,
      })
    }
    setAuth(data.access_token, data.user)
    uni.showToast({ title: subMode.value === 'login' ? '登录成功' : '注册成功', icon: 'success' })
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 400)
  } catch (e) {
    // 错误 toast 已由 request 统一处理
  } finally {
    loading.value = false
  }
}

// ---------- 邮箱验证码 ----------
async function sendCode(channel) {
  if (channel === 'email' && !emailForm.email) {
    return uni.showToast({ title: '请先填写邮箱', icon: 'none' })
  }
  try {
    const purpose = subMode.value === 'register' ? 'register' : 'login'
    await apiSendCode(channel, emailForm.email, purpose)
    uni.showToast({ title: '验证码已发送', icon: 'none' })
    // 启动 60 秒倒计时
    cooldown.value = 60
    const timer = setInterval(() => {
      cooldown.value -= 1
      if (cooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) {
    // 错误已统一处理
  }
}

async function submitEmail() {
  if (!emailForm.email || !emailForm.code) {
    return uni.showToast({ title: '请填写邮箱和验证码', icon: 'none' })
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
    setAuth(data.access_token, data.user)
    uni.showToast({ title: subMode.value === 'login' ? '登录成功' : '注册成功', icon: 'success' })
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 400)
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ---------- 微信小程序一键登录 ----------
async function onWxLogin() {
  if (wxLoading.value) return
  wxLoading.value = true
  try {
    // 1. wx.login 拿临时 code
    const loginRes = await new Promise((resolve, reject) => {
      uni.login({ provider: 'weixin', success: resolve, fail: reject })
    })
    if (!loginRes.code) throw new Error('微信登录失败：未获取到 code')

    // 2. 尝试获取昵称头像（用户拒绝也可登录，只是无资料）
    let nickname = null, avatar = null
    try {
      const profile = await new Promise((resolve, reject) => {
        uni.getUserProfile({ desc: '用于完善会员资料', success: resolve, fail: reject })
      })
      nickname = profile.userInfo?.nickName || null
      avatar = profile.userInfo?.avatarUrl || null
    } catch (e) {
      // 用户拒绝授权头像昵称，仍可登录
    }

    // 3. 调后端 wx-login 换 token
    const data = await apiWxLogin(loginRes.code, nickname, avatar)
    setAuth(data.access_token, data.user)
    uni.showToast({ title: data.is_new_user ? '登录成功' : '欢迎回来', icon: 'success' })
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 400)
  } catch (e) {
    // 错误 toast 已由 request 统一处理
  } finally {
    wxLoading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; background: linear-gradient(180deg, #1e3a8a 0%, #3b82f6 42%, #f8fafc 42%); }
.hero { text-align: center; padding: 110rpx 0 70rpx; color: #fff; }
.logo {
  width: 120rpx; height: 120rpx; line-height: 120rpx; margin: 0 auto;
  background: rgba(255,255,255,0.18); border: 2rpx solid rgba(255,255,255,0.5);
  border-radius: 30rpx; font-size: 60rpx; font-weight: 700;
}
.brand { font-size: 44rpx; font-weight: 700; margin-top: 24rpx; }
.slogan { font-size: 26rpx; opacity: 0.85; margin-top: 12rpx; }
.login-card {
  background: #fff; border-radius: 28rpx; margin: 0 40rpx;
  padding: 20rpx 40rpx 50rpx; box-shadow: 0 12rpx 40rpx rgba(30,58,138,0.12);
}
.tabs { display: flex; border-bottom: 1rpx solid #f1f5f9; }
.tab {
  flex: 1; text-align: center; padding: 30rpx 0; font-size: 30rpx;
  color: #94a3b8; position: relative;
}
.tab.active { color: #1e3a8a; font-weight: 600; }
.tab.active::after {
  content: ''; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 60rpx; height: 6rpx; border-radius: 3rpx; background: #1e3a8a;
}
.field { padding: 26rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.f-label { display: block; font-size: 24rpx; color: #94a3b8; margin-bottom: 12rpx; }
.f-input { font-size: 30rpx; height: 44rpx; }
.submit { margin-top: 50rpx; }

/* 验证码行 */
.code-field { border-bottom: none; padding-bottom: 0; }
.code-row { display: flex; align-items: center; gap: 16rpx; }
.code-input { flex: 1; }
.btn-code {
  flex-shrink: 0; min-width: 180rpx; height: 60rpx; line-height: 60rpx;
  font-size: 24rpx; padding: 0 16rpx; margin: 0;
  background: #1e3a8a; color: #fff; border-radius: 12rpx; border: none;
}
.btn-code[disabled] { background: #94a3b8; }
.btn-code::after { border: none; }

.wx-tip { padding: 40rpx 0; font-size: 26rpx; color: #94a3b8; text-align: center; }

.divider {
  display: flex; align-items: center; margin: 40rpx 0 24rpx;
}
.divider::before, .divider::after {
  content: ''; flex: 1; height: 1rpx; background: #e2e8f0;
}
.divider-text {
  padding: 0 20rpx; font-size: 24rpx; color: #94a3b8;
}
.other-methods { text-align: center; }
.link-small { font-size: 26rpx; color: #1e3a8a; }

.btn-wx {
  background: #07c160; color: #fff; border-radius: 44rpx;
  font-size: 30rpx; height: 88rpx; line-height: 88rpx; text-align: center;
  border: none; display: flex; align-items: center; justify-content: center;
}
.btn-wx::after { border: none; }
.wx-icon { margin-right: 10rpx; font-size: 32rpx; }
.hint { text-align: center; margin-top: 28rpx; font-size: 26rpx; color: #94a3b8; }
.link { color: #1e3a8a; }
</style>
