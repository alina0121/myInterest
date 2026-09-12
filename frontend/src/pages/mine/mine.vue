<template>
  <view class="page">
    <!-- #ifdef H5 --><WebLayout title="我的" subtitle="账户、汇率、提醒与数据" /><!-- #endif -->

    <!-- 用户卡 -->
    <view class="profile-card">
      <view class="avatar">{{ (user?.nickname || user?.username || '投')[0] }}</view>
      <view class="profile-info">
        <text class="nick">{{ user?.nickname || user?.username || '用户' }}</text>
        <text class="profile-sub">数据按用户隔离 · 仅本人可见</text>
      </view>
    </view>

    <!-- 功能菜单 -->
    <view class="card menu-card">
      <!-- v8：当前账户切换（统一入口，含账户管理） -->
      <view class="menu-row" @click="showAccountSwitch">
        <SvgIcon name="account" :size="40" />
        <text class="m-label">账户切换</text>
        <text class="m-sub-text">{{ currentAccountText }}</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row" @click="showCurrencySwitch">
        <SvgIcon name="rate" :size="40" />
        <text class="m-label">显示币种</text>
        <text class="m-sub-text">{{ displayCurrencyText }}</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row" @click="go('/pages/stats/stats')">
        <SvgIcon name="stats" :size="40" />
        <text class="m-label">统计分析</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row" @click="showBindEmail">
        <SvgIcon name="bell" :size="40" />
        <text class="m-label">绑定邮箱</text>
        <text class="m-sub-text">{{ user?.email || '未绑定' }}</text>
        <SvgIcon name="arrow-right" :size="32" class="m-arrow" />
      </view>
      <view class="menu-row no-border" @click="toggleRemind">
        <SvgIcon name="bell" :size="40" />
        <text class="m-label">分红提醒</text>
        <text :class="['m-status', settings.remind_on_payday ? 'on' : 'off']">
          {{ settings.remind_on_payday ? '已开启' : '未开启' }}
        </text>
      </view>
    </view>

    <!-- v8：显示币种切换弹窗 -->
    <view v-if="curVisible" class="modal-mask" @click="curVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">显示币种</view>
        <view class="modal-tip">选择后，所有页面的金额将按该币种显示。选「本币」则各市场按原币种显示。</view>
        <view class="acct-list">
          <view v-for="c in DISPLAY_CURRENCIES" :key="c.value"
                :class="['acct-row', userStore.displayCurrency === c.value ? 'on' : '']"
                @click="pickCurrency(c.value)">
            <text class="acct-dot" :style="{ background: c.color || '#94a3b8' }"></text>
            <text class="acct-name">{{ c.label }}</text>
            <text v-if="userStore.displayCurrency === c.value" class="acct-check">✓</text>
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="curVisible = false">关闭</button>
        </view>
      </view>
    </view>

    <!-- v8：账户切换弹窗（含账户管理） -->
    <view v-if="acctVisible" class="modal-mask" @click="acctVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">账户切换</view>
        <view class="modal-tip">选择账户后，所有页面数据将跟随切换；选择「全部」显示所有账户汇总。左滑或点击右侧按钮可归档/编辑。</view>
        <view class="acct-list">
          <view :class="['acct-row', userStore.currentAccount === '__all__' ? 'on' : '']"
                @click="pickAccount('__all__')">
            <text class="acct-dot" style="background:#1e3a8a"></text>
            <text class="acct-name">全部账户</text>
            <text v-if="userStore.currentAccount === '__all__'" class="acct-check">✓</text>
          </view>
          <view v-for="a in accountList" :key="a.name"
                :class="['acct-row', userStore.currentAccount === a.name ? 'on' : '', a.archived ? 'archived' : '']"
                @click="pickAccount(a.name)">
            <text class="acct-dot" :style="{ background: a.color || '#94a3b8' }"></text>
            <text class="acct-name">{{ a.name }}</text>
            <text class="acct-count">{{ a.holding_count }}只</text>
            <view class="acct-ops">
              <text class="op-btn" @click.stop="toggleArchive(a)">归档</text>
            </view>
            <text v-if="userStore.currentAccount === a.name" class="acct-check">✓</text>
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="acctVisible = false">关闭</button>
        </view>
      </view>
    </view>

    <!-- 绑定邮箱弹窗 -->
    <view v-if="bindVisible" class="modal-mask" @click="bindVisible = false">
      <view class="modal-card" @click.stop>
        <view class="modal-title">{{ user?.email ? '修改绑定邮箱' : '绑定邮箱' }}</view>
        <view class="modal-tip" v-if="!user?.email">绑定后可用邮箱验证码登录、找回密码；若邮箱已被其他账号使用，将合并数据到该账号下。</view>
        <view class="field">
          <text class="f-label">邮箱</text>
          <input class="f-input" v-model="bindForm.email" placeholder="请输入邮箱" />
        </view>
        <view class="field code-field">
          <text class="f-label">验证码</text>
          <view class="code-row">
            <input class="f-input code-input" v-model="bindForm.code" placeholder="6 位验证码" />
            <button class="btn-code" :disabled="bindCooldown > 0" @click="sendBindCode">
              {{ bindCooldown > 0 ? `${bindCooldown}s` : '获取' }}
            </button>
          </view>
        </view>
        <view class="modal-actions">
          <button class="btn-cancel" @click="bindVisible = false">取消</button>
          <button class="btn-confirm" :loading="bindLoading" @click="confirmBind">确认绑定</button>
        </view>
      </view>
    </view>

    <!-- 退出登录 -->
    <view class="logout-wrap">
      <view class="card logout-card" @click="logout">
        <SvgIcon name="logout" :size="36" />
        <text class="logout-text">退出登录</text>
      </view>
    </view>

    <view style="height: 140rpx"></view>
  </view>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import {
  apiRates, apiSettings, apiSaveSettings, apiLogout,
  apiSendCode, apiBindEmail, apiMe, apiAccounts, apiAccountsMeta,
} from '@/api'
import { userStore, setAuth, clearAuth, syncFromSettings, setCurrentAccount, setDisplayCurrency } from '@/store/user'
import WebLayout from '@/components/WebLayout.vue'
import SvgIcon from '@/components/SvgIcon.vue'

// v8：显示币种选项
const DISPLAY_CURRENCIES = [
  { value: 'CNY', label: '人民币 ¥', color: '#dc2626' },
  { value: 'USD', label: '美元 $', color: '#2563eb' },
  { value: 'HKD', label: '港币 HK$', color: '#059669' },
  { value: 'ORIGINAL', label: '本币（按原币种显示）', color: '#7c3aed' },
]

const user = computed(() => userStore.user)
const rates = ref({})
const settings = reactive({})
// v8：账户切换
const acctVisible = ref(false)
const accountList = ref([])
const currentAccountText = computed(() => {
  if (!accountList.value.length) return '未配置'
  if (userStore.currentAccount === '__all__') return '全部账户'
  const a = accountList.value.find(x => x.name === userStore.currentAccount)
  return a ? a.name : '全部账户'
})
// v8：显示币种
const curVisible = ref(false)
const displayCurrencyText = computed(() => {
  const c = DISPLAY_CURRENCIES.find(x => x.value === userStore.displayCurrency)
  return c ? c.label : '人民币'
})

const visibleText = computed(() => displayCurrencyText.value)  // 兼容旧引用

async function load() {
  try {
    const [r, s] = await Promise.all([apiRates(), apiSettings()])
    rates.value = r.rates || {}
    Object.assign(settings, s)
    // v8：从 settings 同步币种配置到 store
    syncFromSettings(s)
    // 同步最新用户信息（has_wx 等可能变化）
    try {
      const u = await apiMe()
      if (u) userStore.user = { ...userStore.user, ...u }
    } catch (e) {}
    // v8：加载账户列表
    try {
      const data = await apiAccounts()
      accountList.value = data.items || []
    } catch (e) {}
  } catch (e) {}
}
onShow(load)

// v8：账户切换
function showAccountSwitch() {
  acctVisible.value = true
}
function pickAccount(name) {
  setCurrentAccount(name)
  acctVisible.value = false
  uni.showToast({ title: name === '__all__' ? '已切换到全部账户' : `已切换到「${name}」`, icon: 'none' })
}

// v8：归档/取消归档账户
async function toggleArchive(a) {
  const meta = accountList.value.map(x => ({
    name: x.name,
    broker: x.broker || '',
    color: x.color,
    sort: x.sort || 0,
    archived: x.name === a.name ? !x.archived : (x.archived || false),
  }))
  try {
    await apiAccountsMeta(meta)
    uni.showToast({ title: a.archived ? '已取消归档' : '已归档', icon: 'none' })
    const data = await apiAccounts()
    accountList.value = data.items || []
  } catch (e) { /* toast 已统一 */ }
}

// v8：显示币种切换
function showCurrencySwitch() {
  curVisible.value = true
}
async function pickCurrency(value) {
  setDisplayCurrency(value)
  curVisible.value = false
  // 持久化到后端 settings
  try {
    await apiSaveSettings({ display_currency: value })
  } catch (e) { /* 静默 */ }
  uni.showToast({ title: '显示币种已更新', icon: 'none' })
}

function go(url) {
  uni.navigateTo({
    url,
    fail: () => uni.switchTab({ url, fail: () => uni.showToast({ title: '页面未就绪', icon: 'none' }) }),
  })
}

async function toggleRemind() {
  const next = !settings.remind_on_payday
  settings.remind_on_payday = next
  try {
    await apiSaveSettings({ remind_on_payday: next ? 1 : 0 })
    uni.showToast({ title: next ? '已开启' : '已关闭', icon: 'none' })
  } catch (e) {
    settings.remind_on_payday = !next
  }
}

// ---------- 绑定邮箱 ----------
const bindVisible = ref(false)
const bindLoading = ref(false)
const bindCooldown = ref(0)
const bindForm = reactive({ email: '', code: '' })

function showBindEmail() {
  bindForm.email = user.value?.email || ''
  bindForm.code = ''
  bindVisible.value = true
}

async function sendBindCode() {
  if (!bindForm.email) return uni.showToast({ title: '请填写邮箱', icon: 'none' })
  try {
    await apiSendCode('email', bindForm.email, 'bind')
    uni.showToast({ title: '验证码已发送', icon: 'none' })
    bindCooldown.value = 60
    const timer = setInterval(() => {
      bindCooldown.value -= 1
      if (bindCooldown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (e) {}
}

async function confirmBind() {
  if (!bindForm.email || !bindForm.code) {
    return uni.showToast({ title: '请填写邮箱和验证码', icon: 'none' })
  }
  bindLoading.value = true
  try {
    const data = await apiBindEmail(bindForm.email, bindForm.code)
    // 合并场景：token 已变化，需要重新 setAuth 切到目标账号
    setAuth(data.access_token, data.user)
    if (data.merged) {
      uni.showToast({ title: '已合并到邮箱账号', icon: 'success' })
    } else {
      uni.showToast({ title: '绑定成功', icon: 'success' })
    }
    bindVisible.value = false
    // 重新加载用户数据
    setTimeout(() => load(), 400)
  } catch (e) {
  } finally {
    bindLoading.value = false
  }
}

function logout() {
  uni.showModal({
    title: '提示', content: '确定退出登录吗？',
    success: async (r) => {
      if (!r.confirm) return
      try { await apiLogout() } catch (e) { /* 即使失败也清本地态 */ }
      clearAuth()
      uni.reLaunch({ url: '/pages/login/login' })
    },
  })
}
</script>

<style scoped>
.page { padding: 24rpx; }

/* 用户卡 */
.profile-card {
  display: flex; align-items: center; gap: 24rpx;
  background: #fff; border-radius: 24rpx; padding: 36rpx 32rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}
.avatar {
  width: 48rpx; height: 48rpx; border-radius: 50%;
  background: #dbeafe; color: #1e3a8a;
  text-align: center; line-height: 48rpx;
  font-size: 28rpx; font-weight: 700; flex-shrink: 0;
}
.profile-info { flex: 1; min-width: 0; }
.nick { display: block; font-size: 30rpx; font-weight: 600; color: #1e293b; }
.profile-sub { display: block; margin-top: 8rpx; font-size: 22rpx; color: #94a3b8; }

/* 菜单卡 */
.card {
  background: #fff; border-radius: 24rpx;
  box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);
}
.menu-card { margin-top: 24rpx; padding: 0 28rpx; }
.menu-row {
  display: flex; align-items: center; padding: 30rpx 0;
  border-bottom: 1rpx solid #f1f5f9;
  gap: 20rpx;
  color: #475569;
}
.menu-row.no-border { border-bottom: none; }
.menu-row:active { background: #f8fafc; }
.m-label { flex: 1; font-size: 28rpx; color: #1e293b; }
.m-arrow { color: #cbd5e1; flex-shrink: 0; }
.m-sub-text { font-size: 22rpx; color: #94a3b8; max-width: 200rpx; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-status { font-size: 24rpx; }
.m-status.on { color: #059669; }
.m-status.off { color: #94a3b8; }

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5);
  z-index: 999; display: flex; align-items: center; justify-content: center;
  padding: 0 40rpx;
}
.modal-card {
  background: #fff; border-radius: 24rpx; padding: 40rpx;
  width: 100%; max-width: 600rpx;
}
.modal-title { font-size: 32rpx; font-weight: 600; color: #1e293b; margin-bottom: 16rpx; }
.modal-tip { font-size: 22rpx; color: #94a3b8; line-height: 1.5; margin-bottom: 24rpx; }
.field { padding: 20rpx 0; border-bottom: 1rpx solid #f1f5f9; }
.f-label { display: block; font-size: 24rpx; color: #94a3b8; margin-bottom: 12rpx; }
.f-input { font-size: 30rpx; height: 44rpx; }
.code-field { border-bottom: none; padding-bottom: 0; }
.code-row { display: flex; align-items: center; gap: 16rpx; }
.code-input { flex: 1; }
.btn-code {
  flex-shrink: 0; min-width: 140rpx; height: 56rpx; line-height: 56rpx;
  font-size: 22rpx; padding: 0 16rpx; margin: 0;
  background: #1e3a8a; color: #fff; border-radius: 12rpx; border: none;
}
.btn-code[disabled] { background: #94a3b8; }
.btn-code::after { border: none; }
.modal-actions { display: flex; gap: 16rpx; margin-top: 32rpx; }

/* v8：账户切换弹窗 */
.acct-list { max-height: 600rpx; overflow-y: auto; }
.acct-row {
  display: flex; align-items: center; gap: 16rpx;
  padding: 24rpx 16rpx; border-bottom: 1rpx solid #f1f5f9;
}
.acct-row:last-child { border-bottom: none; }
.acct-row.on { background: #eff6ff; }
.acct-row.archived { opacity: 0.5; }
.acct-dot { width: 16rpx; height: 16rpx; border-radius: 50%; flex-shrink: 0; }
.acct-name { flex: 1; font-size: 28rpx; color: #1e293b; }
.acct-count { font-size: 22rpx; color: #94a3b8; }
.acct-ops { margin-left: auto; display: flex; gap: 12rpx; }
.op-btn { font-size: 22rpx; color: #2563eb; padding: 4rpx 12rpx; }
.acct-check { color: #1e3a8a; font-size: 32rpx; }
.btn-cancel, .btn-confirm {
  flex: 1; height: 80rpx; line-height: 80rpx;
  font-size: 28rpx; border-radius: 16rpx; border: none; padding: 0;
}
.btn-cancel { background: #f1f5f9; color: #64748b; }
.btn-confirm { background: #1e3a8a; color: #fff; }
.btn-cancel::after, .btn-confirm::after { border: none; }

/* 退出登录 */
.logout-wrap { margin-top: 32rpx; padding: 0 8rpx; }
.logout-card {
  padding: 30rpx 0; text-align: center;
  display: flex; align-items: center; justify-content: center; gap: 12rpx;
  color: #dc2626;
}
.logout-card:active { background: #f8fafc; }
.logout-text { font-size: 28rpx; color: #dc2626; font-weight: 500; }

/* #ifdef H5 */
@media (min-width: 768px) {
  .page { padding: 32rpx 48rpx 60rpx; max-width: 800px; margin: 0 auto; }
}
/* #endif */
</style>
