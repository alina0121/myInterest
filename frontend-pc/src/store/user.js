import { defineStore } from 'pinia'

const TOKEN_KEY = 'xiji_pc_token'
const USER_KEY = 'xiji_pc_user'
const ACCOUNT_KEY = 'xiji_pc_current_account'
const CURRENCY_KEY = 'xiji_pc_display_currency'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
    // v8：账户切换 + 显示币种转换（单值，持久化到 localStorage）
    // displayCurrency: 'CNY' / 'USD' / 'HKD' / 'ORIGINAL'(本币按原币种显示)
    currentAccount: localStorage.getItem(ACCOUNT_KEY) || '__all__',
    displayCurrency: localStorage.getItem(CURRENCY_KEY) || 'CNY',
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => ['admin', 'super_admin'].includes(s.user?.role || ''),
    nickname: (s) => s.user?.nickname || s.user?.username || '用户',
  },
  actions: {
    setAuth(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem(TOKEN_KEY, token)
      localStorage.setItem(USER_KEY, JSON.stringify(user))
    },
    /** v8：设置当前账户（'__all__' 或具体账户名字符串） */
    setCurrentAccount(account) {
      this.currentAccount = account || '__all__'
      localStorage.setItem(ACCOUNT_KEY, this.currentAccount)
    },
    /** v8：设置显示币种（'CNY' / 'USD' / 'HKD' / 'ORIGINAL'） */
    setDisplayCurrency(currency) {
      this.displayCurrency = currency || 'CNY'
      localStorage.setItem(CURRENCY_KEY, this.displayCurrency)
    },
    /** v8：从 settings 接口同步显示币种配置（登录或打开设置页时调用） */
    syncFromSettings(settings) {
      if (!settings) return
      if (settings.display_currency) {
        this.setDisplayCurrency(settings.display_currency)
      }
    },
    clear() {
      this.token = ''
      this.user = null
      this.currentAccount = '__all__'
      this.displayCurrency = 'CNY'
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      localStorage.removeItem(ACCOUNT_KEY)
      localStorage.removeItem(CURRENCY_KEY)
    },
  },
})
