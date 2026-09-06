<template>
  <div class="card">
    <div class="toolbar">
      <el-select v-model="action" placeholder="全部操作" style="width: 160px" clearable @change="load">
        <el-option v-for="a in ACTIONS" :key="a.value" :label="a.label" :value="a.value" />
      </el-select>
      <span class="text-muted">所有后台写操作自动留痕，不可篡改</span>
    </div>

    <el-table :data="list" v-loading="loading" style="width: 100%">
      <el-table-column prop="id" label="#" width="60" />
      <el-table-column prop="admin_name" label="操作人" width="110" />
      <el-table-column label="动作" width="150">
        <template #default="{ row }">
          <el-tag size="small" :type="tagType(row.action)">{{ actionText(row.action) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="对象" width="140">
        <template #default="{ row }">{{ row.target_type }} #{{ row.target_id }}</template>
      </el-table-column>
      <el-table-column label="详情" min-width="240">
        <template #default="{ row }">
          <span class="log-detail">{{ detailText(row.detail) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="120" />
      <el-table-column prop="created_at" label="时间" width="170">
        <template #default="{ row }">{{ row.created_at?.slice(0, 19) }}</template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination background layout="prev, pager, next" :total="total"
                     :page-size="pageSize" :current-page="page" @current-change="onPage" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { apiAdminLogs } from '../../api'

const ACTIONS = [
  { value: 'schedule.approve', label: '预案通过' },
  { value: 'schedule.reject', label: '预案驳回' },
  { value: 'user.ban', label: '封禁用户' },
  { value: 'user.unban', label: '解封用户' },
  { value: 'user.view_data', label: '查看用户数据' },
  { value: 'rate.update', label: '汇率变更' },
  { value: 'tax_rule.update', label: '税率变更' },
  { value: 'announcement.create', label: '发布公告' },
]

const list = ref([])
const loading = ref(false)
const action = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

function actionText(a) {
  const found = ACTIONS.find((x) => a.startsWith(x.value.split('.')[0]) && a === x.value)
  return found?.label || a
}
function tagType(a) {
  if (a.includes('ban') || a.includes('reject')) return 'danger'
  if (a.includes('approve') || a.includes('announcement')) return 'success'
  return 'info'
}
function detailText(d) {
  if (!d) return '-'
  if (typeof d === 'string') return d
  return Object.entries(d).map(([k, v]) => `${k}: ${v}`).join(' · ')
}

async function load() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (action.value) params.action = action.value
    const data = await apiAdminLogs(params)
    list.value = data.items || []
    total.value = data.total || list.value.length
  } finally {
    loading.value = false
  }
}

function onPage(p) { page.value = p; load() }

onMounted(load)
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.log-detail { font-size: 12px; color: #64748b; }
.pager { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
