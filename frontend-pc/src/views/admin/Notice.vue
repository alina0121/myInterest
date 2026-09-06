<template>
  <div class="two-col">
    <!-- 公告管理 -->
    <div class="card">
      <div class="card-head">
        <h3>公告管理</h3>
        <el-button type="primary" @click="annDlg = true">+ 发布公告</el-button>
      </div>
      <p class="text-muted" style="font-size: 12px; margin-bottom: 12px">
        公告将在用户端总览页顶部横幅展示；后台仅创建/下线，历史公告可在数据库留存
      </p>
      <el-form label-width="70px">
        <el-form-item label="标题">
          <el-input v-model="annForm.title" placeholder="一句话标题（≤100字）" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="annForm.content" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="">
          <el-checkbox v-model="annForm.publish">立即发布（否则存为草稿）</el-checkbox>
        </el-form-item>
        <el-button type="primary" :loading="annSaving" @click="createAnn">提交</el-button>
      </el-form>
    </div>

    <!-- 用户反馈 -->
    <div class="card">
      <h3>用户反馈</h3>
      <el-radio-group v-model="fbStatus" size="small" style="margin-bottom: 12px" @change="loadFeedback">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="pending">待处理</el-radio-button>
        <el-radio-button value="resolved">已处理</el-radio-button>
      </el-radio-group>
      <div v-loading="fbLoading">
        <div v-if="!feedback.length" class="empty-tip">暂无反馈</div>
        <div v-for="f in feedback" :key="f.id" class="fb-item">
          <div class="fb-top">
            <b>{{ f.username }}</b>
            <span class="text-muted">{{ f.created_at?.slice(0, 16) }}</span>
            <el-tag :type="f.status === 'pending' ? 'warning' : 'success'" size="small">
              {{ fbStatusText(f.status) }}
            </el-tag>
          </div>
          <div class="fb-content">{{ f.content }}</div>
          <div v-if="f.reply" class="fb-reply">已回复：{{ f.reply }}</div>
          <div v-if="f.status === 'pending'" class="fb-actions">
            <el-select v-model="f._next" size="small" style="width: 120px">
              <el-option label="已采纳" value="adopted" />
              <el-option label="已排期" value="planned" />
              <el-option label="已完成" value="done" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
            <el-input v-model="f._reply" size="small" placeholder="回复内容（选填）" style="flex: 1" />
            <el-button type="primary" size="small" @click="handleFeedback(f)">回复</el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 发布成功提示 -->
    <el-dialog v-model="okDlg" title="发布成功" width="360">
      <p>公告已{{ annForm.publish ? '发布' : '存为草稿' }}，用户端将展示最新公告。</p>
      <template #footer>
        <el-button type="primary" @click="okDlg = false">好的</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiAdminCreateAnnouncement, apiAdminFeedback, apiAdminHandleFeedback } from '../../api'

const annDlg = ref(false)
const okDlg = ref(false)
const annSaving = ref(false)
const annForm = reactive({ title: '', content: '', publish: true })

const fbStatus = ref('')
const feedback = ref([])
const fbLoading = ref(false)

function fbStatusText(s) {
  return { pending: '待处理', adopted: '已采纳', planned: '已排期', done: '已完成', rejected: '已拒绝' }[s] || s
}

async function loadFeedback() {
  fbLoading.value = true
  try {
    const params = {}
    if (fbStatus.value) params.status = fbStatus.value
    const data = await apiAdminFeedback(params)
    feedback.value = (data.items || []).map((f) => ({ ...f, _next: 'adopted', _reply: '' }))
  } finally {
    fbLoading.value = false
  }
}

async function createAnn() {
  if (!annForm.title.trim() || !annForm.content.trim()) return ElMessage.warning('请填写标题和内容')
  annSaving.value = true
  try {
    await apiAdminCreateAnnouncement({
      title: annForm.title.trim(), content: annForm.content.trim(), publish: annForm.publish,
    })
    okDlg.value = true
    annForm.title = ''
    annForm.content = ''
  } catch (e) { /* toast 已统一 */ } finally { annSaving.value = false }
}

async function handleFeedback(f) {
  try {
    await apiAdminHandleFeedback(f.id, { status: f._next, reply: f._reply || null })
    ElMessage.success('已处理')
    loadFeedback()
  } catch (e) { /* toast 已统一 */ }
}

onMounted(loadFeedback)
</script>

<style scoped>
.two-col { display: grid; grid-template-columns: 1fr 1.2fr; gap: 20px; align-items: start; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 12px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.card-head h3 { margin: 0; }
.fb-item { border: 1px solid #f1f5f9; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
.fb-top { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.fb-content { font-size: 14px; margin-bottom: 6px; }
.fb-reply { font-size: 13px; color: #059669; background: #ecfdf5; border-radius: 6px; padding: 6px 10px; }
.fb-actions { display: flex; gap: 8px; margin-top: 8px; }
.empty-tip { color: #94a3b8; text-align: center; padding: 32px 0; font-size: 13px; }
</style>
