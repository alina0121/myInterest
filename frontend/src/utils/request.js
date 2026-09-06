/**
 * 统一请求封装（docs/05 §2 契约）：
 * - 自动携带 JWT，统一解包 {code,msg,data}
 * - 未登录/token 失效（1002/1003）：清登录态并跳登录页
 * - 业务错误（如 2001 密码错误、2002 用户名已存在）：仅 toast 后端 msg
 */
import { BASE_URL, TOKEN_KEY, USER_KEY } from './config'

function redirectToLogin() {
  const pages = getCurrentPages()
  const route = pages.length ? pages[pages.length - 1].route : ''
  if (route !== 'pages/login/login') {
    setTimeout(() => uni.reLaunch({ url: '/pages/login/login' }), 300)
  }
}

export function request(options) {
  const { url, method = 'GET', data = {}, auth = true, silent = false } = options

  // 拦截：需要登录但本地无 token → 直接跳登录，不发请求（避免启动竞态刷 401）
  const token = uni.getStorageSync(TOKEN_KEY)
  if (auth && !token) {
    redirectToLogin()
    return Promise.reject({ code: 1002, msg: '未登录' })
  }

  return new Promise((resolve, reject) => {
    const header = { 'Content-Type': 'application/json' }
    if (auth && token) header.Authorization = 'Bearer ' + token

    uni.request({
      url: BASE_URL + url,
      method,
      data,
      header,
      timeout: 15000,
      success: (res) => {
        const body = res.data || {}
        if (body.code === 0) {
          return resolve(body.data)
        }
        // 1002 未登录 / 1003 token 失效 → 清登录态跳登录
        if ([1002, 1003].includes(body.code)) {
          uni.removeStorageSync(TOKEN_KEY)
          uni.removeStorageSync(USER_KEY)
          if (!silent) {
            uni.showToast({ title: '登录已过期，请重新登录', icon: 'none' })
          }
          redirectToLogin()
          return reject(body)
        }
        // 其他业务错误（2001 密码错误 / 2002 已存在 / 3001 / 4001 / 4002 …）
        if (!silent) {
          uni.showToast({ title: body.msg || '请求失败', icon: 'none' })
        }
        reject(body)
      },
      fail: (err) => {
        if (!silent) {
          uni.showToast({ title: '网络连接失败，请检查后端服务', icon: 'none' })
        }
        reject(err)
      },
    })
  })
}

export const get = (url, data, opts = {}) => request({ url, method: 'GET', data, ...opts })
export const post = (url, data, opts = {}) => request({ url, method: 'POST', data, ...opts })
export const patch = (url, data, opts = {}) => request({ url, method: 'PATCH', data, ...opts })
export const del = (url, data, opts = {}) => request({ url, method: 'DELETE', data, ...opts })
export const put = (url, data, opts = {}) => request({ url, method: 'PUT', data, ...opts })
