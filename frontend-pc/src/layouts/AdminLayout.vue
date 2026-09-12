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
          <div v-for="item in menus" :key="item.path"
               class="nav-item" :class="{ active: isActive(item.path) }"
               @click="$router.push(item.path)">
            <span>{{ item.icon }}</span><span>{{ item.label }}</span>
          </div>
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
import { useRoute } from 'vue-router'
import { useUserStore } from '../store/user'

const route = useRoute()
const userStore = useUserStore()

const menus = [
  { path: '/admin', label: '运营看板', icon: '📊' },
  { path: '/admin/schedules', label: '分红预案审核', icon: '📋' },
  { path: '/admin/securities', label: '证券与白名单', icon: '🏷️' },
  { path: '/admin/users', label: '用户管理', icon: '👥' },
  { path: '/admin/login-methods', label: '系统参数配置', icon: '🔐' },
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
.admin-shell { min-height: 100vh; display: flex; flex-direction: column; background: #f1f5f9; }

/* 顶部导航栏（深色） */
.admin-topbar {
  height: 60px; background: #0f172a; color: #cbd5e1;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.topbar-left { display: flex; align-items: center; gap: 32px; }

.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
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
  transition: all 0.15s; white-space: nowrap; color: #94a3b8;
}
.nav-item:hover { background: rgba(255,255,255,0.08); color: #fff; }
.nav-item.active { background: rgba(255,255,255,0.15); color: #fff; font-weight: 500; }

.topbar-right { display: flex; align-items: center; gap: 16px; }
.isolation-tip { font-size: 12px; color: #64748b; }
.admin-meta { display: flex; align-items: center; gap: 8px; }
.admin-name { font-size: 13px; color: #cbd5e1; }

.admin-main { flex: 1; display: flex; flex-direction: column; }
.page-header { padding: 20px 28px 0; }
.page-title { font-size: 20px; font-weight: 700; margin: 0; color: #0f172a; }
.admin-content { flex: 1; padding: 16px 28px 28px; }
</style>
