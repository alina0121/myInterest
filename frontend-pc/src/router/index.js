import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layouts/UserLayout.vue'),
    children: [
      { path: '', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '总览看板' } },
      { path: 'holdings', name: 'holdings', component: () => import('../views/Holdings.vue'), meta: { title: '持仓管理' } },
      { path: 'holdings/:id', name: 'holdingDetail', component: () => import('../views/HoldingDetail.vue'), meta: { title: '持仓详情' } },
      { path: 'dividends', name: 'dividends', component: () => import('../views/Dividends.vue'), meta: { title: '分红记录' } },
      { path: 'calendar', name: 'calendar', component: () => import('../views/Calendar.vue'), meta: { title: '分红日历' } },
      { path: 'stats', name: 'stats', component: () => import('../views/Stats.vue'), meta: { title: '统计分析' } },
      { path: 'settings', name: 'settings', component: () => import('../views/Settings.vue'), meta: { title: '设置' } },
    ],
  },
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requiresAdmin: true },
    children: [
      { path: '', name: 'adminDashboard', component: () => import('../views/admin/Dashboard.vue'), meta: { title: '运营看板' } },
      { path: 'schedules', name: 'adminSchedules', component: () => import('../views/admin/Schedules.vue'), meta: { title: '分红预案审核' } },
      { path: 'securities', name: 'adminSecurities', component: () => import('../views/admin/Securities.vue'), meta: { title: '证券与白名单' } },
      { path: 'users', name: 'adminUsers', component: () => import('../views/admin/Users.vue'), meta: { title: '用户管理' } },
      { path: 'config', name: 'adminConfig', component: () => import('../views/admin/Config.vue'), meta: { title: '汇率与税率' } },
      { path: 'notice', name: 'adminNotice', component: () => import('../views/admin/Notice.vue'), meta: { title: '公告与反馈' } },
      { path: 'logs', name: 'adminLogs', component: () => import('../views/admin/Logs.vue'), meta: { title: '操作日志' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const user = useUserStore()
  if (!to.meta.public && !user.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !user.isAdmin) {
    return { path: '/' }
  }
  document.title = to.meta.title ? `${to.meta.title} · 攒息` : '攒息'
  return true
})

export default router
