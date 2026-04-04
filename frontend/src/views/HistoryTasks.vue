<template>
  <div class="history-tasks">
    <!-- Supabase 云端扩展能力说明折叠卡片 -->
    <el-collapse v-model="supabaseOpen" class="supabase-collapse">
      <el-collapse-item name="supabase">
        <template #title>
          <div class="supabase-header">
            <span class="supabase-logo">⚡</span>
            <span class="supabase-title">云端扩展能力 — Supabase PostgreSQL 集成</span>
            <el-tag size="small" type="success" style="margin-left:10px">已预留接口</el-tag>
          </div>
        </template>
        <div class="supabase-body">
          <el-row :gutter="24">
            <el-col :span="14">
              <div class="supabase-desc">
                <p>
                  本系统当前演示环境使用 <strong>本地 SQLite</strong> 数据库存储历史任务，
                  数据文件位于 <code>backend/data/history.db</code>，无需任何外部依赖，保证演示稳定性。
                </p>
                <p style="margin-top:8px">
                  系统架构已为 <strong>Supabase 云端 PostgreSQL</strong> 预留标准化数据访问接口。
                  在生产部署场景下，只需替换 <code>history.py</code> 中的连接驱动，即可实现：
                </p>
                <ul class="supabase-features">
                  <li>多设备/多巡检车辆数据实时同步</li>
                  <li>云端持久化，数据不随本机重启丢失</li>
                  <li>Supabase 行级安全策略（RLS）保障数据隔离</li>
                  <li>内置 REST API 与 Realtime 推送能力</li>
                </ul>
              </div>
            </el-col>
            <el-col :span="10">
              <div class="supabase-code-block">
                <div class="code-label">生产环境切换示例（仅需修改连接配置）</div>
                <pre class="code-snippet">
# 安装 PostgreSQL 驱动
pip install psycopg2-binary supabase

# history.py 生产环境配置
import psycopg2
SUPABASE_URL = "postgresql://postgres:[password]"
              "@db.[project].supabase.co:5432/postgres"

def _get_conn():
    return psycopg2.connect(SUPABASE_URL)
# 其余接口逻辑完全不变 ✓</pre>
              </div>
            </el-col>
          </el-row>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 缺陷类型饼图（巡检员看自己 / 管理员看全量） -->
    <el-card shadow="hover" class="pie-card">
      <template #header>
        <div class="pie-header">
          <span class="card-title">缺陷类型分布（按检测实例数）</span>
          <div class="pie-controls">
            <el-date-picker
              v-model="pieDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              clearable
              style="width:260px"
              @change="loadPie"
            />
            <el-button size="small" @click="clearPieRange">全量</el-button>
          </div>
        </div>
      </template>
      <div v-if="pieRaw.total_detections === 0" class="pie-empty">
        当前范围内暂无缺陷检测数据
      </div>
      <v-chart v-else :option="pieOption" class="pie-chart" autoresize />
    </el-card>

    <!-- 顶部汇总统计卡片 -->
    <el-row :gutter="16" class="summary-row">
      <el-col :span="6">
        <el-card class="summary-card" shadow="hover">
          <div class="summary-inner">
            <div class="summary-icon" style="background:linear-gradient(135deg,#667eea,#764ba2)">
              <el-icon :size="22"><List /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">{{ summary.total }}</div>
              <div class="summary-label">历史任务总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card" shadow="hover">
          <div class="summary-inner">
            <div class="summary-icon" style="background:linear-gradient(135deg,#f5576c,#f093fb)">
              <el-icon :size="22"><WarnTriangleFilled /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">{{ summary.defects }}</div>
              <div class="summary-label">累计检出缺陷</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card" shadow="hover">
          <div class="summary-inner">
            <div class="summary-icon" style="background:linear-gradient(135deg,#ff4d4f,#ff7a45)">
              <el-icon :size="22"><Warning /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">{{ summary.highDanger }}</div>
              <div class="summary-label">高危缺陷数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card" shadow="hover">
          <div class="summary-inner">
            <div class="summary-icon" style="background:linear-gradient(135deg,#43e97b,#38f9d7)">
              <el-icon :size="22"><Money /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">¥{{ summary.totalCost.toLocaleString() }}</div>
              <div class="summary-label">累计预估修复费用</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选与操作栏 -->
    <el-card shadow="never" class="filter-card">
      <div class="filter-row">
        <div class="filter-left">
          <el-select
            v-model="filterDefect"
            placeholder="缺陷筛选"
            clearable
            style="width:140px"
            @change="loadTasks"
          >
            <el-option label="全部任务" value="" />
            <el-option label="有缺陷" value="yes" />
            <el-option label="无缺陷" value="no" />
          </el-select>

          <el-date-picker
            v-model="filterDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width:260px; margin-left:12px"
            @change="applyDateFilter"
          />
        </div>

        <div class="filter-right">
          <el-button
            type="primary"
            :icon="RefreshRight"
            :loading="loading"
            @click="loadTasks"
          >
            刷新
          </el-button>
          <el-button
            type="danger"
            plain
            :icon="Delete"
            :disabled="selectedIds.length === 0"
            @click="batchDelete"
          >
            删除所选 ({{ selectedIds.length }})
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 任务列表表格 -->
    <el-card shadow="hover" class="table-card">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span class="card-title">巡检任务列表</span>
          <span class="table-count">共 {{ filteredTasks.length }} 条记录</span>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="pagedTasks"
        stripe
        highlight-current-row
        @selection-change="handleSelectionChange"
        style="width:100%"
      >
        <el-table-column type="selection" width="50" />

        <el-table-column label="任务ID" prop="id" width="80" align="center">
          <template #default="{ row }">
            <span class="task-id">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column label="检测时间" width="175">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="类型" width="72" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="row.task_type === 'video' ? 'warning' : 'info'">
              {{ row.task_type === 'video' ? '视频' : '图片' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="文件名" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <el-icon style="vertical-align:-2px;margin-right:4px"><Picture /></el-icon>
            <span>{{ row.filename }}</span>
          </template>
        </el-table-column>

        <el-table-column label="置信度" width="90" align="center">
          <template #default="{ row }">
            <span class="conf-text">{{ (row.confidence * 100).toFixed(0) }}%</span>
          </template>
        </el-table-column>

        <el-table-column label="A/B对比" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.ab_test" type="warning" size="small">开启</el-tag>
            <el-tag v-else type="info" size="small">关闭</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="检测结果" width="100" align="center">
          <template #default="{ row }">
            <span
              v-if="row.has_defect"
              style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;background:#fff1f0;color:#ff4d4f;border:1px solid #ffa39e"
            >发现缺陷</span>
            <span
              v-else
              style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;background:#f6ffed;color:#52c41a;border:1px solid #b7eb8f"
            >路面正常</span>
          </template>
        </el-table-column>

        <el-table-column label="缺陷数" width="80" align="center">
          <template #default="{ row }">
            <span :class="row.defect_count > 0 ? 'count-bad' : 'count-ok'">
              {{ row.defect_count }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="高危数" width="80" align="center">
          <template #default="{ row }">
            <span :class="row.high_danger_count > 0 ? 'count-danger' : 'count-ok'">
              {{ row.high_danger_count }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="预估费用" width="100" align="right">
          <template #default="{ row }">
            <span class="cost-text">¥{{ row.total_cost.toLocaleString() }}</span>
          </template>
        </el-table-column>

        <el-table-column label="耗时" width="80" align="center">
          <template #default="{ row }">
            <span class="time-ms">{{ row.inference_time_ms }} ms</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="130" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              :icon="View"
              @click="openDetail(row.id)"
            >详情</el-button>
            <el-button
              type="danger"
              link
              size="small"
              :icon="Delete"
              @click="confirmDelete(row.id)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredTasks.length"
          @size-change="currentPage = 1"
        />
      </div>
    </el-card>

    <!-- 任务详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="巡检任务详情"
      width="700px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div v-if="detailTask" class="detail-body">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small" class="detail-desc">
          <el-descriptions-item label="任务ID">#{{ detailTask.id }}</el-descriptions-item>
          <el-descriptions-item label="检测时间">{{ formatTime(detailTask.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="文件名">{{ detailTask.filename }}</el-descriptions-item>
          <el-descriptions-item label="置信度阈值">{{ (detailTask.confidence * 100).toFixed(0) }}%</el-descriptions-item>
          <el-descriptions-item label="A/B对比模式">
            <el-tag :type="detailTask.ab_test ? 'warning' : 'info'" size="small">
              {{ detailTask.ab_test ? '已开启' : '未开启' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="推理耗时">{{ detailTask.inference_time_ms }} ms</el-descriptions-item>
          <el-descriptions-item label="检测结果">
            <span
              v-if="detailTask.has_defect"
              style="color:#ff4d4f;font-weight:600"
            >发现 {{ detailTask.defect_count }} 处缺陷（高危 {{ detailTask.high_danger_count }} 处）</span>
            <span v-else style="color:#52c41a;font-weight:600">路面状况良好，未发现缺陷</span>
          </el-descriptions-item>
          <el-descriptions-item label="预估修复费用">
            <span style="color:#1677ff;font-weight:700;font-size:15px">
              ¥{{ detailTask.total_cost.toLocaleString() }}
            </span>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 缺陷列表 -->
        <div v-if="detailDetections.length > 0" class="detail-detections">
          <div class="detail-section-title">缺陷检测明细</div>
          <el-table :data="detailDetections" size="small" stripe border>
            <el-table-column label="#" type="index" width="50" align="center" />
            <el-table-column label="缺陷类型" width="110">
              <template #default="{ row }">
                <span style="font-weight:600">{{ row.class_cn }}</span>
                <div style="font-size:11px;color:#999">{{ row.class_name }}</div>
              </template>
            </el-table-column>
            <el-table-column label="置信度" width="80" align="center">
              <template #default="{ row }">
                <span :style="{ color: row.confidence > 0.6 ? '#1677ff' : '#fa8c16', fontWeight: 600 }">
                  {{ (row.confidence * 100).toFixed(1) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="危险等级" width="90" align="center">
              <template #default="{ row }">
                <span
                  :style="{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    fontWeight: 600,
                    background: row.danger_level === '高' ? '#fff1f0' : row.danger_level === '中' ? '#fff7e6' : '#f6ffed',
                    color: row.danger_level === '高' ? '#ff4d4f' : row.danger_level === '中' ? '#fa8c16' : '#52c41a',
                    border: `1px solid ${row.danger_level === '高' ? '#ffa39e' : row.danger_level === '中' ? '#ffd591' : '#b7eb8f'}`
                  }"
                >{{ row.danger_level }}</span>
              </template>
            </el-table-column>
            <el-table-column label="预估费用" align="right">
              <template #default="{ row }">
                <span style="color:#1677ff;font-weight:600">¥{{ row.estimated_cost.toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column label="边界框 (x1,y1,x2,y2)" min-width="160">
              <template #default="{ row }">
                <span style="font-size:11px;color:#888;font-family:monospace">
                  {{ row.bbox.map(v => Math.round(v)).join(', ') }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <el-empty v-else description="本次检测未发现缺陷" :image-size="80" />
      </div>

      <div v-else style="text-align:center;padding:40px">
        <el-icon :size="48" class="is-loading"><Loading /></el-icon>
        <div style="margin-top:12px;color:#999">加载详情中…</div>
      </div>

      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { RefreshRight, Delete, View } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  getHistoryTasks,
  getHistoryTask,
  deleteHistoryTask,
  getDefectPie,
} from '../api/http.js'

use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

const CLASS_COLORS = {
  坑洼: '#ff4d4f',
  横向裂缝: '#fa8c16',
  纵向裂缝: '#fadb14',
  网状裂缝: '#52c41a',
}

// ── 状态 ───────────────────────────────────────────────
const loading = ref(false)
const tasks = ref([])
const selectedIds = ref([])
const supabaseOpen = ref([])  // 默认折叠

const filterDefect = ref('')
const filterDateRange = ref(null)

const currentPage = ref(1)
const pageSize = ref(20)

const detailVisible = ref(false)
const detailTask = ref(null)
const detailDetections = ref([])

const pieDateRange = ref(null)
const pieRaw = ref({ total_detections: 0, series: [] })

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  series: [{
    type: 'pie',
    radius: ['38%', '65%'],
    center: ['50%', '46%'],
    data: (pieRaw.value.series || []).map((item) => ({
      name: item.name,
      value: item.value,
      itemStyle: { color: CLASS_COLORS[item.name] || '#91caff' },
    })),
    label: { formatter: '{b}\n{d}%', fontSize: 11 },
  }],
}))

async function loadPie() {
  try {
    const params = {}
    if (pieDateRange.value && pieDateRange.value[0]) {
      params.startDate = pieDateRange.value[0]
      params.endDate = pieDateRange.value[1]
    }
    pieRaw.value = await getDefectPie(params)
  } catch {
    pieRaw.value = { total_detections: 0, series: [] }
  }
}

function clearPieRange() {
  pieDateRange.value = null
  loadPie()
}

// ── 加载任务列表 ────────────────────────────────────────
async function loadTasks() {
  loading.value = true
  try {
    const data = await getHistoryTasks(200, 0)
    tasks.value = data
  } catch {
    // 错误由 http.js 拦截器统一弹出
  } finally {
    loading.value = false
  }
}

// ── 筛选逻辑 ────────────────────────────────────────────
const filteredTasks = computed(() => {
  let list = tasks.value

  if (filterDefect.value === 'yes') list = list.filter(t => t.has_defect)
  else if (filterDefect.value === 'no') list = list.filter(t => !t.has_defect)

  if (filterDateRange.value && filterDateRange.value[0]) {
    const start = new Date(filterDateRange.value[0] + 'T00:00:00Z').getTime()
    const end = new Date(filterDateRange.value[1] + 'T23:59:59Z').getTime()
    list = list.filter(t => {
      const ts = new Date(t.created_at).getTime()
      return ts >= start && ts <= end
    })
  }

  return list
})

function applyDateFilter() {
  currentPage.value = 1
}

// ── 分页 ────────────────────────────────────────────────
const pagedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredTasks.value.slice(start, start + pageSize.value)
})

// ── 汇总统计 ────────────────────────────────────────────
const summary = computed(() => {
  const list = filteredTasks.value
  return {
    total: list.length,
    defects: list.reduce((s, t) => s + t.defect_count, 0),
    highDanger: list.reduce((s, t) => s + t.high_danger_count, 0),
    totalCost: list.reduce((s, t) => s + t.total_cost, 0),
  }
})

// ── 多选 ────────────────────────────────────────────────
function handleSelectionChange(rows) {
  selectedIds.value = rows.map(r => r.id)
}

// ── 删除 ────────────────────────────────────────────────
async function confirmDelete(id) {
  try {
    await ElMessageBox.confirm(`确定删除任务 #${id}？此操作不可撤销。`, '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteHistoryTask(id)
    ElMessage.success(`任务 #${id} 已删除`)
    tasks.value = tasks.value.filter(t => t.id !== id)
    loadPie()
  } catch (e) {
    if (e === 'cancel') return
  }
}

async function batchDelete() {
  if (selectedIds.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定删除所选的 ${selectedIds.value.length} 条任务？此操作不可撤销。`,
      '批量删除确认',
      { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
    )
    await Promise.all(selectedIds.value.map(id => deleteHistoryTask(id)))
    ElMessage.success(`已删除 ${selectedIds.value.length} 条任务`)
    const deleted = new Set(selectedIds.value)
    tasks.value = tasks.value.filter(t => !deleted.has(t.id))
    selectedIds.value = []
    loadPie()
  } catch (e) {
    if (e === 'cancel') return
  }
}

// ── 详情弹窗 ────────────────────────────────────────────
async function openDetail(id) {
  detailTask.value = null
  detailDetections.value = []
  detailVisible.value = true
  try {
    const data = await getHistoryTask(id)
    detailTask.value = data
    detailDetections.value = JSON.parse(data.detections_json || '[]')
  } catch {
    detailVisible.value = false
  }
}

// ── 时间格式化 ──────────────────────────────────────────
function formatTime(isoStr) {
  if (!isoStr) return '—'
  const d = new Date(isoStr)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// ── 初始化 ──────────────────────────────────────────────
onMounted(() => {
  loadTasks()
  loadPie()
})
</script>

<style scoped>
.history-tasks { display: flex; flex-direction: column; gap: 16px; }

.pie-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
.pie-controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.pie-empty { text-align: center; color: #999; padding: 28px; font-size: 14px; }
.pie-chart { height: 280px; width: 100%; }
.pie-card {}

/* Supabase 折叠卡片 */
.supabase-collapse :deep(.el-collapse-item__header) {
  padding: 0 16px; height: 48px; background: #f0f7ff;
  border: 1px solid #bae0ff; border-radius: 8px;
}
.supabase-collapse :deep(.el-collapse-item__wrap) {
  border: 1px solid #bae0ff; border-top: none;
  border-radius: 0 0 8px 8px; background: #f8fbff;
}
.supabase-header { display: flex; align-items: center; gap: 8px; }
.supabase-logo { font-size: 18px; }
.supabase-title { font-weight: 600; font-size: 14px; color: #1677ff; }
.supabase-body { padding: 4px 8px 8px; }
.supabase-desc { font-size: 13px; color: #434343; line-height: 1.7; }
.supabase-desc code {
  background: #f0f0f0; padding: 1px 6px; border-radius: 3px;
  font-family: 'Courier New', monospace; font-size: 12px; color: #c41d7f;
}
.supabase-features {
  margin: 6px 0 0 16px; padding: 0; list-style: disc;
  font-size: 12px; color: #595959;
}
.supabase-features li { margin-bottom: 4px; }
.supabase-code-block { background: #1e1e1e; border-radius: 8px; overflow: hidden; }
.code-label { padding: 8px 14px; background: #2d2d2d; font-size: 11px; color: #9cdcfe; font-family: monospace; }
.code-snippet {
  margin: 0; padding: 12px 14px;
  font-size: 11.5px; line-height: 1.6;
  color: #d4d4d4; font-family: 'Courier New', monospace;
  white-space: pre-wrap; word-break: break-all;
}

/* 汇总卡片 */
.summary-row { margin: 0; }
.summary-card :deep(.el-card__body) { padding: 14px 16px; }
.summary-inner { display: flex; align-items: center; gap: 14px; }
.summary-icon {
  width: 46px; height: 46px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  color: white; flex-shrink: 0;
}
.summary-value { font-size: 22px; font-weight: 800; color: #1a1a2e; }
.summary-label { font-size: 12px; color: #8c8c8c; margin-top: 2px; }

/* 筛选栏 */
.filter-card :deep(.el-card__body) { padding: 12px 16px; }
.filter-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.filter-left { display: flex; align-items: center; flex-wrap: wrap; gap: 0; }
.filter-right { display: flex; align-items: center; gap: 8px; }

/* 表格卡片 */
.table-card {}
.card-title { font-weight: 600; font-size: 14px; color: #1a1a2e; }
.table-count { font-size: 13px; color: #8c8c8c; }
.task-id { font-family: monospace; font-weight: 700; color: #1677ff; }
.time-text { font-size: 12px; color: #595959; }
.conf-text { font-weight: 600; color: #1677ff; }
.count-bad { font-weight: 700; color: #fa8c16; }
.count-danger { font-weight: 700; color: #ff4d4f; }
.count-ok { color: #52c41a; font-weight: 600; }
.cost-text { font-weight: 700; color: #1677ff; }
.time-ms { font-size: 12px; color: #8c8c8c; font-family: monospace; }
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }

/* 详情弹窗 */
.detail-body { display: flex; flex-direction: column; gap: 16px; }
.detail-desc {}
.detail-section-title {
  font-size: 13px; font-weight: 600; color: #434343;
  margin-bottom: 10px; padding-bottom: 6px;
  border-bottom: 2px solid #e8f4ff;
}
.detail-detections {}
</style>
