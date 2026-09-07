<template>
  <div>
    <!-- 头部信息 -->
    <div class="card head-card" v-loading="loading">
      <div class="head-top">
        <div class="head-title">
          <div class="d-icon">{{ marketIcon(h.market) }}</div>
          <div>
            <div class="head-name-row">
              <h2>{{ h.name }}</h2>
              <span class="text-muted">{{ h.code }}</span>
              <span class="badge" :class="'badge-' + h.market?.replace('_stock', '')">{{ marketMap[h.market]?.label }}</span>
              <span class="badge badge-freq">{{ freqMap[h.freq] || '未知' }}</span>
            </div>
            <div class="text-muted" v-if="h.account">{{ h.account }} · {{ h.currency }}</div>
          </div>
        </div>
        <div>
          <el-button type="primary" @click="lotDlg = true">+ 添加批次</el-button>
          <el-button type="primary" plain @click="openBatchDlg">批量录入</el-button>
          <el-button @click="$router.back()">返回</el-button>
        </div>
      </div>
      <div class="head-stats">
        <div class="hs-item"><div class="text-muted">当前持仓</div><div class="hs-val">{{ fmt(h.shares_now) }}</div></div>
        <div class="hs-item"><div class="text-muted">平均成本</div><div class="hs-val">{{ sym(h.currency) }}{{ fmt(h.avg_cost, 4) }}</div></div>
        <div class="hs-item"><div class="text-muted">总投入</div><div class="hs-val">{{ sym(h.currency) }}{{ fmt(h.cost_total) }}</div></div>
        <div class="hs-item"><div class="text-muted">本年分红</div><div class="hs-val text-emerald">{{ fmtCNY(h.year_dividend_cny ?? h.year_dividend) }}</div></div>
        <div class="hs-item">
          <div class="text-muted">累计分红</div>
          <div class="hs-val text-emerald">{{ fmtCNY(st.total_net_cny ?? h.total_dividend) }}</div>
          <div class="yoc-badge">TTM成本 {{ ((st.yoc_ttm ?? h.yoc_ttm) * 100).toFixed(2) }}%</div>
        </div>
      </div>
      <div class="hint-box">💡 分红按<b>股权登记日</b>当天持有的批次计算：买入日期晚于除权除息日的批次，不参与当次分红。每笔分红的批次归属明细见「分红历史」。</div>
    </div>

    <!-- Tabs -->
    <div class="card mt20">
      <el-tabs v-model="tab">
        <!-- 买入批次 -->
        <el-tab-pane label="买入批次" name="lots">
          <el-table :data="lots" style="width: 100%">
            <el-table-column prop="trade_date" label="交易日期" width="120" />
            <el-table-column label="方向" width="80">
              <template #default="{ row }">
                <el-tag :type="row.direction === 'buy' ? 'success' : 'danger'" size="small">
                  {{ row.direction === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="shares" label="数量(股)" width="100" align="right" />
            <el-table-column label="单价" width="110" align="right">
              <template #default="{ row }">{{ sym(h.currency) }}{{ fmt(row.price, 4) }}</template>
            </el-table-column>
            <el-table-column label="手续费" width="90" align="right">
              <template #default="{ row }">{{ fmt(row.fee) }}</template>
            </el-table-column>
            <el-table-column label="金额" width="130" align="right">
              <template #default="{ row }">{{ sym(h.currency) }}{{ fmt(row.amount) }}</template>
            </el-table-column>
            <el-table-column label="累计分红" width="120" align="right">
              <template #default="{ row }"><span class="text-emerald">{{ fmtCNY(row.lot_dividend) }}</span></template>
            </el-table-column>
            <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip />
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-popconfirm title="删除该批次？将重算分红归属" @confirm="delLot(row)">
                  <template #reference><el-button link type="danger">删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!lots.length" class="empty-tip">暂无批次，点击右上角「+ 添加批次」</div>
        </el-tab-pane>

        <!-- 分红历史 -->
        <el-tab-pane label="分红历史" name="divs">
          <el-table :data="divs" style="width: 100%">
            <el-table-column type="expand">
              <template #default="{ row }">
                <div class="alloc-box">
                  <div class="text-muted" style="margin-bottom: 8px">批次归属明细（按股权登记日 {{ row.record_date }} 匹配当时持仓批次）</div>
                  <template v-if="row.allocations?.length">
                    <div v-for="a in row.allocations" :key="a.lot_id" class="alloc-line">
                      <span>{{ a.trade_date }} 买入 {{ fmt(a.lot_shares) }} 股</span>
                      <span>核销 {{ fmt(a.shares) }} 股</span>
                      <span>分红 {{ sym(row.currency) }}{{ fmt(a.gross) }}</span>
                    </div>
                  </template>
                  <div v-else class="text-muted">（无明细数据）</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="ex_date" label="除权日" width="110" />
            <el-table-column prop="pay_date" label="派息日" width="110" />
            <el-table-column label="每股分红" width="110" align="right">
              <template #default="{ row }">{{ sym(row.currency) }}{{ fmt(row.dps) }}</template>
            </el-table-column>
            <el-table-column prop="shares" label="参与股数" width="100" align="right" />
            <el-table-column label="税前" width="110" align="right">
              <template #default="{ row }">{{ sym(row.currency) }}{{ fmt(row.gross_amount) }}</template>
            </el-table-column>
            <el-table-column label="税费" width="90" align="right">
              <template #default="{ row }">{{ fmt(row.tax) }}</template>
            </el-table-column>
            <el-table-column label="税后(折CNY)" width="130" align="right">
              <template #default="{ row }"><span class="text-emerald bold">{{ fmtCNY(row.net_cny) }}</span></template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 'confirmed' ? 'success' : 'warning'" size="small">
                  {{ row.status === 'confirmed' ? '已到账' : '待确认' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="来源" width="80">
              <template #default="{ row }">{{ row.source === 'manual' ? '手动' : row.source }}</template>
            </el-table-column>
          </el-table>
          <div v-if="!divs.length" class="empty-tip">暂无分红记录</div>
        </el-tab-pane>

        <!-- 年度统计 -->
        <el-tab-pane label="年度统计" name="yearly">
          <el-table :data="st.yearly || []" style="width: 100%">
            <el-table-column prop="year" label="年份" width="120" />
            <el-table-column label="税后分红(折CNY)" align="right">
              <template #default="{ row }"><span class="text-emerald bold">{{ fmtCNY(row.net_cny) }}</span></template>
            </el-table-column>
          </el-table>
          <div v-if="!(st.yearly || []).length" class="empty-tip">暂无年度数据</div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 添加批次 -->
    <el-dialog v-model="lotDlg" title="添加批次" width="480">
      <el-form label-width="90px">
        <el-form-item label="方向">
          <el-radio-group v-model="lotForm.direction">
            <el-radio value="buy">买入</el-radio>
            <el-radio value="sell">卖出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="交易日期">
          <el-date-picker v-model="lotForm.trade_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数量(股)">
          <el-input-number v-model="lotForm.shares" :min="0" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="lotForm.price" :min="0" :precision="4" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="手续费">
          <el-input-number v-model="lotForm.fee" :min="0" :precision="2" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="lotForm.note" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="lotDlg = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveLot">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量录入批次 -->
    <el-dialog v-model="batchDlg" title="批量录入批次" width="960">
      <el-table :data="batchLots" size="small" border style="width: 100%">
        <el-table-column label="交易日期" width="170">
          <template #default="{ row }">
            <el-date-picker
              v-model="row.trade_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              style="width: 100%"
            />
          </template>
        </el-table-column>
        <el-table-column label="方向" width="120">
          <template #default="{ row }">
            <el-select v-model="row.direction" style="width: 100%">
              <el-option label="买入" value="buy" />
              <el-option label="卖出" value="sell" />
              <el-option label="送转" value="bonus_share" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="数量(股)" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.shares" :min="0" :controls="false" style="width: 100%" />
          </template>
        </el-table-column>
        <el-table-column label="成交价" width="140">
          <template #default="{ row }">
            <el-input-number v-model="row.price" :min="0" :precision="4" :controls="false" style="width: 100%" />
          </template>
        </el-table-column>
        <el-table-column label="费用" width="130">
          <template #default="{ row }">
            <el-input-number v-model="row.fee" :min="0" :precision="2" :controls="false" style="width: 100%" />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="150">
          <template #default="{ row }">
            <el-input v-model="row.note" placeholder="选填" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ $index }">
            <el-button link type="danger" :icon="Delete" @click="removeBatchRow($index)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="batch-toolbar">
        <el-button :icon="Plus" @click="addBatchRow">+ 新增一行</el-button>
      </div>
      <template #footer>
        <div class="batch-footer">
          <el-button @click="batchDlg = false">取消</el-button>
          <el-button type="primary" :loading="batchSaving" @click="saveBatchLots">批量保存</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { apiHolding, apiLots, apiCreateLot, apiCreateLotsBatch, apiDeleteLot, apiDividends, apiHoldingStats } from '../api'
import { marketMap, fmt, fmtCNY, currencyMap, freqMap } from '../utils/constants'

const route = useRoute()
const id = route.params.id

function marketIcon(m) {
  return { a_share: '🍷', us_stock: '🇺🇸', hk_stock: '🇭🇰', fund: '📊' }[m] || '📈'
}

const h = ref({})
const st = ref({})
const lots = ref([])
const divs = ref([])
const loading = ref(false)
const tab = ref('lots')
const lotDlg = ref(false)
const saving = ref(false)

const lotForm = reactive({ direction: 'buy', trade_date: '', shares: undefined, price: undefined, fee: 0, note: '' })

const batchDlg = ref(false)
const batchSaving = ref(false)
const batchLots = ref([])

function newBatchRow() {
  return { trade_date: '', direction: 'buy', shares: undefined, price: undefined, fee: 0, note: '' }
}

function openBatchDlg() {
  batchLots.value = Array.from({ length: 5 }, newBatchRow)
  batchDlg.value = true
}

function addBatchRow() {
  batchLots.value.push(newBatchRow())
}

function removeBatchRow(idx) {
  batchLots.value.splice(idx, 1)
}

function sym(c) { return currencyMap[c]?.symbol || '' }

async function load() {
  loading.value = true
  try {
    const [hh, ss, ll, dd] = await Promise.all([
      apiHolding(id), apiHoldingStats(id), apiLots(id), apiDividends({ holding_id: id, page_size: 100 }),
    ])
    h.value = hh
    st.value = ss
    lots.value = ll.items || []
    divs.value = dd.items || []
  } finally {
    loading.value = false
  }
}

async function saveLot() {
  if (!lotForm.trade_date || !lotForm.shares) return ElMessage.warning('请填写日期和数量')
  saving.value = true
  try {
    await apiCreateLot(id, {
      trade_date: lotForm.trade_date, direction: lotForm.direction,
      shares: Number(lotForm.shares), price: Number(lotForm.price || 0), fee: Number(lotForm.fee || 0),
      note: lotForm.note || null,
    })
    ElMessage.success('批次已添加，分红归属已重算')
    lotDlg.value = false
    Object.assign(lotForm, { direction: 'buy', trade_date: '', shares: undefined, price: undefined, fee: 0, note: '' })
    load()
  } catch (e) {
    /* toast 已统一 */
  } finally {
    saving.value = false
  }
}

async function delLot(lot) {
  try {
    await apiDeleteLot(lot.id)
    ElMessage.success('批次已删除')
    load()
  } catch (e) { /* toast 已统一 */ }
}

async function saveBatchLots() {
  const payload = batchLots.value
    .filter(r => r.trade_date && r.shares)
    .map(r => ({
      trade_date: r.trade_date,
      direction: r.direction,
      shares: Number(r.shares),
      price: Number(r.price || 0),
      fee: Number(r.fee || 0),
      note: r.note || null,
    }))
  if (!payload.length) return ElMessage.warning('请至少填写一行有效数据（日期 + 数量）')
  batchSaving.value = true
  try {
    await apiCreateLotsBatch(id, payload)
    ElMessage.success(`已批量添加 ${payload.length} 条批次`)
    batchDlg.value = false
    load()
  } catch (e) {
    /* toast 已统一 */
  } finally {
    batchSaving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.head-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.head-title { display: flex; align-items: center; gap: 12px; }
.d-icon {
  width: 48px; height: 48px; border-radius: 12px; background: #eff6ff;
  display: flex; align-items: center; justify-content: center; font-size: 24px;
}
.head-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.head-name-row h2 { margin: 0; font-size: 18px; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 9999px; font-weight: 500; }
.badge-freq { background: #f5f3ff; color: #7c3aed; }
.head-stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; text-align: center; }
.hs-val { font-size: 20px; font-weight: 700; margin-top: 4px; }
.yoc-badge {
  display: inline-block; font-size: 11px; background: #ecfdf5; color: #059669;
  border-radius: 9999px; padding: 1px 8px; margin-top: 4px;
}
.hint-box {
  margin-top: 16px; padding: 12px 16px; font-size: 12px; color: #b45309;
  background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;
}
.mt20 { margin-top: 20px; }
.empty-tip { color: #94a3b8; text-align: center; padding: 40px 0; font-size: 13px; }
.alloc-box { padding: 8px 16px 16px 48px; background: #f8fafc; }
.alloc-line { display: flex; gap: 24px; font-size: 13px; padding: 4px 0; color: #475569; }
.batch-toolbar { margin-top: 12px; }
.batch-footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
