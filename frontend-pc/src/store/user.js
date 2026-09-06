import { defineStore } from 'pinia'

const TOKEN_KEY = 'xiji_pc_token'
const USER_KEY = 'xiji_pc_user'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
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
    clear() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})
