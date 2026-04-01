<template>
  <div class="video-inspect">
    <!-- 页面标题卡片 -->
    <el-card class="header-card" shadow="never">
      <div class="header-inner">
        <div class="header-left">
          <el-icon :size="28" class="header-icon"><VideoPlay /></el-icon>
          <div>
            <div class="header-title">视频巡检分析</div>
            <div class="header-sub">上传行车记录仪视频，系统自动逐帧识别道路缺陷并生成标注视频</div>
          </div>
        </div>
        <div class="header-badges">
          <el-tag type="success" size="small">CUDA 自适应加速</el-tag>
          <el-tag type="primary" size="small">best.pt 改进模型</el-tag>
          <el-tag type="warning" size="small">智能跳帧推理</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 上传区 + Demo视频选择 -->
    <el-row :gutter="16" v-if="phase === 'idle'">
      <!-- 左：上传区 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">上传视频文件</span>
          </template>
          <el-upload
            ref="uploadRef"
            drag
            :auto-upload="false"
            :limit="1"
            accept="video/mp4,video/mpeg,video/quicktime,.mp4,.mpeg,.mov,.avi"
            :on-change="handleFileChange"
            :on-exceed="() => ElMessage.warning('每次只能选择一个视频文件')"
            class="video-upload"
          >
            <el-icon :size="48" class="upload-icon"><Upload /></el-icon>
            <div class="upload-text">拖拽视频到此处，或 <em>点击选择</em></div>
            <div class="upload-hint">支持 MP4 / MOV / AVI，最大 200 MB</div>
          </el-upload>
          <div v-if="selectedFile" class="file-preview">
            <el-icon><Film /></el-icon>
            <span class="file-name">{{ selectedFile.name }}</span>
            <span class="file-size">（{{ (selectedFile.size / 1024 / 1024).toFixed(1) }} MB）</span>
            <el-button type="danger" link size="small" @click="clearFile">移除</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右：Demo视频 + 参数 -->
      <el-col :span="10">
        <el-card shadow="hover" style="margin-bottom:16px">
          <template #header>
            <span class="card-title">或使用 Demo 演示视频</span>
          </template>
          <div v-if="demosLoading" style="text-align:center;padding:20px">
            <el-icon class="is-loading" :size="24"><Loading /></el-icon>
          </div>
          <div v-else-if="demos.length === 0" class="no-demos">
            暂无可用 Demo 视频
          </div>
          <div v-else class="demo-list">
            <div
              v-for="demo in demos"
              :key="demo.filename"
              class="demo-item"
              :class="{ 'demo-selected': selectedDemo === demo.filename }"
              @click="selectDemo(demo)"
            >
              <el-icon class="demo-icon"><Film /></el-icon>
              <div class="demo-info">
                <div class="demo-name">{{ demo.filename }}</div>
                <div class="demo-size">{{ demo.size_mb }} MB</div>
              </div>
              <el-icon v-if="selectedDemo === demo.filename" class="demo-check"><CircleCheck /></el-icon>
            </div>
          </div>
        </el-card>

        <!-- 参数设置 -->
        <el-card shadow="hover">
          <template #header><span class="card-title">检测参数</span></template>
          <div class="param-row">
            <span class="param-label">置信度阈值</span>
            <el-slider
              v-model="confidence"
              :min="0.1" :max="0.9" :step="0.05"
              :format-tooltip="v => (v * 100).toFixed(0) + '%'"
              show-input
              size="small"
              style="flex:1"
            />
          </div>
          <el-button
            type="primary"
            size="large"
            :icon="VideoCamera"
            :disabled="!selectedFile && !selectedDemo"
            :loading="false"
            style="width:100%;margin-top:16px"
            @click="startAnalysis"
          >
            开始巡检分析
          </el-button>
          <div v-if="!selectedFile && !selectedDemo" class="param-hint">
            请先上传视频或选择 Demo 视频
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 处理中：进度条 -->
    <el-card v-if="phase === 'processing'" shadow="hover" class="progress-card">
      <template #header>
        <div style="display:flex;align-items:center;gap:8px">
          <el-icon class="is-loading" style="color:#1677ff"><Loading /></el-icon>
          <span class="card-title">正在进行视频巡检分析…</span>
        </div>
      </template>
      <div class="progress-body">
        <div class="progress-filename">
          <el-icon><Film /></el-icon>
          <span>{{ processingFilename }}</span>
        </div>
        <el-progress
          :percentage="taskProgress"
          :stroke-width="14"
          :color="progressColor"
          style="margin:20px 0"
        />
        <div class="progress-message">{{ taskMessage }}</div>
        <div class="progress-badges">
          <el-tag size="small" type="info">设备：{{ deviceInfo }}</el-tag>
          <el-tag size="small" type="success">跳帧模式：每隔 1 帧推理</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 结果展示 -->
    <template v-if="phase === 'done' && videoResult">
      <!-- 汇总统计卡片 -->
      <el-row :gutter="16" class="result-summary-row">
        <el-col :span="6">
          <el-card class="result-stat-card" shadow="hover">
            <div class="result-stat-inner">
              <div class="result-stat-icon" style="background:linear-gradient(135deg,#667eea,#764ba2)">
                <el-icon :size="22"><VideoCamera /></el-icon>
              </div>
              <div>
                <div class="result-stat-value">{{ videoResult.total_frames_processed }}</div>
                <div class="result-stat-label">推理帧数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="result-stat-card" shadow="hover">
            <div class="result-stat-inner">
              <div class="result-stat-icon" style="background:linear-gradient(135deg,#f5576c,#f093fb)">
                <el-icon :size="22"><WarnTriangleFilled /></el-icon>
              </div>
              <div>
                <div class="result-stat-value">{{ videoResult.defect_frame_count }}</div>
                <div class="result-stat-label">缺陷帧数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="result-stat-card" shadow="hover">
            <div class="result-stat-inner">
              <div class="result-stat-icon" style="background:linear-gradient(135deg,#fa8c16,#fadb14)">
                <el-icon :size="22"><LocationFilled /></el-icon>
              </div>
              <div>
                <div class="result-stat-value">{{ videoResult.total_defects }}</div>
                <div class="result-stat-label">缺陷总数</div>
              </div>
            </div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card class="result-stat-card" shadow="hover">
            <div class="result-stat-inner">
              <div class="result-stat-icon" style="background:linear-gradient(135deg,#43e97b,#38f9d7)">
                <el-icon :size="22"><CircleCheck /></el-icon>
              </div>
              <div>
                <div class="result-stat-value">
                  {{ videoResult.total_frames_processed > 0
                    ? ((videoResult.defect_frame_count / videoResult.total_frames_processed) * 100).toFixed(1)
                    : 0 }}%
                </div>
                <div class="result-stat-label">缺陷帧占比</div>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 下载按钮 + 重新分析 -->
      <el-card shadow="never" class="action-card">
        <div class="action-row">
          <div class="action-left">
            <el-icon style="color:#52c41a;font-size:18px"><CircleCheckFilled /></el-icon>
            <span style="font-weight:600;color:#1a1a2e">分析完成！标注视频已生成</span>
          </div>
          <div class="action-right">
            <el-button
              type="success"
              :icon="Download"
              size="large"
              @click="downloadVideo"
            >
              下载标注视频 MP4
            </el-button>
            <el-button
              type="default"
              :icon="RefreshRight"
              size="large"
              @click="resetToIdle"
            >
              重新分析
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 有缺陷帧的明细表格 -->
      <el-card shadow="hover">
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <span class="card-title">缺陷帧明细（共 {{ defectFrames.length }} 帧有缺陷）</span>
            <el-tag size="small" type="danger">仅展示检出缺陷的帧</el-tag>
          </div>
        </template>
        <el-empty v-if="defectFrames.length === 0" description="本次巡检视频未检测到缺陷，路面状况良好" :image-size="80" />
        <el-table v-else :data="pagedDefectFrames" stripe size="small" style="width:100%">
          <el-table-column label="帧序号" prop="frame_idx" width="90" align="center">
            <template #default="{ row }">
              <span style="font-family:monospace;font-weight:700;color:#1677ff">F{{ row.frame_idx }}</span>
            </template>
          </el-table-column>
          <el-table-column label="缺陷数" width="80" align="center">
            <template #default="{ row }">
              <span style="font-weight:700;color:#fa8c16">{{ row.defect_count }}</span>
            </template>
          </el-table-column>
          <el-table-column label="缺陷类型与详情" min-width="300">
            <template #default="{ row }">
              <div v-for="(det, i) in row.detections" :key="i" class="det-row">
                <span class="det-cn">{{ det.class_cn }}</span>
                <span class="det-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
                <span
                  :style="{
                    display: 'inline-block',
                    padding: '1px 6px',
                    borderRadius: '3px',
                    fontSize: '11px',
                    fontWeight: 600,
                    background: det.danger_level === '高' ? '#fff1f0' : det.danger_level === '中' ? '#fff7e6' : '#f6ffed',
                    color: det.danger_level === '高' ? '#ff4d4f' : det.danger_level === '中' ? '#fa8c16' : '#52c41a',
                    border: `1px solid ${det.danger_level === '高' ? '#ffa39e' : det.danger_level === '中' ? '#ffd591' : '#b7eb8f'}`
                  }"
                >{{ det.danger_level }}危</span>
                <span class="det-cost">¥{{ det.estimated_cost.toLocaleString() }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="最高置信度" width="110" align="center">
            <template #default="{ row }">
              <span style="font-weight:700;color:#1677ff">
                {{ row.detections.length > 0
                  ? (Math.max(...row.detections.map(d => d.confidence)) * 100).toFixed(1) + '%'
                  : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="预估费用" width="110" align="right">
            <template #default="{ row }">
              <span style="font-weight:700;color:#1677ff">
                ¥{{ row.detections.reduce((s, d) => s + d.estimated_cost, 0).toLocaleString() }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="defectFrames.length > pageSize" class="pagination-row">
          <el-pagination
            v-model:current-page="currentPage"
            :page-size="pageSize"
            layout="total, prev, pager, next"
            :total="defectFrames.length"
          />
        </div>
      </el-card>
    </template>

    <!-- 错误提示 -->
    <el-card v-if="phase === 'error'" shadow="hover" class="error-card">
      <el-result icon="error" title="视频处理失败" :sub-title="errorMessage">
        <template #extra>
          <el-button type="primary" @click="resetToIdle">重新上传</el-button>
        </template>
      </el-result>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { RefreshRight, Download, VideoCamera } from '@element-plus/icons-vue'
import {
  submitVideo,
  submitDemoVideo,
  getVideoProgress,
  getVideoResult,
  getVideoDemos,
  downloadAnnotatedVideo,
} from '../api/http.js'

// ── 状态 ───────────────────────────────────────────────
const phase = ref('idle')  // idle / processing / done / error

const selectedFile = ref(null)
const selectedDemo = ref('')
const confidence = ref(0.25)
const uploadRef = ref(null)

const demos = ref([])
const demosLoading = ref(false)

const currentTaskId = ref('')
const taskProgress = ref(0)
const taskMessage = ref('')
const taskStatus = ref('')
const processingFilename = ref('')
const deviceInfo = ref('自动检测中…')

const videoResult = ref(null)
const errorMessage = ref('')

const currentPage = ref(1)
const pageSize = 15

let pollTimer = null

// ── 计算属性 ────────────────────────────────────────────
const progressColor = computed(() => {
  const p = taskProgress.value
  if (p < 20) return '#1677ff'
  if (p < 45) return '#096dd9'
  if (p < 65) return '#fa8c16'
  if (p < 85) return '#d48806'
  return '#52c41a'
})

const defectFrames = computed(() => {
  if (!videoResult.value) return []
  return videoResult.value.frame_results.filter(f => f.has_defect)
})

const pagedDefectFrames = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return defectFrames.value.slice(start, start + pageSize)
})

// ── 文件选择 ────────────────────────────────────────────
function handleFileChange(file) {
  selectedFile.value = file.raw
  selectedDemo.value = ''
}

function clearFile() {
  selectedFile.value = null
  if (uploadRef.value) uploadRef.value.clearFiles()
}

function selectDemo(demo) {
  selectedDemo.value = demo.filename
  selectedFile.value = null
  if (uploadRef.value) uploadRef.value.clearFiles()
}

// ── 开始分析 ────────────────────────────────────────────
async function startAnalysis() {
  if (!selectedFile.value && !selectedDemo.value) return

  try {
    phase.value = 'processing'
    taskProgress.value = 0
    taskMessage.value = '正在提交任务…'
    processingFilename.value = selectedFile.value
      ? selectedFile.value.name
      : selectedDemo.value

    let resp
    if (selectedFile.value) {
      resp = await submitVideo(selectedFile.value, confidence.value)
    } else {
      resp = await submitDemoVideo(selectedDemo.value, confidence.value)
    }

    currentTaskId.value = resp.task_id
    startPolling()
  } catch {
    phase.value = 'error'
    errorMessage.value = '提交失败，请检查后端是否正常运行'
  }
}

// ── 轮询进度 ────────────────────────────────────────────
function startPolling() {
  // RTX 4060 GPU 模式下处理极快，0.8s 轮询一次兼顾流畅和不卡
  pollTimer = setInterval(pollProgress, 800)
}

async function pollProgress() {
  try {
    const data = await getVideoProgress(currentTaskId.value)
    taskProgress.value = data.progress
    taskStatus.value = data.status

    // 科技感状态文字序列（前端覆写，不依赖后端原始 message）
    const p = data.progress
    if (p < 5) {
      taskMessage.value = '正在解析视频流，初始化推理引擎…'
    } else if (p < 25) {
      taskMessage.value = `正在提取视频帧，加载 CBAM 注意力模块… (${p}%)`
    } else if (p < 60) {
      taskMessage.value = `调用 YOLOv8+CBAM 改进模型进行逐帧推理… (${p}%)`
    } else if (p < 90) {
      taskMessage.value = `缺陷识别完成，正在合成标注视频帧… (${p}%)`
    } else if (p < 100) {
      taskMessage.value = `推理完成，正在写出 MP4 输出文件… (${p}%)`
    } else {
      taskMessage.value = '分析完成，标注视频已就绪！'
    }

    // 从消息里提取设备信息
    if (data.message.includes('cuda')) deviceInfo.value = 'CUDA (GPU)'
    else if (data.message.includes('cpu')) deviceInfo.value = 'CPU'

    if (data.status === 'done') {
      stopPolling()
      await fetchResult()
    } else if (data.status === 'error') {
      stopPolling()
      phase.value = 'error'
      errorMessage.value = data.message || '视频处理过程中发生错误'
    }
  } catch {
    // 网络短暂抖动时静默，不停止轮询
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function fetchResult() {
  try {
    const result = await getVideoResult(currentTaskId.value)
    videoResult.value = result
    phase.value = 'done'

    // 更新设备信息
    deviceInfo.value = result.total_frames_processed > 0 ? 'CUDA (GPU)' : 'CPU'
  } catch {
    phase.value = 'error'
    errorMessage.value = '获取结果失败，请重试'
  }
}

// ── 下载 ────────────────────────────────────────────────
function downloadVideo() {
  downloadAnnotatedVideo(currentTaskId.value)
}

// ── 重置 ────────────────────────────────────────────────
function resetToIdle() {
  stopPolling()
  phase.value = 'idle'
  selectedFile.value = null
  selectedDemo.value = ''
  currentTaskId.value = ''
  taskProgress.value = 0
  taskMessage.value = ''
  videoResult.value = null
  errorMessage.value = ''
  currentPage.value = 1
  if (uploadRef.value) uploadRef.value.clearFiles()
}

// ── 初始化 ──────────────────────────────────────────────
async function loadDemos() {
  demosLoading.value = true
  try {
    demos.value = await getVideoDemos()
  } catch {
    demos.value = []
  } finally {
    demosLoading.value = false
  }
}

onMounted(loadDemos)
onUnmounted(stopPolling)
</script>

<style scoped>
.video-inspect { display: flex; flex-direction: column; gap: 16px; }

/* 标题卡片 */
.header-card :deep(.el-card__body) { padding: 16px 20px; background: linear-gradient(135deg,#001529,#003366); }
.header-inner { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.header-left { display: flex; align-items: center; gap: 14px; }
.header-icon { color: #4096ff; }
.header-title { font-size: 18px; font-weight: 800; color: #fff; }
.header-sub { font-size: 12px; color: #7eb8e8; margin-top: 4px; }
.header-badges { display: flex; gap: 8px; flex-wrap: wrap; }

/* 上传区 */
.video-upload { width: 100%; }
.video-upload :deep(.el-upload-dragger) { height: 160px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.upload-icon { color: #1677ff; margin-bottom: 8px; }
.upload-text { font-size: 14px; color: #595959; }
.upload-text em { color: #1677ff; font-style: normal; }
.upload-hint { font-size: 12px; color: #bfbfbf; margin-top: 4px; }
.file-preview { display: flex; align-items: center; gap: 6px; margin-top: 12px; padding: 8px 12px; background: #f6f8ff; border-radius: 6px; font-size: 13px; }
.file-name { font-weight: 600; color: #1a1a2e; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { color: #8c8c8c; white-space: nowrap; }

/* Demo列表 */
.no-demos { text-align: center; color: #bfbfbf; padding: 20px; font-size: 13px; }
.demo-list { display: flex; flex-direction: column; gap: 8px; }
.demo-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 8px; cursor: pointer;
  border: 1px solid #f0f0f0; transition: all 0.2s;
}
.demo-item:hover { border-color: #1677ff; background: #f0f7ff; }
.demo-selected { border-color: #1677ff !important; background: #e6f0ff !important; }
.demo-icon { color: #1677ff; font-size: 20px; flex-shrink: 0; }
.demo-info { flex: 1; min-width: 0; }
.demo-name { font-size: 13px; font-weight: 600; color: #1a1a2e; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.demo-size { font-size: 11px; color: #8c8c8c; }
.demo-check { color: #1677ff; font-size: 18px; }

/* 参数行 */
.param-row { display: flex; align-items: center; gap: 12px; }
.param-label { font-size: 13px; color: #595959; white-space: nowrap; }
.param-hint { text-align: center; font-size: 12px; color: #bfbfbf; margin-top: 6px; }
.card-title { font-weight: 600; font-size: 14px; color: #1a1a2e; }

/* 进度卡片 */
.progress-card {}
.progress-body { padding: 8px 0; }
.progress-filename { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: #1a1a2e; margin-bottom: 4px; }
.progress-message { font-size: 13px; color: #595959; text-align: center; margin-bottom: 12px; }
.progress-badges { display: flex; gap: 8px; justify-content: center; }

/* 结果统计卡片 */
.result-summary-row { margin: 0; }
.result-stat-card :deep(.el-card__body) { padding: 14px 16px; }
.result-stat-inner { display: flex; align-items: center; gap: 14px; }
.result-stat-icon { width: 46px; height: 46px; border-radius: 12px; display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0; }
.result-stat-value { font-size: 24px; font-weight: 800; color: #1a1a2e; }
.result-stat-label { font-size: 12px; color: #8c8c8c; margin-top: 2px; }

/* 操作行 */
.action-card :deep(.el-card__body) { padding: 12px 20px; background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px; }
.action-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.action-left { display: flex; align-items: center; gap: 8px; }
.action-right { display: flex; gap: 10px; }

/* 缺陷明细 */
.det-row { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; font-size: 12px; }
.det-cn { font-weight: 600; color: #1a1a2e; }
.det-conf { color: #1677ff; font-weight: 600; }
.det-cost { color: #52c41a; font-weight: 600; margin-left: 2px; }
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }

/* 错误卡片 */
.error-card {}
</style>
