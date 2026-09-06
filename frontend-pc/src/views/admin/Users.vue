<template>
  <div>
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名" style="width: 200px" clearable @keyup.enter="load" />
    </div>

    <div class="card">
      <el-table :data="list" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="email" label="邮箱(脱敏)" width="160" />
        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="row.role === 'user' ? 'info' : 'warning'" size="small">
              {{ row.role === 'super_admin' ? '超管' : row.role === 'admin' ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="持仓 / 分红" width="110" align="center">
          <template #default="{ row }">{{ row.holding_count }} / {{ row.dividend_count }}</template>
        </el-table-column>
        <el-table-column label="累计分红" width="120" align="right">
          <template #default="{ row }">{{ fmtCNY(row.total_dividend_cny) }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="160">
          <template #default="{ row }">{{ row.created_at?.slice(0, 16) }}</template>
        </el-table-column>
        <el-table-column prop="last_login_at" label="最近登录" width="160">
          <template #default="{ row }">{{ row.last_login_at?.slice(0, 16) || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'" size="small">
              {{ row.status === 'active' ? '正常' : '已封禁' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewData(row)">查看数据</el-button>
            <el-button v-if="row.status === 'active' && row.role === 'user'" link type="danger" @click="ban(row)">封禁</el-button>
            <el-button v-if="row.status === 'banned'" link type="success" @click="unban(row)">解封</el-button>
            <el-button link type="warning" @click="resetPwd(row)">重置密码</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 用户数据只读查看 -->
    <el-dialog v-model="dataDlg" :title="`用户数据（只读）· ${viewing?.username}`" width="640">
      <div v-loading="dataLoading">
        <div v-if="!userData.length" class="empty-tip">该用户暂无持仓数据</div>
        <div v-for="h in userData" :key="h.id" class="ud-card">
          <div class="ud-head">
            <span class="badge" :class="'badge-' + h.market?.replace('_stock', '')">{{ marketMap[h.market]?.label }}</span>
            <b>{{ h.name }}</b><span class="text-muted">{{ h.code }}</span>
          </div>
          <div class="ud-grid">
            <span>持仓 {{ h.shares_now }} 股</span>
            <span>批次 {{ h.lot_count }}</span>
            <span>分红 {{ h.dividend_count }} 笔</span>
            <span class="text-emerald">累计 {{ fmtCNY(h.total_dividend_cny) }}</span>
          </div>
        </div>
      </div>
      <p class="text-muted" style="font-size: 12px; margin-top: 12px">
        管理员对用户业务数据仅只读访问，本次查看已记录操作日志
      </p>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apiAdminUsers, apiAdminUserData, apiAdminBanUser, apiAdminUnbanUser, apiAdminResetPwd } from '../../api'
import { marketMap, fmtCNY } from '../../utils/constants'

const list = ref([])
const loading = ref(false)
const keyword = ref('')
const dataDlg = ref(false)
const dataLoading = ref(false)
const userData = ref([])
const viewing = ref(null)

async function load() {
  loading.value = true
  try {
    const params = {}
    if (keyword.value) params.keyword = keyword.value
    const data = await apiAdminUsers(params)
    list.value = data.items || []
  } finally {
    loading.value = false
  }
}

async function viewData(row) {
  viewing.value = row
  dataDlg.value = true
  dataLoading.value = true
  try {
    const data = await apiAdminUserData(row.id)
    userData.value = data.items || data.holdings || []
  } catch (e) {
    userData.value = []
  } finally {
    dataLoading.value = false
  }
}

async function ban(row) {
  try {
    await ElMessageBox.confirm(`确认封禁用户「${row.username}」？封禁后无法登录`, '封禁确认', { type: 'warning' })
    await apiAdminBanUser(row.id)
    ElMessage.success('已封禁')
    load()
  } catch (e) { /* 取消或 toast 已统一 */ }
}

async function unban(row) {
  try {
    await apiAdminUnbanUser(row.id)
    ElMessage.success('已解封')
    load()
  } catch (e) { /* toast 已统一 */ }
}

async function resetPwd(row) {
  try {
    const r = await apiAdminResetPwd(row.id)
    const pwd = r?.new_password || r?.password || '已重置'
    ElMessageBox.alert(`新密码：<b>${pwd}</b>`, '密码已重置', { dangerouslyUseHTMLString: true })
    load()
  } catch (e) { /* toast 已统一 */ }
}

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; margin-bottom: 16px; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }
.ud-card { border: 1px solid #f1f5f9; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.ud-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ud-grid { display: flex; gap: 16px; font-size: 13px; color: #475569; }
.empty-tip { color: #94a3b8; text-align: center; padding: 24px 0; font-size: 13px; }
</style>
