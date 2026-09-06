import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'
import router from '../router'

const http = axios.create({ baseURL: '', timeout: 15000 })

http.interceptors.request.use((config) => {
  const user = useUserStore()
  if (user.token && !config.headers.noAuth) {
    config.headers.Authorization = `Bearer ${user.token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => {
    const body = res.data || {}
    if (body.code === 0) return body.data
    // 1002 未登录 / 1003 token 失效 → 跳登录
    if ([1002, 1003].includes(body.code)) {
      const user = useUserStore()
      user.clear()
      ElMessage.warning('登录已过期，请重新登录')
      router.push('/login')
      return Promise.reject(body)
    }
    // 1004 无权限（管理接口）
    if (body.code === 1004) {
      ElMessage.error('无权限访问')
      return Promise.reject(body)
    }
    ElMessage.error(body.msg || '请求失败')
    return Promise.reject(body)
  },
  (err) => {
    // HTTP 401：后端业务码 2001 密码错误等也返回 401，尝试读取 body
    const body = err.response?.data || {}
    if ([1002, 1003].includes(body.code)) {
      const user = useUserStore()
      user.clear()
      ElMessage.warning('登录已过期，请重新登录')
      router.push('/login')
    } else if (body.msg) {
      ElMessage.error(body.msg)
    } else {
      ElMessage.error('网络连接失败，请检查后端服务')
    }
    return Promise.reject(body)
  },
)

export const get = (url, params) => http.get(url, { params })
export const post = (url, data) => http.post(url, data)
export const put = (url, data) => http.put(url, data)
export const httpPatch = (url, data) => http.patch(url, data)
export const del = (url) => http.delete(url)
export default http
