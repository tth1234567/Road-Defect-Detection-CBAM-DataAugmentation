<template>
  <div class="reports">
    <!-- 页头 -->
    <el-card shadow="hover" class="header-card">
      <div style="display:flex;align-items:center;justify-content:space-between">
        <div>
          <div class="page-title">维修任务报告</div>
          <div class="page-desc">本次巡检缺陷汇总，可按类型和危险等级筛选，导出 PDF 提交维修部门</div>
        </div>
        <el-button type="danger" :icon="Download" size="large" @click="exportPDF" :loading="exporting">
          导出维修任务 PDF
        </el-button>
      </div>
    </el-card>

    <!-- 筛选栏 -->
    <el-card shadow="hover" class="filter-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="6">
          <el-select v-model="filterClass" placeholder="缺陷类型（全部）" clearable style="width:100%">
            <el-option label="坑洼" value="坑洼" />
            <el-option label="横向裂缝" value="横向裂缝" />
            <el-option label="纵向裂缝" value="纵向裂缝" />
            <el-option label="网状裂缝" value="网状裂缝" />
          </el-select>
        </el-col>
        <el-col :span="5">
          <el-select v-model="filterDanger" placeholder="危险等级（全部）" clearable style="width:100%">
            <el-option label="高危" value="高" />
            <el-option label="中危" value="中" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button @click="resetFilter" :icon="RefreshRight">重置筛选</el-button>
        </el-col>
        <el-col :span="9" style="text-align:right">
          <span style="color:#8c8c8c;font-size:13px">
            共 {{ filteredRows.length }} 条缺陷记录 |
            高危 {{ highCount }} 处 |
            总费用 <strong style="color:#cf1322">¥{{ totalCost.toLocaleString() }}</strong>
          </span>
        </el-col>
      </el-row>
    </el-card>

    <!-- 报告主体（此区域用于 PDF 导出） -->
    <div ref="reportRef">
      <!-- 报告标题头（仅打印时显示，屏幕上也显示） -->
      <el-card shadow="hover" class="report-title-card">
        <div class="report-title-inner">
          <div class="report-main-title">智巡 SmartInspect — 道路缺陷巡检维修任务报告</div>
          <div class="report-sub">
            河北工业大学 · 道路缺陷智能检测系统 ·
            生成时间：{{ reportTime }} · 检测模型：YOLOv8n+CBAM（论文最终模型）
          </div>
        </div>
      </el-card>

      <!-- 汇总统计卡片 -->
      <el-row :gutter="12" style="margin:12px 0">
        <el-col :span="6" v-for="s in summaryStats" :key="s.label">
          <el-card shadow="never" :style="{ borderLeft: `4px solid ${s.color}`, borderRadius: '8px' }">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <div>
                <div style="font-size:22px;font-weight:700;color:#1a1a2e">{{ s.value }}</div>
                <div style="font-size:12px;color:#8c8c8c">{{ s.label }}</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 缺陷明细表格 -->
      <el-card shadow="hover">
        <template #header>
          <span class="card-title">缺陷明细表</span>
        </template>

        <div v-if="allRows.length === 0" style="padding:20px 0">
          <el-empty description="暂无数据。请先在「智能检测工作台」完成巡检分析" :image-size="80" />
        </div>

        <el-table v-else :data="pagedRows" style="width:100%" :row-class-name="rowCls" size="small">
          <el-table-column type="index" :index="(i) => (currentPage-1)*pageSize+i+1" label="序号" width="60" />
          <el-table-column prop="filename" label="图片名" min-width="130" show-overflow-tooltip />
          <el-table-column prop="class_cn" label="缺陷类型" width="110">
            <template #default="{ row }">
              <span :style="{
                display:'inline-block', padding:'2px 8px', borderRadius:'4px', fontSize:'12px',
                background: row.danger_level==='高' ? '#fff1f0' : '#fff7e6',
                color: row.danger_level==='高' ? '#cf1322' : '#d46b08',
                border: `1px solid ${row.danger_level==='高' ? '#ffa39e' : '#ffd591'}`
              }">{{ row.class_cn }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="danger_level" label="危险等级" width="90">
            <template #default="{ row }">
              <span :style="{
                display:'inline-block', padding:'2px 8px', borderRadius:'4px', fontSize:'12px',
                background: '#fff',
                color: row.danger_level==='高' ? '#cf1322' : '#d46b08',
                border: `1px solid ${row.danger_level==='高' ? '#ffa39e' : '#ffd591'}`
              }">{{ row.danger_level }}危</span>
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度" width="80">
            <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
          </el-table-column>
          <el-table-column label="GPS 坐标" width="170" show-overflow-tooltip>
            <template #default="{ row }">
              <span style="font-size:11px;color:#888">
                {{ row.lat.toFixed(4) }}°N, {{ row.lng.toFixed(4) }}°E
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="estimated_cost" label="预估费用（元）" width="120">
            <template #default="{ row }">
              <span style="color:#cf1322;font-weight:600">¥{{ row.estimated_cost.toLocaleString() }}</span>
            </template>
          </el-table-column>
          <el-table-column label="处理建议" min-width="120">
            <template #default="{ row }">
              <span style="font-size:12px;color:#595959">{{ getAdvice(row.class_cn) }}</span>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-if="filteredRows.length > pageSize"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="filteredRows.length"
          layout="total, prev, pager, next"
          style="margin-top:12px;justify-content:flex-end"
        />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, RefreshRight } from '@element-plus/icons-vue'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import { inspectionStore } from '../stores/inspectionStore.js'

const reportRef = ref(null)
const filterClass = ref('')
const filterDanger = ref('')
const currentPage = ref(1)
const pageSize = 15
const exporting = ref(false)

const reportTime = computed(() => new Date().toLocaleString('zh-CN'))

// 将 store 里的嵌套数据展开为一行一行的缺陷记录
const allRows = computed(() => {
  const rows = []
  inspectionStore.defectRecords.forEach(record => {
    record.detections.forEach(det => {
      rows.push({
        filename: record.filename,
        ...det,
        lat: record.gpsCoord[1],
        lng: record.gpsCoord[0],
      })
    })
  })
  return rows
})

const filteredRows = computed(() => {
  let rows = allRows.value
  if (filterClass.value) rows = rows.filter(r => r.class_cn === filterClass.value)
  if (filterDanger.value) rows = rows.filter(r => r.danger_level === filterDanger.value)
  return rows
})

const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredRows.value.slice(start, start + pageSize)
})

const highCount = computed(() => filteredRows.value.filter(r => r.danger_level === '高').length)
const totalCost = computed(() => filteredRows.value.reduce((s, r) => s + r.estimated_cost, 0))

const summaryStats = computed(() => [
  { label: '巡检照片数', value: `${inspectionStore.defectRecords.length} 张`, color: '#1677ff' },
  { label: '缺陷总数', value: `${allRows.value.length} 处`, color: '#fa8c16' },
  { label: '高危缺陷', value: `${allRows.value.filter(r=>r.danger_level==='高').length} 处`, color: '#ff4d4f' },
  { label: '预估总费用', value: `¥${allRows.value.reduce((s,r)=>s+r.estimated_cost,0).toLocaleString()}`, color: '#52c41a' },
])

function resetFilter() {
  filterClass.value = ''
  filterDanger.value = ''
  currentPage.value = 1
}

function rowCls({ row }) {
  return row.danger_level === '高' ? 'danger-row' : ''
}

function getAdvice(classCn) {
  const map = {
    '坑洼': '优先处理，开挖填补，恢复路面平整',
    '横向裂缝': '灌缝处理，防止水渗入路基',
    '纵向裂缝': '灌缝处理，监测扩展情况',
    '网状裂缝': '结构性修复，铣刨重铺面层',
  }
  return map[classCn] || '现场核查后处理'
}

// PDF 导出
async function exportPDF() {
  if (allRows.value.length === 0) {
    ElMessage.warning('暂无数据，请先完成巡检分析')
    return
  }
  exporting.value = true
  ElMessage.info('正在生成 PDF，请稍候...')
  try {
    const el = reportRef.value
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffffff',
      logging: false,
    })
    const imgData = canvas.toDataURL('image/jpeg', 0.95)
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const pageW = 210
    const pageH = 297
    const imgW = pageW - 20
    const imgH = (canvas.height * imgW) / canvas.width

    let y = 10
    let remaining = imgH
    while (remaining > 0) {
      const sliceH = Math.min(remaining, pageH - 20)
      const srcY = (imgH - remaining) / imgH * canvas.height
      const sliceCanvas = document.createElement('canvas')
      sliceCanvas.width = canvas.width
      sliceCanvas.height = (sliceH / imgH) * canvas.height
      const ctx = sliceCanvas.getContext('2d')
      ctx.drawImage(canvas, 0, srcY, canvas.width, sliceCanvas.height, 0, 0, canvas.width, sliceCanvas.height)
      if (y < imgH) {
        if (y > 10) pdf.addPage()
        pdf.addImage(sliceCanvas.toDataURL('image/jpeg', 0.95), 'JPEG', 10, 10, imgW, sliceH)
      }
      remaining -= sliceH
      y += sliceH
    }
    pdf.save(`SmartInspect_维修任务报告_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '')}.pdf`)
    ElMessage.success('PDF 已成功导出！')
  } catch (err) {
    ElMessage.error('PDF 导出失败：' + err.message)
  }
  exporting.value = false
}
</script>

<style scoped>
.reports { display: flex; flex-direction: column; gap: 16px; }
.header-card {}
.page-title { font-size: 18px; font-weight: 700; color: #1a1a2e; }
.page-desc { font-size: 13px; color: #8c8c8c; margin-top: 4px; }
.filter-card :deep(.el-card__body) { padding: 14px 20px; }
.card-title { font-weight: 600; font-size: 14px; }
.report-title-card { background: linear-gradient(135deg, #001529, #003366); }
.report-title-inner { text-align: center; padding: 8px 0; }
.report-main-title { color: #fff; font-size: 18px; font-weight: 700; }
.report-sub { color: #a8d8ff; font-size: 12px; margin-top: 6px; }
:deep(.danger-row) { background-color: #fff1f0 !important; }
:deep(.danger-row:hover > td) { background-color: #ffe7e7 !important; }
</style>
