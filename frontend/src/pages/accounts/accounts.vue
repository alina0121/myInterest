<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="账户管理" subtitle="管理券商账户的排序、颜色和归档" /><!-- #endif -->

    <view class="tip">账户由你持仓时填写的"账户"字段聚合而来；这里可调整颜色/排序/归档，不影响持仓数据。</view>

    <!-- 账户列表 -->
    <view v-if="accounts.length" class="card list-card">
      <view
        v-for="(a, idx) in accounts"
        :key="a.name"
        :class="['acc-item', idx === accounts.length - 1 ? 'no-border' : '']"
      >
        <view class="acc-color" :style="{ background: a.color }"></view>
        <view class="acc-info">
          <view class="acc-name">{{ a.name }}</view>
          <view class="acc-meta">
            <text v-if="a.broker">{{ a.broker }} · </text>
            <text>{{ a.holding_count }} 只持仓</text>
            <text v-if="a.archived" class="archived-tag">已归档</text>
          </view>
        </view>
        <view class="acc-actions">
          <view class="act-btn" @click="openEdit(a)">编辑</view>
          <view class="act-btn" @click="toggleArchive(a)">{{ a.archived ? '取消归档' : '归档' }}</view>
        </view>
      </view>
    </view>

    <view v-else class="empty card">
      <text class="empty-text">暂无账户，添加持仓时填写账户字段即可生成</text>
    </view>

    <!-- 添加账户按钮 -->
    <view class="add-btn-wrap">
      <button class="add-btn" @click="openAdd">+ 添加账户</button>
    </view>

    <!-- 编辑/添加弹窗 -->
    <view v-if="editing" class="modal-mask" @click="editing = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">{{ form.origName ? '编辑账户' : '添加账户' }}</view>
        <view class="field">
          <text class="f-label">账户名</text>
          <input class="f-input" v-model="form.name" placeholder="如：华泰证券" :disabled="!!form.origName" />
        </view>
        <view class="field">
          <text class="f-label">券商</text>
          <input class="f-input" v-model="form.broker" placeholder="选填" />
        </view>
        <view class="field">
          <text class="f-label">颜色</text>
          <view class="color-row">
            <view
              v-for="c in COLORS"
              :key="c"
              :class="['color-dot', form.color === c ? 'active' : '']"
              :style="{ background: c }"
              @click="form.color = c"
            ></view>
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="editing = false">取消</button>
          <button class="btn-confirm" @click="saveAccount">保存</button>
        </view>
      </view>
    </view>

    <view style="height: 140rpx"></view>
  </view>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { apiAccounts, apiAccountsMeta } from '@/api'
import WebLayout from '@/components/WebLayout.vue'

const COLORS = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b',
                '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

const accounts = ref([])
const editing = ref(false)
const form = reactive({ origName: '', name: '', broker: '', color: COLORS[0] })

async function load() {
  try {
    const data = await apiAccounts()
    accounts.value = data.items || []
  } catch (e) {}
}
onShow(load)

function openAdd() {
  form.origName = ''
  form.name = ''
  form.broker = ''
  form.color = COLORS[accounts.value.length % COLORS.length]
  editing.value = true
}

function openEdit(a) {
  form.origName = a.name
  form.name = a.name
  form.broker = a.broker || ''
  form.color = a.color || COLORS[0]
  editing.value = true
}

async function saveAccount() {
  if (!form.name) return uni.showToast({ title: '请填写账户名', icon: 'none' })
  // 把当前列表转成 meta 格式，新增或更新一项
  const meta = accounts.value.map(a => ({
    name: a.name,
    broker: a.broker || '',
    color: a.color,
    sort: a.sort || 0,
    archived: a.archived || false,
  }))
  if (form.origName) {
    // 编辑：找原 name 替换
    const i = meta.findIndex(m => m.name === form.origName)
    if (i >= 0) {
      meta[i] = { ...meta[i], broker: form.broker, color: form.color }
    }
  } else {
    // 新增
    meta.push({
      name: form.name,
      broker: form.broker,
      color: form.color,
      sort: meta.length,
      archived: false,
    })
  }
  try {
    await apiAccountsMeta(meta)
    uni.showToast({ title: '保存成功', icon: 'success' })
    editing.value = false
    load()
  } catch (e) {}
}

async function toggleArchive(a) {
  const meta = accounts.value.map(x => ({
    name: x.name,
    broker: x.broker || '',
    color: x.color,
    sort: x.sort || 0,
    archived: x.name === a.name ? !x.archived : (x.archived || false),
  }))
  try {
    await apiAccountsMeta(meta)
    uni.showToast({ title: a.archived ? '已取消归档' : '已归档', icon: 'none' })
    load()
  } catch (e) {}
}
</script>

<style scoped>
.page { padding: 24rpx; }
.tip {
  background: #fff; border-radius: 16rpx; padding: 20rpx 24rpx;
  font-size: 24rpx; color: #94a3b8; line-height: 1.5; margin-bottom: 24rpx;
}
.card { background: #fff; border-radius: 24rpx; box-shadow: 0 2rpx 6rpx rgba(0,0,0,0.06); }
.empty { padding: 80rpx 40rpx; text-align: center; }
.empty-text { font-size: 26rpx; color: #94a3b8; }
.list-card { padding: 0 28rpx; }
.acc-item {
  display: flex; align-items: center; gap: 20rpx;
  padding: 28rpx 0; border-bottom: 1rpx solid #f1f5f9;
}
.acc-item.no-border { border-bottom: none; }
.acc-color {
  width: 16rpx; height: 60rpx; border-radius: 8rpx; flex-shrink: 0;
}
.acc-info { flex: 1; min-width: 0; }
.acc-name { font-size: 30rpx; font-weight: 600; color: #1e293b; }
.acc-meta { font-size: 22rpx; color: #94a3b8; margin-top: 6rpx; }
.archived-tag {
  margin-left: 12rpx; padding: 2rpx 10rpx;
  background: #f1f5f9; color: #64748b; border-radius: 6rpx;
}
.acc-actions { display: flex; gap: 16rpx; }
.act-btn {
  font-size: 24rpx; color: #1e3a8a; padding: 8rpx 18rpx;
  background: #eff6ff; border-radius: 8rpx;
}
.act-btn:active { opacity: 0.7; }

.add-btn-wrap { margin-top: 32rpx; padding: 0 8rpx; }
.add-btn {
  width: 100%; height: 88rpx; line-height: 88rpx;
  background: #1e3a8a; color: #fff; font-size: 30rpx;
  border-radius: 24rpx; border: none;
  box-shadow: 0 4rpx 12rpx rgba(30, 58, 138, 0.18);
}
.add-btn::after { border: none; }

.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 999;
  display: flex; align-items: center; justify-content: center; padding: 0 40rpx;
}
.modal-card {
  background: #fff; border-radius: 24rpx; padding: 40rpx;
  width: 100%; max-width: 600rpx;
}
.modal-title { font-size: 32rpx; font-weight: 600; color: #1e293b; margin-bottom: 24rpx; }
.field { padding: 20rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.f-label { display: block; font-size: 24rpx; color: #94a3b8; margin-bottom: 12rpx; }
.f-input { font-size: 30rpx; height: 44rpx; }
.color-row { display: flex; gap: 16rpx; flex-wrap: wrap; }
.color-dot {
  width: 56rpx; height: 56rpx; border-radius: 50%;
  border: 4rpx solid transparent;
}
.color-dot.active { border-color: #1e293b; transform: scale(1.1); }
.modal-actions { display: flex; gap: 16rpx; margin-top: 32rpx; }
.btn-cancel, .btn-confirm {
  flex: 1; height: 80rpx; line-height: 80rpx;
  font-size: 28rpx; border-radius: 16rpx; border: none; padding: 0;
}
.btn-cancel { background: #f1f5f9; color: #64748b; }
.btn-confirm { background: #1e3a8a; color: #fff; }
.btn-cancel::after, .btn-confirm::after { border: none; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
