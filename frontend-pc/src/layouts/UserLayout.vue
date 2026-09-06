<template>
  <div class="app-shell">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">息</div>
        <div>
          <div class="brand-name">息计</div>
          <div class="brand-sub">分红记录助手</div>
        </div>
      </div>
      <nav class="nav">
        <div v-for="item in menus" :key="item.path"
             class="nav-item" :class="{ active: isActive(item.path) }"
             @click="$router.push(item.path)">
          <span class="nav-icon">{{ item.icon }}</span><span>{{ item.label }}</span>
        </div>
      </nav>
      <div class="sidebar-foot">v1.0.0 · 支持多批次持仓</div>
    </aside>

    <!-- 主内容区 -->
    <main class="main">
      <header class="topbar">
        <div>
          <h1 class="page-title">{{ $route.meta.title }}</h1>
          <p class="page-sub">记录每一笔分红，见证复利的力量</p>
        </div>
        <div class="topbar-right">
          <el-button v-if="$route.name === 'dashboard'" type="primary" @click="$router.push('/dividends?create=1')">
            + 添加分红
          </el-button>
          <el-dropdown trigger="click" @command="onCommand">
            <div class="user-box">
              <div class="avatar">{{ userStore.nickname.charAt(0).toUpperCase() }}</div>
              <div class="user-meta">
                <div class="user-name">{{ userStore.nickname }}</div>
                <div class="user-hint">点击操作 →</div>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="userStore.isAdmin" command="admin">🛠️ 运营后台</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <div class="page-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../store/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const menus = [
  { path: '/', label: '总览看板', icon: '📊' },
  { path: '/holdings', label: '持仓管理', icon: '📈' },
  { path: '/dividends', label: '分红记录', icon: '💰' },
  { path: '/calendar', label: '分红日历', icon: '📅' },
  { path: '/stats', label: '统计分析', icon: '📉' },
  { path: '/settings', label: '设置', icon: '⚙️' },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

function onCommand(cmd) {
  if (cmd === 'logout') {
    userStore.clear()
    router.push('/login')
  } else if (cmd === 'admin') {
    router.push('/admin')
  }
}
</script>

<style scoped>
.app-shell { display: flex; min-height: 100vh; }
.sidebar {
  width: 224px; flex-shrink: 0; background: #fff;
  border-right: 1px solid #e2e8f0; display: flex; flex-direction: column;
  position: sticky; top: 0; height: 100vh;
}
.brand { display: flex; align-items: center; gap: 10px; padding: 20px; border-bottom: 1px solid #e2e8f0; }
.logo {
  width: 36px; height: 36px; border-radius: 8px; background: var(--primary);
  color: #fff; font-weight: 700; font-size: 20px;
  display: flex; align-items: center; justify-content: center;
}
.brand-name { font-weight: 700; font-size: 15px; }
.brand-sub { font-size: 12px; color: #94a3b8; }
.nav { flex: 1; padding: 12px; }
.nav-item {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px;
  border-radius: 8px; color: #475569; font-size: 14px; cursor: pointer;
  margin-bottom: 4px; transition: background 0.15s;
}
.nav-item:hover { background: #f1f5f9; }
.nav-item.active { background: var(--primary); color: #fff; }
.nav-icon { font-size: 18px; }
.sidebar-foot { padding: 16px; font-size: 12px; color: #cbd5e1; border-top: 1px solid #f1f5f9; }

.main { flex: 1; min-width: 0; }
.topbar {
  background: #fff; border-bottom: 1px solid #e2e8f0;
  padding: 14px 32px; display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 10;
}
.page-title { font-size: 20px; font-weight: 700; margin: 0; }
.page-sub { font-size: 13px; color: #94a3b8; margin: 2px 0 0; }
.topbar-right { display: flex; align-items: center; gap: 16px; }
.user-box { display: flex; align-items: center; gap: 10px; cursor: pointer; outline: none; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%; background: #dbeafe;
  color: var(--primary); font-weight: 600; display: flex; align-items: center; justify-content: center;
}
.user-name { font-size: 14px; font-weight: 500; }
.user-hint { font-size: 12px; color: #94a3b8; }
</style>
