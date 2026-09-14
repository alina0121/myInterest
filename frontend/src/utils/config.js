/**
 * 环境与接口地址配置（docs/05-前端三端设计.md §2 baseUrl 策略）
 * - H5 生产：走同域相对路径，/api 由 Caddy 反代到后端（mobile.icefun.cn）
 * - 小程序：同域相对路径（经配置的合法域名/代理）
 * - 真机调试：如需改地址，把 BASE_URL 改成局域网 IP 或 https 域名
 */
// #ifdef H5
// 生产走同域相对路径：/api 由 Caddy 反代到后端（mobile.icefun.cn）
export const BASE_URL = ''
// #endif
// #ifndef H5
export const BASE_URL = ''
// #endif

export const TOKEN_KEY = 'xi_token'
export const USER_KEY = 'xi_user'
