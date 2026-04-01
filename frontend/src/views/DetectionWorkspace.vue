<template>
  <div class="workspace">
    <!-- 顶部控制区 -->
    <el-card class="control-card" shadow="hover">
      <div class="control-header">
        <div class="control-title">
          <el-icon style="color:#1677ff;font-size:20px"><Search /></el-icon>
          智能巡检分析
        </div>
        <div class="control-desc">上传自动驾驶车辆回传的道路照片，系统将自动识别缺陷并生成维修清单</div>
      </div>

      <el-row :gutter="24" style="margin-top:16px">
        <!-- 上传区 -->
        <el-col :span="12">
          <el-upload
            ref="uploadRef"
            v-model:file-list="fileList"
            :auto-upload="false"
            :multiple="true"
            accept="image/jpeg,image/png,image/jpg"
            list-type="picture"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            drag
          >
            <el-icon :size="40" style="color:#c0c4cc"><UploadFilled /></el-icon>
            <div style="margin-top:8px;font-size:14px;color:#606266">
              拖拽照片到此处，或 <em style="color:#1677ff">点击选择文件</em>
            </div>
            <div style="font-size:12px;color:#909399;margin-top:4px">
              支持 JPG/PNG，可同时上传多张
            </div>
          </el-upload>
        </el-col>

        <!-- 参数控制 -->
        <el-col :span="12">
          <div class="param-group">
            <div class="param-label">置信度阈值：<strong>{{ confidence }}</strong></div>
            <el-slider v-model="confidence" :min="0.1" :max="0.9" :step="0.05" show-stops />
            <div class="param-hint">越低=检测越多但可能有误报；越高=更精准但可能漏检</div>
          </div>

          <div class="param-group" style="margin-top:16px">
            <div class="param-label">
              消融实验 A/B 对比模式
              <el-switch v-model="abTest" style="margin-left:12px" />
            </div>
            <div class="param-hint">开启后同时运行基线 YOLOv8n 对比，展示 CBAM 改进效果</div>
          </div>

          <div style="margin-top:20px;display:flex;gap:12px">
            <el-button
              type="primary" :icon="VideoPlay" size="large"
              :disabled="fileList.length === 0 || analyzing"
              :loading="analyzing"
              @click="startAnalysis"
            >
              {{ analyzing ? `分析中 ${currentIdx}/${fileList.length}` : '开始巡检分析' }}
            </el-button>
            <el-button :icon="MagicStick" size="large" @click="loadDemoImages" :loading="loadingDemo">
              Demo 演示
            </el-button>
            <el-button v-if="results.length > 0" :icon="Delete" @click="clearAll">清空</el-button>
          </div>
        </el-col>
      </el-row>

      <!-- GPS 说明折叠卡片 -->
      <el-collapse style="margin-top:16px;border:none">
        <el-collapse-item name="gps">
          <template #title>
            <span style="font-size:13px;color:#595959;display:flex;align-items:center;gap:6px">
              <el-icon style="color:#1677ff"><InfoFilled /></el-icon>
              GPS 坐标获取说明（点击展开）
            </span>
          </template>
          <div style="padding:4px 0 8px 0">
            <el-alert type="info" :closable="false" style="margin-bottom:10px">
              <template #title>
                <span style="font-weight:600">方式一：自动提取真实 EXIF GPS</span>
              </template>
              <div style="font-size:13px;margin-top:4px;line-height:1.7">
                若照片由手机或带 GPS 的相机直接拍摄，文件中包含 EXIF 元数据，系统会自动提取真实经纬度坐标并显示在地图上。
              </div>
            </el-alert>
            <el-alert type="success" :closable="false">
              <template #title>
                <span style="font-weight:600">方式二：自动按预设路线分配坐标（兜底）</span>
              </template>
              <div style="font-size:13px;margin-top:4px;line-height:1.7">
                若照片来自电脑导入、截图或无 GPS 设备，系统将按照片顺序沿「天津市预设巡检路线」均匀分配坐标，模拟自动驾驶车辆巡检路径。<br/>
                预设路线起点：<strong>117.1512°E, 39.1042°N</strong>（天津西部）→
                终点：<strong>117.2769°E, 39.1408°N</strong>（天津东部），全程覆盖约 12 km 城市道路。
              </div>
            </el-alert>
          </div>
        </el-collapse-item>
      </el-collapse>

      <!-- 进度条 -->
      <div v-if="analyzing" style="margin-top:16px">
        <div style="margin-bottom:8px;font-size:13px;color:#595959">
          正在分析：<strong>{{ currentFileName }}</strong>
        </div>
        <el-progress :percentage="progressPercent" :stroke-width="12" striped striped-flow />
      </div>
    </el-card>

    <!-- 主内容区：汇总表 + 详情面板 -->
    <el-row :gutter="16" style="margin-top:16px" v-if="results.length > 0 || analyzing">
      <!-- 左：待维修路段汇总表 -->
      <el-col :span="abTest ? 24 : 14">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span class="card-title">待维修路段汇总</span>
              <div style="display:flex;align-items:center;gap:10px" v-if="results.length > 0">
                <el-switch
                  v-model="onlyHighRisk"
                  active-text="仅看高危"
                  inactive-text="全部"
                  inline-prompt
                />
                <el-tag type="danger">共 {{ totalDefects }} 处缺陷</el-tag>
                <el-tag type="warning" style="margin-left:8px">高危 {{ highDangerCount }} 处</el-tag>
                <el-tag type="success" style="margin-left:8px">¥{{ totalCost.toLocaleString() }}</el-tag>
              </div>
            </div>
          </template>

          <div v-if="displayResults.length === 0 && !analyzing" class="empty-hint">
            <el-empty description="暂无数据，点击「开始巡检分析」后显示结果" :image-size="80" />
          </div>

          <el-table
            v-else
            :data="displayResults"
            style="width:100%"
            max-height="400"
            @row-click="selectRow"
            highlight-current-row
            :row-class-name="rowClassName"
            size="small"
          >
            <el-table-column type="index" label="序号" width="55" />
            <el-table-column prop="filename" label="图片名" min-width="120" show-overflow-tooltip />
            <el-table-column label="缺陷类型" min-width="120">
              <template #default="{ row }">
                <el-tag v-for="d in row.detections" :key="d.class_name"
                  :type="d.danger_level==='高'?'danger':'warning'" size="small"
                  style="margin:1px">{{ d.class_cn }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="最高危险等级" width="110">
              <template #default="{ row }">
                <el-tag :type="row.maxDanger==='高'?'danger':'warning'" size="small">
                  {{ row.maxDanger }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="GPS 坐标" width="155" show-overflow-tooltip>
              <template #default="{ row }">
                <span style="font-size:11px;color:#888">
                  {{ row.gpsCoord[1].toFixed(4) }}°N, {{ row.gpsCoord[0].toFixed(4) }}°E
                </span>
              </template>
            </el-table-column>
            <el-table-column label="预估费用" width="90">
              <template #default="{ row }">
                <span style="color:#cf1322;font-weight:600">¥{{ row.totalCost.toLocaleString() }}</span>
              </template>
            </el-table-column>
          </el-table>

          <!-- 合计行 -->
          <div v-if="displayResults.length > 0" class="table-footer">
            合计：{{ displayResults.length }} 条需维修路段 ·
            预估总费用 <strong style="color:#cf1322">¥{{ filteredTotalCost.toLocaleString() }}</strong> 元
          </div>
        </el-card>
      </el-col>

      <!-- 右：单图详情面板（非A/B模式时显示） -->
      <el-col :span="10" v-if="!abTest && selectedResult">
        <el-card shadow="hover" class="detail-card">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span class="card-title">{{ selectedResult.filename }}</span>
              <el-button size="small" type="warning" plain @click="showCorrectionDialog = true">
                识别有误？人工纠正
              </el-button>
            </div>
          </template>

          <!-- Before/After 拖拽滑块对比 -->
          <div
            class="compare-slider-wrap"
            ref="compareWrapRef"
            @mousedown.prevent="startDrag"
            @mousemove="onDrag"
            @mouseup="stopDrag"
            @mouseleave="stopDrag"
          >
            <!-- 底层：检测结果图（完整） -->
            <img
              class="compare-img"
              :src="`data:image/jpeg;base64,${selectedResult.annotated_image_b64}`"
              draggable="false"
            />
            <!-- 上层：原图（clip-path 裁切，左侧露出原图） -->
            <img
              class="compare-img compare-top"
              :src="`data:image/jpeg;base64,${selectedResult.originalB64}`"
              :style="{ clipPath: `inset(0 ${100 - sliderPct}% 0 0)` }"
              draggable="false"
            />
            <!-- 分割线 + 拖拽把手 -->
            <div class="compare-divider" :style="{ left: sliderPct + '%' }">
              <div class="compare-handle">⇄</div>
            </div>
            <!-- 左右标签 -->
            <span class="compare-label compare-label-left">原图</span>
            <span class="compare-label compare-label-right">检测结果</span>
          </div>

          <!-- 检测框详情 -->
          <div style="margin-top:12px">
            <div v-for="(d, i) in selectedResult.detections" :key="i" class="detection-item">
              <el-tag :type="d.danger_level==='高'?'danger':'warning'" size="small">{{ d.class_cn }}</el-tag>
              <span class="det-conf">置信度 {{ (d.confidence*100).toFixed(1) }}%</span>
              <el-tag :type="d.danger_level==='高'?'danger':'warning'" size="small" effect="plain">
                {{ d.danger_level }}危
              </el-tag>
              <span class="det-cost">¥{{ d.estimated_cost }}</span>
            </div>
          </div>

          <!-- 推理时间 -->
          <div style="margin-top:8px;font-size:11px;color:#aaa">
            推理耗时：{{ selectedResult.inference_time_ms }} ms ·
            模型：YOLOv8n+CBAM
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- A/B 对比展示区 -->
    <div v-if="abTest && selectedResult && selectedResult.baseline_result" style="margin-top:16px">
      <el-card shadow="hover">
        <template #header>
          <span class="card-title">消融实验 A/B 对比 — {{ selectedResult.filename }}</span>
        </template>
        <el-row :gutter="24">
          <el-col :span="12">
            <div class="ab-header improved">改进模型（YOLOv8n+CBAM）— 论文最终模型</div>
            <img :src="`data:image/jpeg;base64,${selectedResult.annotated_image_b64}`" class="ab-img" />
            <div class="ab-stats">
              检测到 {{ selectedResult.detections.length }} 处缺陷 |
              高危 {{ selectedResult.detections.filter(d=>d.danger_level==='高').length }} 处
            </div>
          </el-col>
          <el-col :span="12">
            <div class="ab-header baseline">基线模型（YOLOv8n）— 对照组</div>
            <img :src="`data:image/jpeg;base64,${selectedResult.baseline_result.annotated_image_b64}`" class="ab-img" />
            <div class="ab-stats">
              检测到 {{ selectedResult.baseline_result.detections.length }} 处缺陷
            </div>
          </el-col>
        </el-row>
        <div style="margin-top:12px;text-align:center;font-size:13px;color:#595959">
          点击汇总表中不同图片行查看对应对比结果
        </div>
      </el-card>
    </div>

    <!-- 人工纠偏弹窗 -->
    <el-dialog v-model="showCorrectionDialog" title="人工纠偏" width="400px">
      <el-form :model="correctionForm" label-width="80px">
        <el-form-item label="正确类别">
          <el-select v-model="correctionForm.correctClass" placeholder="请选择">
            <el-option label="坑洼" value="pothole" />
            <el-option label="横向裂缝" value="lateral_crack" />
            <el-option label="纵向裂缝" value="longitudinal_crack" />
            <el-option label="网状裂缝" value="alligator_crack" />
            <el-option label="无缺陷（误检）" value="none" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="correctionForm.note" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCorrectionDialog = false">取消</el-button>
        <el-button type="primary" @click="submitCorrection">提交纠偏</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, MagicStick, Delete, UploadFilled, InfoFilled } from '@element-plus/icons-vue'
import { detectImage, getDemoImages } from '../api/http.js'
import { inspectionStore } from '../stores/inspectionStore.js'
import exifr from 'exifr'

// ── 天津市预设巡检路线（真实道路坐标序列） ──────────────────
const TIANJIN_ROUTE = [
  [117.1512, 39.1042], [117.1558, 39.1065], [117.1601, 39.1083],
  [117.1643, 39.1101], [117.1688, 39.1124], [117.1730, 39.1148],
  [117.1778, 39.1172], [117.1822, 39.1193], [117.1868, 39.1215],
  [117.1913, 39.1238], [117.1958, 39.1260], [117.2002, 39.1281],
  [117.2048, 39.1302], [117.2093, 39.1322], [117.2138, 39.1341],
  [117.2182, 39.1358], [117.2227, 39.1374], [117.2272, 39.1388],
  [117.2316, 39.1400], [117.2360, 39.1411], [117.2404, 39.1420],
  [117.2447, 39.1427], [117.2490, 39.1432], [117.2532, 39.1435],
  [117.2574, 39.1436], [117.2615, 39.1435], [117.2655, 39.1431],
  [117.2694, 39.1426], [117.2732, 39.1418], [117.2769, 39.1408],
]

function assignRouteCoord(index, total) {
  if (total <= 1) return TIANJIN_ROUTE[0]
  const routeIdx = Math.round(index * (TIANJIN_ROUTE.length - 1) / (total - 1))
  return TIANJIN_ROUTE[Math.min(routeIdx, TIANJIN_ROUTE.length - 1)]
}

// ── 状态 ────────────────────────────────────────────────────
const uploadRef = ref(null)
const fileList = ref([])
const confidence = ref(0.25)
const abTest = ref(false)
const analyzing = ref(false)
const loadingDemo = ref(false)
const currentIdx = ref(0)
const currentFileName = ref('')
const results = ref([])
const selectedResult = ref(null)
const showCorrectionDialog = ref(false)
const correctionForm = ref({ correctClass: '', note: '' })
const onlyHighRisk = ref(false)

// ── Before/After 滑块对比 ────────────────────────────────────
const sliderPct = ref(50)
const isDragging = ref(false)
const compareWrapRef = ref(null)

function startDrag(e) {
  isDragging.value = true
  updateSlider(e)
}
function onDrag(e) {
  if (!isDragging.value) return
  updateSlider(e)
}
function stopDrag() {
  isDragging.value = false
}
function updateSlider(e) {
  const el = compareWrapRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const x = (e.clientX - rect.left) / rect.width
  sliderPct.value = Math.max(0, Math.min(100, x * 100))
}

// ── 计算属性 ─────────────────────────────────────────────────
const progressPercent = computed(() => {
  if (fileList.value.length === 0) return 0
  return Math.round((currentIdx.value / fileList.value.length) * 100)
})

const totalDefects = computed(() => results.value.reduce((s, r) => s + r.detections.length, 0))
const highDangerCount = computed(() => results.value.reduce((s, r) =>
  s + r.detections.filter(d => d.danger_level === '高').length, 0))
const totalCost = computed(() => results.value.reduce((s, r) => s + r.totalCost, 0))
const displayResults = computed(() =>
  onlyHighRisk.value ? results.value.filter(r => r.maxDanger === '高') : results.value
)
const filteredTotalCost = computed(() =>
  displayResults.value.reduce((s, r) => s + r.totalCost, 0)
)

// ── 文件操作 ─────────────────────────────────────────────────
function handleFileChange(file) {
  // 手动生成本地预览 URL，确保 list-type="picture" 缩略图可见
  if (file.raw && !file.url) {
    file.url = URL.createObjectURL(file.raw)
  }
}
function handleFileRemove() {
  if (fileList.value.length === 0) results.value = []
}

// ── GPS 提取 ─────────────────────────────────────────────────
async function extractGPS(file, index, total) {
  try {
    const gps = await exifr.gps(file)
    if (gps && gps.longitude && gps.latitude) {
      return [gps.longitude, gps.latitude]
    }
  } catch {}
  return assignRouteCoord(index, total)
}

// ── 图片转 Base64（用于显示原图） ───────────────────────────
function fileToBase64(file) {
  return new Promise((resolve) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target.result.split(',')[1])
    reader.readAsDataURL(file)
  })
}

// ── 开始分析 ─────────────────────────────────────────────────
async function startAnalysis() {
  if (fileList.value.length === 0) return
  results.value = []
  inspectionStore.clear()
  analyzing.value = true
  currentIdx.value = 0

  const total = fileList.value.length

  for (let i = 0; i < total; i++) {
    const fileItem = fileList.value[i]
    const file = fileItem.raw
    currentIdx.value = i + 1
    currentFileName.value = file.name

    try {
      const [gpsCoord, originalB64] = await Promise.all([
        extractGPS(file, i, total),
        fileToBase64(file),
      ])

      const resp = await detectImage(file, confidence.value, abTest.value)

      if (resp.has_defect) {
        const record = {
          filename: file.name,
          gpsCoord,
          originalB64,
          ...resp,
          maxDanger: resp.detections.some(d => d.danger_level === '高') ? '高' : '中',
          totalCost: resp.detections.reduce((s, d) => s + d.estimated_cost, 0),
        }
        results.value.push(record)
        inspectionStore.addRecord(record)

        // 默认选中最新一条
        selectedResult.value = record
      }
    } catch (err) {
      ElMessage.warning(`图片 ${file.name} 处理失败，已跳过`)
    }
  }

  analyzing.value = false
  currentIdx.value = 0

  if (results.value.length === 0) {
    ElMessage.info('本次巡检未检测到缺陷，可尝试降低置信度后重新分析')
  } else {
    ElMessage.success(`巡检完成！共发现 ${results.value.length} 处需维修路段`)
  }
}

// ── Demo 演示 ────────────────────────────────────────────────
async function loadDemoImages() {
  loadingDemo.value = true
  try {
    const demoList = await getDemoImages()
    fileList.value = demoList.map(d => ({
      name: d.filename,
      raw: base64ToFile(d.image_b64, d.filename),
    }))
    ElMessage.success(`已加载 ${demoList.length} 张演示图片，点击「开始巡检分析」运行`)
  } catch {
    ElMessage.error('加载 Demo 图片失败，请确认后端已启动')
  }
  loadingDemo.value = false
}

function base64ToFile(b64, filename) {
  const byteStr = atob(b64)
  const arr = new Uint8Array(byteStr.length)
  for (let i = 0; i < byteStr.length; i++) arr[i] = byteStr.charCodeAt(i)
  return new File([arr], filename, { type: 'image/jpeg' })
}

// ── 表格操作 ─────────────────────────────────────────────────
function selectRow(row) {
  selectedResult.value = row
}

function rowClassName({ row }) {
  return row.maxDanger === '高' ? 'high-danger-row' : ''
}

function clearAll() {
  ElMessageBox.confirm('确定清空本次巡检结果？', '提示', { type: 'warning' })
    .then(() => {
      results.value = []
      fileList.value = []
      selectedResult.value = null
      onlyHighRisk.value = false
      inspectionStore.clear()
    }).catch(() => {})
}

// ── 人工纠偏 ─────────────────────────────────────────────────
function submitCorrection() {
  showCorrectionDialog.value = false
  correctionForm.value = { correctClass: '', note: '' }
  ElMessage.success('感谢纠偏！已记录，将用于后续模型优化迭代。')
}

watch(onlyHighRisk, () => {
  if (!selectedResult.value) return
  const exists = displayResults.value.includes(selectedResult.value)
  if (!exists) selectedResult.value = displayResults.value[0] || null
})
</script>

<style scoped>
.workspace { display: flex; flex-direction: column; gap: 16px; }
.control-card :deep(.el-card__body) { padding: 20px; }
.control-header { border-bottom: 1px solid #f0f0f0; padding-bottom: 12px; margin-bottom: 4px; }
.control-title { font-size: 16px; font-weight: 700; color: #1a1a2e; display: flex; align-items: center; gap: 8px; }
.control-desc { font-size: 13px; color: #8c8c8c; margin-top: 4px; }
.param-group {}
.param-label { font-size: 14px; color: #434343; margin-bottom: 8px; display: flex; align-items: center; }
.param-hint { font-size: 11px; color: #aaa; margin-top: 4px; }
.card-title { font-weight: 600; font-size: 14px; }
.empty-hint { padding: 20px 0; }
.table-footer {
  margin-top: 12px; padding: 8px 12px;
  background: #fafafa; border-radius: 6px; font-size: 13px; color: #595959;
}
.summary-badges { display: flex; gap: 0; }

/* 高危行红色背景 */
:deep(.high-danger-row) { background-color: #fff1f0 !important; }
:deep(.high-danger-row:hover > td) { background-color: #ffe7e7 !important; }

.detail-card :deep(.el-card__body) { padding: 16px; }

/* ── Before/After 滑块对比 ─────────────────────────────────── */
.compare-slider-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  cursor: ew-resize;
  user-select: none;
  background: #000;
}
.compare-img {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
}
.compare-top {
  /* clip-path set via inline style */
}
.compare-divider {
  position: absolute;
  top: 0; bottom: 0;
  width: 2px;
  background: #fff;
  transform: translateX(-50%);
  pointer-events: none;
  box-shadow: 0 0 8px rgba(0,0,0,.5);
}
.compare-handle {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 36px; height: 36px;
  background: #fff;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; color: #1677ff;
  box-shadow: 0 2px 10px rgba(0,0,0,.3);
  pointer-events: none;
}
.compare-label {
  position: absolute;
  bottom: 8px;
  padding: 2px 8px;
  background: rgba(0,0,0,.55);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
  pointer-events: none;
}
.compare-label-left { left: 8px; }
.compare-label-right { right: 8px; }
.detection-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px;
}
.det-conf { color: #595959; }
.det-cost { margin-left: auto; color: #cf1322; font-weight: 600; }

.ab-header {
  padding: 6px 12px; border-radius: 6px 6px 0 0;
  font-size: 13px; font-weight: 600; margin-bottom: 8px; text-align: center;
}
.ab-header.improved { background: #e6f4ff; color: #1677ff; }
.ab-header.baseline { background: #f6ffed; color: #389e0d; }
.ab-img { width: 100%; border-radius: 0 0 6px 6px; border: 1px solid #e8e8e8; }
.ab-stats { text-align: center; font-size: 12px; color: #8c8c8c; margin-top: 6px; }
</style>
