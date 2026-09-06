/** 全局用户态（轻量 reactive，三端一致；docs/05 §2 token 存储策略） */
import { reactive } from 'vue'
import { TOKEN_KEY, USER_KEY } from '@/utils/config'

export const userStore = reactive({
  token: uni.getStorageSync(TOKEN_KEY) || '',
  user: uni.getStorageSync(USER_KEY) || null,
})

export function setAuth(token, user) {
  userStore.token = token
  userStore.user = user
  uni.setStorageSync(TOKEN_KEY, token)
  uni.setStorageSync(USER_KEY, user)
}

export function updateUser(user) {
  userStore.user = user
  uni.setStorageSync(USER_KEY, user)
}

export function clearAuth() {
  userStore.token = ''
  userStore.user = null
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(USER_KEY)
}
