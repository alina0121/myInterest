<template>
  <view class="login-page">
    <view class="hero">
      <view class="logo">息</view>
      <view class="brand">息计</view>
      <view class="slogan">记录每一笔分红，看见复利的力量</view>
    </view>

    <view class="login-card">
      <view class="tabs">
        <view :class="['tab', mode === 'login' ? 'active' : '']" @click="mode = 'login'">登录</view>
        <view :class="['tab', mode === 'register' ? 'active' : '']" @click="mode = 'register'">注册</view>
      </view>

      <view class="form">
        <view class="field">
          <text class="f-label">{{ mode === 'login' ? '账号' : '用户名' }}</text>
          <input class="f-input" v-model="form.account" placeholder="用户名 / 邮箱（注册时为用户名）" />
        </view>
        <view v-if="mode === 'register'" class="field">
          <text class="f-label">邮箱</text>
          <input class="f-input" v-model="form.email" placeholder="选填" />
        </view>
        <view class="field">
          <text class="f-label">密码</text>
          <input class="f-input" v-model="form.password" password placeholder="至少 8 位" />
        </view>
        <view v-if="mode === 'register'" class="field">
          <text class="f-label">昵称</text>
          <input class="f-input" v-model="form.nickname" placeholder="选填" />
        </view>

        <button class="btn-primary submit" :loading="loading" @click="submit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </button>
        <view v-if="mode === 'login'" class="hint">还没有账号？<text class="link" @click="mode = 'register'">立即注册</text></view>
        <view v-else class="hint">已有账号？<text class="link" @click="mode = 'login'">返回登录</text></view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { apiLogin, apiRegister } from '@/api'
import { setAuth } from '@/store/user'

const mode = ref('login')
const loading = ref(false)
const form = reactive({ account: '', email: '', password: '', nickname: '' })

async function submit() {
  if (!form.account || !form.password) {
    return uni.showToast({ title: '请填写账号和密码', icon: 'none' })
  }
  if (mode.value === 'register' && form.password.length < 8) {
    return uni.showToast({ title: '密码至少 8 位', icon: 'none' })
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
    setAuth(data.access_token, data.user)
    uni.showToast({ title: mode.value === 'login' ? '登录成功' : '注册成功', icon: 'success' })
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 400)
  } catch (e) {
    // 错误 toast 已由 request 统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { min-height: 100vh; background: linear-gradient(180deg, #1668dc 0%, #3b82f6 42%, #f3f6fb 42%); }
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
  padding: 20rpx 40rpx 50rpx; box-shadow: 0 12rpx 40rpx rgba(22,104,220,0.12);
}
.tabs { display: flex; border-bottom: 1rpx solid #f1f5f9; }
.tab {
  flex: 1; text-align: center; padding: 30rpx 0; font-size: 30rpx;
  color: #94a3b8; position: relative;
}
.tab.active { color: #1668dc; font-weight: 600; }
.tab.active::after {
  content: ''; position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: 60rpx; height: 6rpx; border-radius: 3rpx; background: #1668dc;
}
.field { padding: 26rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.f-label { display: block; font-size: 24rpx; color: #94a3b8; margin-bottom: 12rpx; }
.f-input { font-size: 30rpx; height: 44rpx; }
.submit { margin-top: 50rpx; }
.hint { text-align: center; margin-top: 28rpx; font-size: 26rpx; color: #94a3b8; }
.link { color: #1668dc; }
</style>
