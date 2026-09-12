/** 全局用户态（轻量 reactive，三端一致；docs/05 §2 token 存储策略）
 *
 * v8：增加 currentAccount（账户切换）与 displayCurrency（显示币种转换）状态。
 *     都持久化到 uni storage，登录后从 /api/settings 预取。
 *     displayCurrency：单值 'CNY' / 'USD' / 'HKD' / 'ORIGINAL'（本币按原币种显示）
 */
import { reactive } from 'vue'
import { TOKEN_KEY, USER_KEY } from '@/utils/config'

const ACCOUNT_KEY = 'xi_current_account'
const CURRENCY_KEY = 'xi_display_currency'

export const userStore = reactive({
  token: uni.getStorageSync(TOKEN_KEY) || '',
  user: uni.getStorageSync(USER_KEY) || null,
  // v8：账户切换 + 显示币种
  currentAccount: uni.getStorageSync(ACCOUNT_KEY) || '__all__',
  displayCurrency: uni.getStorageSync(CURRENCY_KEY) || 'CNY',
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
  userStore.currentAccount = '__all__'
  userStore.displayCurrency = 'CNY'
  uni.removeStorageSync(TOKEN_KEY)
  uni.removeStorageSync(USER_KEY)
  uni.removeStorageSync(ACCOUNT_KEY)
  uni.removeStorageSync(CURRENCY_KEY)
}

/** v8：设置当前账户（'__all__' 或具体账户名字符串） */
export function setCurrentAccount(account) {
  userStore.currentAccount = account || '__all__'
  uni.setStorageSync(ACCOUNT_KEY, userStore.currentAccount)
}

/** v8：设置显示币种（'CNY' / 'USD' / 'HKD' / 'ORIGINAL'） */
export function setDisplayCurrency(currency) {
  userStore.displayCurrency = currency || 'CNY'
  uni.setStorageSync(CURRENCY_KEY, userStore.displayCurrency)
}

/** v8：从 settings 接口同步账户/币种配置（登录或打开 mine 页时调用） */
export function syncFromSettings(settings) {
  if (!settings) return
  if (settings.display_currency) {
    setDisplayCurrency(settings.display_currency)
  }
}
