<template>
  <view class="login-page">
    <view class="hero">
      <view class="logo">攒</view>
      <view class="brand">攒息</view>
      <view class="slogan">时间的朋友 · 记录每一笔分红</view>
    </view>

    <view class="login-card">
      <!-- 微信小程序端：一键登录（必须用户点击触发；H5/App 不编译此块） -->
      <!-- #ifdef MP-WEIXIN -->
      <view class="wx-block">
        <button class="btn-wx" :loading="wxLoading" @click="onWxLogin">
          <text class="wx-icon">✦</text> 微信一键登录
        </button>
        <view class="hint wx-hint">登录后可在「我的」中绑定邮箱</view>
        <view class="divider"><text class="divider-text">或 用邮箱验证码登录</text></view>
      </view>
      <!-- #endif -->

      <!-- 邮箱验证码：登录/注册合一（未注册邮箱自动建号，参考 eatWhat） -->
      <view class="form">
        <view class="field">
          <text class="f-label">邮箱</text>
          <input class="f-input" v-model="emailForm.email" placeholder="请输入邮箱地址" />
        </view>
        <view class="field code-field">
          <text class="f-label">验证码</text>
          <view class="code-row">
            <input class="f-input code-input" v-model="emailForm.code" placeholder="6 位验证码" />
            <button class="btn-code" :disabled="cooldown > 0" @click="sendCode">
              {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
            </button>
          </view>
        </view>
        <button class="btn-primary submit" :loading="loading" @click="submitEmail">
          登录 / 注册
        </button>
        <view class="hint">未注册的邮箱验证通过后将自动创建账号</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { apiWxLogin, apiSendCode, apiEmailLogin } from '@/api'
import { setAuth } from '@/store/user'

const loading = ref(false)
const wxLoading = ref(false)
const cooldown = ref(0)

const emailForm = reactive({ email: '', code: '' })

// ---------- 邮箱验证码（登录/注册合一） ----------
async function sendCode() {
  if (!emailForm.email) {
    return uni.showToast({ title: '请先填写邮箱', icon: 'none' })
  }
  try {
    await apiSendCode('email', emailForm.email, 'login')
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
    // 未注册邮箱由后端自动建号，无需区分登录/注册
    const data = await apiEmailLogin(emailForm.email, emailForm.code)
    setAuth(data.access_token, data.user)
    uni.showToast({ title: data.is_new_user ? '注册并登录成功' : '登录成功', icon: 'success' })
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 400)
  } catch (e) {
    // 错误已统一处理
  } finally {
    loading.value = false
  }
}

// ---------- 微信小程序一键登录（仅 MP-WEIXIN 编译，H5/App 不存在该函数调用） ----------
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
    // 微信新用户引导绑定邮箱（对齐 eatWhat redirect=bind）
    const url = data.is_new_user ? '/pages/mine/mine?bind=1' : '/pages/index/index'
    setTimeout(() => uni.reLaunch({ url }), 400)
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
  padding: 44rpx 40rpx 50rpx; box-shadow: 0 12rpx 40rpx rgba(30,58,138,0.12);
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

/* 微信一键登录块（仅小程序渲染） */
.wx-block { margin-bottom: 10rpx; }
.btn-wx {
  background: #07c160; color: #fff; border-radius: 44rpx;
  font-size: 30rpx; height: 88rpx; line-height: 88rpx; text-align: center;
  border: none; display: flex; align-items: center; justify-content: center;
}
.btn-wx::after { border: none; }
.wx-icon { margin-right: 10rpx; font-size: 32rpx; }
.wx-hint { margin-top: 20rpx; }

.divider { display: flex; align-items: center; margin: 34rpx 0 6rpx; }
.divider::before, .divider::after {
  content: ''; flex: 1; height: 1rpx; background: #e2e8f0;
}
.divider-text {
  padding: 0 20rpx; font-size: 24rpx; color: #94a3b8;
}

.hint { text-align: center; margin-top: 28rpx; font-size: 26rpx; color: #94a3b8; }
</style>
