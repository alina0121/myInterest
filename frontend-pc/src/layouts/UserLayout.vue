<template>
  <div class="app-shell">
    <!-- 顶部导航栏 -->
    <header class="topbar">
      <div class="topbar-left">
        <div class="brand" @click="$router.push('/')">
          <div class="logo">攒</div>
          <div class="brand-text">
            <div class="brand-name">攒息</div>
            <div class="brand-sub">时间的朋友</div>
          </div>
        </div>
        <nav class="nav">
          <div v-for="item in menus" :key="item.path"
               class="nav-item" :class="{ active: isActive(item.path) }"
               @click="$router.push(item.path)">
            <span class="nav-icon">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </div>
        </nav>
      </div>
      <div class="topbar-right">
        <el-button v-if="$route.name === 'dashboard'" type="primary" @click="$router.push('/dividends?create=1')">
          + 添加分红
        </el-button>
        <!-- v8：账户切换下拉 -->
        <el-dropdown v-if="accounts.length > 1" trigger="click" @command="onAccountCommand">
          <el-button size="small" plain>
            <span class="acct-dot" :style="{ background: currentAccountColor }"></span>
            {{ currentAccountText }}
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="__all__" :class="{ 'is-active': userStore.currentAccount === '__all__' }">
                全部账户
              </el-dropdown-item>
              <el-dropdown-item v-for="a in accounts" :key="a.name"
                                :command="a.name"
                                :class="{ 'is-active': userStore.currentAccount === a.name }">
                <span class="acct-dot" :style="{ background: a.color || '#94a3b8' }"></span>
                {{ a.name }}{{ a.archived ? '（归档）' : '' }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" @command="onCommand">
          <div class="user-box">
            <div class="avatar">{{ userStore.nickname.charAt(0).toUpperCase() }}</div>
            <div class="user-meta">
              <div class="user-name">{{ userStore.nickname }}</div>
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

    <!-- 主内容区 -->
    <main class="main">
      <div class="page-header">
        <h1 class="page-title">{{ $route.meta.title }}</h1>
        <p class="page-sub">记录每一笔分红，见证复利的力量</p>
      </div>
      <div class="page-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../store/user'
import { apiAccounts } from '../api'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// v8：账户切换
const accounts = ref([])
const currentAccountText = computed(() => {
  if (userStore.currentAccount === '__all__') return '全部账户'
  const a = accounts.value.find(x => x.name === userStore.currentAccount)
  return a ? a.name : '全部账户'
})
const currentAccountColor = computed(() => {
  if (userStore.currentAccount === '__all__') return '#1e3a8a'
  const a = accounts.value.find(x => x.name === userStore.currentAccount)
  return a?.color || '#94a3b8'
})

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

// v8：账户切换
function onAccountCommand(name) {
  userStore.setCurrentAccount(name)
  // 触发当前页重新加载（通过路由 push 同页）
  const fullPath = route.fullPath
  router.replace(fullPath).then(() => {
    // 通知子页面刷新：通过 location.reload() 简单粗暴，或用 router 跳转触发
    window.location.reload()
  })
}

onMounted(async () => {
  try {
    const data = await apiAccounts()
    accounts.value = data.items || []
  } catch (e) { /* 未登录或没账户 */ }
})
</script>

<style scoped>
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }

/* 顶部导航栏 */
.topbar {
  height: 60px; background: #fff; border-bottom: 1px solid #e2e8f0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.topbar-left { display: flex; align-items: center; gap: 32px; }

.brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.logo {
  width: 34px; height: 34px; border-radius: 8px; background: var(--primary);
  color: #fff; font-weight: 700; font-size: 18px;
  display: flex; align-items: center; justify-content: center;
}
.brand-text { line-height: 1.2; }
.brand-name { font-weight: 700; font-size: 16px; color: var(--primary); letter-spacing: 1px; }
.brand-sub { font-size: 11px; color: #94a3b8; }

.nav { display: flex; align-items: center; gap: 4px; }
.nav-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 14px;
  border-radius: 8px; color: #64748b; font-size: 14px; cursor: pointer;
  transition: all 0.15s; white-space: nowrap;
}
.nav-item:hover { background: #f1f5f9; color: var(--primary); }
.nav-item.active { background: var(--primary); color: #fff; }
.nav-icon { font-size: 16px; }

.topbar-right { display: flex; align-items: center; gap: 16px; }

/* v8：账户切换 */
.acct-dot {
  display: inline-block; width: 8px; height: 8px;
  border-radius: 50%; margin-right: 6px; vertical-align: middle;
}
.is-active { color: var(--el-color-primary); font-weight: 600; }
.user-box { display: flex; align-items: center; gap: 10px; cursor: pointer; outline: none; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; background: #dbeafe;
  color: var(--primary); font-weight: 600; display: flex; align-items: center; justify-content: center;
}
.user-name { font-size: 14px; font-weight: 500; }

.main { flex: 1; display: flex; flex-direction: column; }
.page-header {
  padding: 20px 32px 0;
}
.page-title { font-size: 22px; font-weight: 700; margin: 0; }
.page-sub { font-size: 13px; color: #94a3b8; margin: 4px 0 0; }
.page-content { flex: 1; padding: 20px 32px 32px; }
</style>
