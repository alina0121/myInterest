<template>
  <div class="admin-shell">
    <!-- 后台侧边栏（深色，对齐原型 adminScreen） -->
    <aside class="admin-sidebar">
      <div class="admin-brand">
        <div class="admin-logo">息</div>
        <div>
          <div class="admin-name">息计 · 运营后台</div>
          <div class="admin-ver">Admin Console v1.0</div>
        </div>
      </div>
      <nav class="admin-nav">
        <div v-for="item in menus" :key="item.path"
             class="admin-nav-item" :class="{ active: isActive(item.path) }"
             @click="$router.push(item.path)">
          <span>{{ item.icon }}</span><span>{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </div>
      </nav>
      <div class="admin-foot">
        管理员：{{ userStore.user?.username }}<br />
        角色：{{ roleText }}
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="admin-main">
      <header class="admin-topbar">
        <span class="crumb">{{ $route.meta.title }}</span>
        <div class="topbar-right">
          <span class="isolation-tip">后台与用户 App 数据隔离 · 操作留痕</span>
          <el-button @click="$router.push('/')">← 返回前台 App</el-button>
        </div>
      </header>
      <div class="admin-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const menus = [
  { path: '/admin', label: '运营看板', icon: '📊' },
  { path: '/admin/schedules', label: '分红预案审核', icon: '📋' },
  { path: '/admin/users', label: '用户管理', icon: '👥' },
  { path: '/admin/config', label: '汇率与税率', icon: '💱' },
  { path: '/admin/notice', label: '公告与反馈', icon: '📢' },
  { path: '/admin/logs', label: '操作日志', icon: '📝' },
]

const roleText = computed(() =>
  userStore.user?.role === 'super_admin' ? '超级管理员' : '管理员')

function isActive(path) {
  if (path === '/admin') return route.path === '/admin'
  return route.path.startsWith(path)
}
</script>

<style scoped>
.admin-shell { display: flex; min-height: 100vh; background: #f1f5f9; }
.admin-sidebar {
  width: 224px; flex-shrink: 0; background: #0f172a; color: #cbd5e1;
  display: flex; flex-direction: column; position: sticky; top: 0; height: 100vh;
}
.admin-brand { display: flex; align-items: center; gap: 10px; padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.admin-logo {
  width: 32px; height: 32px; border-radius: 8px; background: rgba(255,255,255,0.1);
  color: #fff; font-weight: 700; display: flex; align-items: center; justify-content: center;
}
.admin-name { color: #fff; font-weight: 700; font-size: 14px; }
.admin-ver { font-size: 10px; color: #94a3b8; }
.admin-nav { flex: 1; padding: 12px; }
.admin-nav-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px;
  border-radius: 8px; font-size: 14px; cursor: pointer; margin-bottom: 4px;
  transition: background 0.15s;
}
.admin-nav-item:hover { background: rgba(255,255,255,0.08); }
.admin-nav-item.active { background: rgba(255,255,255,0.12); color: #fff; font-weight: 500; }
.nav-badge {
  margin-left: auto; font-size: 10px; background: #f59e0b; color: #fff;
  border-radius: 9999px; padding: 1px 6px;
}
.admin-foot { padding: 12px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 11px; color: #94a3b8; }

.admin-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.admin-topbar {
  background: #fff; border-bottom: 1px solid #e2e8f0;
  padding: 12px 24px; display: flex; align-items: center; justify-content: space-between;
}
.crumb { font-size: 14px; color: #64748b; }
.topbar-right { display: flex; align-items: center; gap: 16px; }
.isolation-tip { font-size: 12px; color: #94a3b8; }
.admin-content { flex: 1; padding: 24px; overflow-y: auto; }
</style>
