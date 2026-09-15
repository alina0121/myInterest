<template>
  <div class="admin-shell">
    <!-- 顶部导航栏（深色，区分前台） -->
    <header class="admin-topbar">
      <div class="topbar-left">
        <div class="brand" @click="$router.push('/admin')">
          <div class="logo">攒</div>
          <div class="brand-text">
            <div class="brand-name">攒息 · 运营后台</div>
            <div class="brand-sub">Admin Console</div>
          </div>
        </div>
        <nav class="admin-nav">
          <!-- 一级菜单：无二级的直接点击跳转 -->
          <div v-for="item in flatMenus" :key="item.path"
               class="nav-item" :class="{ active: isActive(item.path) }"
               @click="$router.push(item.path)">
            <span>{{ item.icon }}</span><span>{{ item.label }}</span>
          </div>
          <!-- 二级菜单：hover 展开下拉 -->
          <el-dropdown v-for="item in groupMenus" :key="item.label" trigger="hover"
                       @command="onNavCommand">
            <div class="nav-item" :class="{ active: isMenuActive(item) }">
              <span>{{ item.icon }}</span><span>{{ item.label }}</span>
              <span class="caret">▾</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="c in item.children" :key="c.path"
                                  :command="c.path"
                                  :class="{ 'is-active': isActive(c.path) }">
                  {{ c.label }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </nav>
      </div>
      <div class="topbar-right">
        <span class="isolation-tip">数据隔离 · 操作留痕</span>
        <div class="admin-meta">
          <span class="admin-name">{{ userStore.user?.username }}</span>
          <el-tag size="small" type="warning">{{ roleText }}</el-tag>
        </div>
        <el-button @click="$router.push('/')">← 返回前台</el-button>
      </div>
    </header>

    <!-- 主内容区 -->
    <div class="admin-main">
      <div class="page-header">
        <h1 class="page-title">{{ $route.meta.title }}</h1>
      </div>
      <div class="admin-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 菜单：一级项直接展示；含 children 的为二级下拉（hover 展开）
const menus = [
  { path: '/admin', label: '运营看板', icon: '📊' },
  {
    label: '业务管理', icon: '📋',
    children: [
      { path: '/admin/schedules', label: '分红预案审核' },
      { path: '/admin/securities', label: '证券与白名单' },
    ],
  },
  { path: '/admin/users', label: '用户管理', icon: '👥' },
  {
    label: '系统设置', icon: '⚙️',
    children: [
      { path: '/admin/login-methods', label: '系统参数配置' },
      { path: '/admin/config', label: '汇率与税率' },
    ],
  },
  {
    label: '运营工具', icon: '🛠️',
    children: [
      { path: '/admin/notice', label: '公告与反馈' },
      { path: '/admin/logs', label: '操作日志' },
    ],
  },
]

const flatMenus = computed(() => menus.filter(m => !m.children))
const groupMenus = computed(() => menus.filter(m => m.children))

const roleText = computed(() =>
  userStore.user?.role === 'super_admin' ? '超级管理员' : '管理员')

function isActive(path) {
  if (path === '/admin') return route.path === '/admin'
  return route.path.startsWith(path)
}

// 二级菜单任一路由激活时，一级菜单高亮
function isMenuActive(item) {
  return item.children.some(c => isActive(c.path))
}

// 点击二级菜单项跳转
function onNavCommand(path) {
  router.push(path)
}
</script>

<style scoped>
.admin-shell { min-height: 100vh; display: flex; flex-direction: column; background: #f1f5f9; }

/* 顶部导航栏（深色） */
.admin-topbar {
  height: 60px; background: #0f172a; color: #cbd5e1;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.topbar-left { display: flex; align-items: center; gap: 32px; min-width: 0; }

.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; flex-shrink: 0; }
.logo {
  width: 34px; height: 34px; border-radius: 8px; background: rgba(255,255,255,0.12);
  color: #fff; font-weight: 700; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
}
.brand-text { line-height: 1.2; }
.brand-name { color: #fff; font-weight: 700; font-size: 15px; letter-spacing: 0.5px; }
.brand-sub { font-size: 10px; color: #64748b; }

.admin-nav { display: flex; align-items: center; gap: 2px; }
.nav-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 14px;
  border-radius: 8px; font-size: 14px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap; color: #94a3b8; outline: none;
}
.nav-item:hover { background: rgba(255,255,255,0.08); color: #fff; }
.nav-item.active { background: rgba(255,255,255,0.15); color: #fff; font-weight: 500; }
.caret { font-size: 10px; color: #64748b; }
.nav-item.active .caret { color: #94a3b8; }

.topbar-right { display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
.isolation-tip { font-size: 12px; color: #64748b; }
.admin-meta { display: flex; align-items: center; gap: 8px; }
.admin-name { font-size: 13px; color: #cbd5e1; }

/* 下拉菜单中当前激活的子项高亮 */
:deep(.el-dropdown-menu__item.is-active) {
  color: var(--el-color-primary); font-weight: 600;
}

.admin-main { flex: 1; display: flex; flex-direction: column; }
.page-header { padding: 20px 28px 0; }
.page-title { font-size: 20px; font-weight: 700; margin: 0; color: #0f172a; }
.admin-content { flex: 1; padding: 16px 28px 28px; }

/* 窄屏兜底：菜单允许横向滚动，避免挤压 */
@media (max-width: 1100px) {
  .admin-nav { overflow-x: auto; scrollbar-width: none; }
  .admin-nav::-webkit-scrollbar { display: none; }
  .isolation-tip { display: none; }
}
</style>
