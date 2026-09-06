/**
 * 环境与接口地址配置（docs/05-前端三端设计.md §2 baseUrl 策略）
 * - H5 开发：直连本机 8000 端口（CORS 已全开）
 * - 微信开发者工具：urlCheck 关闭时可直连 127.0.0.1（同机调试）
 * - 真机预览/发布：改为局域网 IP 或 https 备案域名
 */
// #ifdef H5
export const BASE_URL = 'http://127.0.0.1:8000'
// #endif
// #ifndef H5
export const BASE_URL = 'http://127.0.0.1:8000'
// #endif

export const TOKEN_KEY = 'xi_token'
export const USER_KEY = 'xi_user'
