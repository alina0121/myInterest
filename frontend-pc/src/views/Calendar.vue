<template>
  <div>
    <!-- 月份切换 + 汇总 -->
    <div class="cal-toolbar">
      <div class="month-nav">
        <el-button circle @click="prevMonth"><el-icon><ArrowLeft /></el-icon></el-button>
        <span class="month-text">{{ year }} 年 {{ month }} 月</span>
        <el-button circle @click="nextMonth"><el-icon><ArrowRight /></el-icon></el-button>
      </div>
      <div class="month-summary">
        <span>本月已确认：<b class="text-emerald">{{ fmtCNY(cal.month_confirmed_cny) }}</b></span>
        <span>待确认：<b class="text-amber">{{ fmtCNY(cal.month_pending_cny) }}</b></span>
      </div>
    </div>

    <!-- 月历网格 -->
    <div class="card">
      <div class="week-row">
        <div v-for="w in WEEKS" :key="w" class="week-cell">{{ w }}</div>
      </div>
      <div class="days-grid">
        <div v-for="cell in cells" :key="cell.key"
             :class="['day-cell', { dim: !cell.day, today: cell.isToday }]">
          <template v-if="cell.day">
            <div class="day-num">{{ cell.day }}</div>
            <div v-if="cell.items" class="day-events">
              <div v-for="(it, i) in cell.items" :key="i" class="event-dot">
                {{ it.holding_name }} +{{ sym(it.currency) }}{{ fmt(it.net) }}
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 本月分红流水 -->
    <div class="card mt20">
      <h3>本月分红流水</h3>
      <div v-if="!flowItems.length" class="empty-tip">本月暂无分红</div>
      <div v-for="(f, i) in flowItems" :key="i" :class="['flow-row', i < flowItems.length - 1 ? 'bordered' : '']">
        <div class="flow-date">
          <div class="fd-day">{{ f.day }}日</div>
        </div>
        <div class="flow-main">
          <div class="bold">{{ f.holding_name }} ({{ f.code }})</div>
          <div class="text-muted">{{ fmt(f.shares) }} 股 × {{ sym(f.currency) }}{{ fmt(f.dps) }} · 税 {{ fmt(f.tax) }}</div>
        </div>
        <div class="text-right">
          <div :class="f.status === 'confirmed' ? 'text-emerald' : 'text-amber'" style="font-weight: 600">
            {{ f.status === 'confirmed' ? '+' : '约 ' }}{{ sym(f.currency) }}{{ fmt(f.net) }}
          </div>
          <div class="text-muted">{{ f.status === 'confirmed' ? '已到账' : '待确认' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { apiCalendar } from '../api'
import { fmt, fmtCNY, currencyMap } from '../utils/constants'

const WEEKS = ['一', '二', '三', '四', '五', '六', '日']

const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const cal = ref({ days: {}, month_confirmed_cny: 0, month_pending_cny: 0 })

const cells = computed(() => {
  const y = year.value, m = month.value
  const first = new Date(y, m - 1, 1)
  const daysInMonth = new Date(y, m, 0).getDate()
  // 周一为第一天：getDay() 周日=0 → 转换 (getDay()+6)%7
  const startBlank = (first.getDay() + 6) % 7
  const list = []
  for (let i = 0; i < startBlank; i++) {
    list.push({ key: 'b' + i, day: null })
  }
  const todayStr = new Date().getDate()
  const isCurrentMonth = y === now.getFullYear() && m === now.getMonth() + 1
  for (let d = 1; d <= daysInMonth; d++) {
    list.push({
      key: 'd' + d, day: d,
      items: cal.value.days[String(d)] || null,
      isToday: isCurrentMonth && d === todayStr,
    })
  }
  return list
})

// 本月流水（按日展开）
const flowItems = computed(() => {
  const items = []
  Object.entries(cal.value.days || {}).forEach(([day, arr]) => {
    arr.forEach((it) => items.push({ ...it, day }))
  })
  return items.sort((a, b) => a.day - b.day)
})

function sym(c) { return currencyMap[c]?.symbol || '' }

async function load() {
  cal.value = await apiCalendar(year.value, month.value)
}

function prevMonth() {
  if (month.value === 1) { year.value--; month.value = 12 } else { month.value-- }
  load()
}
function nextMonth() {
  if (month.value === 12) { year.value++; month.value = 1 } else { month.value++ }
  load()
}

onMounted(load)
</script>

<style scoped>
.cal-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.month-nav { display: flex; align-items: center; gap: 16px; }
.month-text { font-size: 16px; font-weight: 600; }
.month-summary { display: flex; gap: 24px; font-size: 14px; color: #475569; }
.week-row { display: grid; grid-template-columns: repeat(7, 1fr); border-bottom: 1px solid #f1f5f9; }
.week-cell { text-align: center; font-size: 12px; color: #94a3b8; padding: 8px 0; }
.days-grid { display: grid; grid-template-columns: repeat(7, 1fr); }
.day-cell { min-height: 88px; border-right: 1px solid #f8fafc; border-bottom: 1px solid #f8fafc; padding: 6px; }
.day-cell.dim { background: #fcfcfd; }
.day-cell.today { background: #eff6ff; }
.day-num { font-size: 12px; color: #64748b; }
.day-cell.today .day-num { color: #2563eb; font-weight: 700; }
.day-events { margin-top: 4px; }
.event-dot {
  font-size: 10px; color: #059669; background: #ecfdf5;
  border-radius: 4px; padding: 1px 4px; margin-bottom: 2px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mt20 { margin-top: 20px; }
.card h3 { font-size: 15px; font-weight: 600; margin: 0 0 12px; }
.flow-row { display: flex; align-items: center; gap: 20px; padding: 12px 0; }
.flow-row.bordered { border-bottom: 1px solid #f1f5f9; }
.flow-date { width: 48px; text-align: center; }
.fd-day { font-size: 18px; font-weight: 700; color: #475569; }
.flow-main { flex: 1; }
.text-right { text-align: right; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
</style>
