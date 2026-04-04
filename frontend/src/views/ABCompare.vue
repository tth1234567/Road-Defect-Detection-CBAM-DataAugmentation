<template>
  <div class="ab-compare">
    <!-- 标题 -->
    <div class="ab-header">
      <div class="ab-title">
        <span class="title-main">A/B 对比实验室</span>
        <el-tag type="danger" size="small">最强杀器</el-tag>
      </div>
      <div class="ab-subtitle">
        同一张图片，两个模型同时推理——让改进效果一目了然，眼见为实
      </div>
    </div>

    <!-- 控制栏 -->
    <el-card class="control-card" shadow="hover">
      <div class="control-row">
        <!-- 预置图片 -->
        <div class="control-group">
          <span class="control-label">预置演示图片：</span>
          <el-select
            v-model="selectedPreset"
            placeholder="选择预置图片..."
            style="width:220px"
            clearable
            @change="onPresetChange"
          >
            <el-option
              v-for="img in presetImages"
              :key="img.filename"
              :label="img.filename"
              :value="img.filename"
            />
            <template v-if="presetImages.length === 0" #empty>
              <div style="padding:12px;color:#999;text-align:center;font-size:13px">
                暂无预置图片<br>
                <span style="font-size:11px">请将图片放入 backend/ab_compare_images/</span>
              </div>
            </template>
          </el-select>
        </div>

        <div class="control-sep">或</div>

        <!-- 上传自定义 -->
        <div class="control-group">
          <span class="control-label">上传自定义图片：</span>
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/jpeg,image/png,image/webp"
            :on-change="onFileChange"
          >
            <el-button type="default" :icon="Upload">选择图片</el-button>
          </el-upload>
          <span v-if="uploadedFile" class="file-hint">{{ uploadedFile.name }}</span>
        </div>

        <!-- 置信度 -->
        <div class="control-group">
          <span class="control-label">置信度阈值：</span>
          <el-slider
            v-model="confidence"
            :min="0.05"
            :max="0.95"
            :step="0.05"
            :format-tooltip="v => `${(v*100).toFixed(0)}%`"
            style="width:140px"
          />
          <span class="conf-val">{{ (confidence * 100).toFixed(0) }}%</span>
        </div>

        <!-- 一键对比 -->
        <el-button
          type="primary"
          size="large"
          :loading="comparing"
          :disabled="!canCompare"
          @click="doCompare"
          class="compare-btn"
        >
          <span v-if="!comparing">⚡ 一键对比推理</span>
          <span v-else>推理中...</span>
        </el-button>
      </div>
    </el-card>

    <!-- 预览图（还未推理时显示） -->
    <div v-if="previewSrc && !baselineResult && !improvedResult" class="preview-area">
      <el-card shadow="never" class="preview-card">
        <div class="preview-label">待检测图片预览</div>
        <img :src="previewSrc" class="preview-img" alt="预览" />
      </el-card>
    </div>

    <!-- 双屏结果 -->
    <div v-if="baselineResult || improvedResult || comparing" class="results-row">
      <!-- 左：Baseline -->
      <el-card class="result-card baseline-card" shadow="hover">
        <template #header>
          <div class="result-header">
            <div class="model-badge baseline-badge">
              <span class="model-icon">🔵</span>
              <div>
                <div class="model-name">YOLOv8n Baseline</div>
                <div class="model-desc">原始基线模型（未改进）</div>
              </div>
            </div>
            <el-tag v-if="baselineResult" :type="baselineResult.has_defect ? 'danger' : 'success'" size="small">
              {{ baselineResult.has_defect ? `检出 ${baselineResult.defect_count} 处缺陷` : '未检出缺陷' }}
            </el-tag>
          </div>
        </template>
        <div v-if="comparing && !baselineResult" class="result-loading">
          <el-icon class="loading-spin"><Loading /></el-icon>
          <span>基线模型推理中...</span>
        </div>
        <template v-else-if="baselineResult">
          <img :src="`data:image/jpeg;base64,${baselineResult.annotated_image_b64}`" class="result-img" alt="baseline结果" />
          <div class="result-stats">
            <div class="stat-item">
              <span class="stat-label">推理耗时</span>
              <span class="stat-value">{{ baselineResult.inference_time_ms }} ms</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">检出框数</span>
              <span class="stat-value">{{ baselineResult.defect_count }}</span>
            </div>
            <div class="stat-item" v-if="baselineResult.detections.length > 0">
              <span class="stat-label">最高置信度</span>
              <span class="stat-value">
                {{ (Math.max(...baselineResult.detections.map(d => d.confidence)) * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
          <!-- 检测列表 -->
          <div v-if="baselineResult.detections.length > 0" class="detection-list">
            <div v-for="(d, i) in baselineResult.detections" :key="i" class="det-item">
              <el-tag size="small" :type="d.danger_level === '高' ? 'danger' : 'warning'">{{ d.class_cn }}</el-tag>
              <span class="det-conf">{{ (d.confidence * 100).toFixed(1) }}%</span>
            </div>
          </div>
          <div v-else class="no-detect-tip baseline-no">
            基线模型未检测到缺陷
          </div>
        </template>
      </el-card>

      <!-- 分隔箭头 -->
      <div class="vs-divider">
        <div class="vs-badge">VS</div>
        <div class="vs-arrow">→</div>
        <div v-if="compareReady" class="improvement-tip">
          <template v-if="diffCount > 0">
            <span class="improve-plus">改进模型多检出 +{{ diffCount }} 处</span>
          </template>
          <template v-else-if="diffCount < 0">
            <span class="improve-minus">改进模型少检出 {{ diffCount }} 处</span>
          </template>
          <template v-else>
            <span class="improve-same">检出数量相同</span>
          </template>
        </div>
      </div>

      <!-- 右：改进模型 -->
      <el-card class="result-card improved-card" shadow="hover">
        <template #header>
          <div class="result-header">
            <div class="model-badge improved-badge">
              <span class="model-icon">🟢</span>
              <div>
                <div class="model-name">+Aug+CBAM 论文改进模型</div>
                <div class="model-desc">YOLOv8n + 数据增强 + 注意力机制</div>
              </div>
            </div>
            <el-tag v-if="improvedResult" :type="improvedResult.has_defect ? 'danger' : 'success'" size="small">
              {{ improvedResult.has_defect ? `检出 ${improvedResult.defect_count} 处缺陷` : '未检出缺陷' }}
            </el-tag>
          </div>
        </template>
        <div v-if="comparing && !improvedResult" class="result-loading">
          <el-icon class="loading-spin"><Loading /></el-icon>
          <span>改进模型推理中...</span>
        </div>
        <template v-else-if="improvedResult">
          <img :src="`data:image/jpeg;base64,${improvedResult.annotated_image_b64}`" class="result-img" alt="改进模型结果" />
          <div class="result-stats">
            <div class="stat-item">
              <span class="stat-label">推理耗时</span>
              <span class="stat-value">{{ improvedResult.inference_time_ms }} ms</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">检出框数</span>
              <span class="stat-value highlight-blue">{{ improvedResult.defect_count }}</span>
            </div>
            <div class="stat-item" v-if="improvedResult.detections.length > 0">
              <span class="stat-label">最高置信度</span>
              <span class="stat-value highlight-blue">
                {{ (Math.max(...improvedResult.detections.map(d => d.confidence)) * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
          <div v-if="improvedResult.detections.length > 0" class="detection-list">
            <div v-for="(d, i) in improvedResult.detections" :key="i" class="det-item">
              <el-tag size="small" :type="d.danger_level === '高' ? 'danger' : 'warning'">{{ d.class_cn }}</el-tag>
              <span class="det-conf highlight-blue">{{ (d.confidence * 100).toFixed(1) }}%</span>
            </div>
          </div>
          <div v-else class="no-detect-tip improved-no">
            改进模型未检测到缺陷
          </div>
        </template>
      </el-card>
    </div>

    <!-- 空状态提示 -->
    <div v-if="!baselineResult && !improvedResult && !comparing && !previewSrc" class="empty-state">
      <div class="empty-icon">🔬</div>
      <div class="empty-title">选择或上传一张道路图片，点击「一键对比推理」</div>
      <div class="empty-desc">
        左侧展示 YOLOv8n 基线模型结果，右侧展示论文改进模型结果<br>
        推荐使用含有细小裂缝、复杂光照的图片，效果最震撼
      </div>
      <div class="empty-hint">
        💡 提示：将演示图片放入 <code>backend/ab_compare_images/</code> 目录后，在上方下拉框中可直接选择
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Loading } from '@element-plus/icons-vue'
import { getABImages, detectBaseline, detectImproved } from '../api/http.js'

const presetImages = ref([])
const selectedPreset = ref('')
const uploadedFile = ref(null)
const confidence = ref(0.25)
const comparing = ref(false)
const baselineResult = ref(null)
const improvedResult = ref(null)
const previewSrc = ref('')

const canCompare = computed(() => (selectedPreset.value || uploadedFile.value) && !comparing.value)
const compareReady = computed(() => baselineResult.value && improvedResult.value)
const diffCount = computed(() => {
  if (!compareReady.value) return 0
  return improvedResult.value.defect_count - baselineResult.value.defect_count
})

async function loadPresets() {
  try {
    const data = await getABImages()
    presetImages.value = data.images || []
  } catch {
    presetImages.value = []
  }
}

function onPresetChange(filename) {
  if (!filename) {
    previewSrc.value = ''
    uploadedFile.value = null
    return
  }
  uploadedFile.value = null
  baselineResult.value = null
  improvedResult.value = null
  previewSrc.value = ''
}

function onFileChange(file) {
  uploadedFile.value = file.raw
  selectedPreset.value = ''
  baselineResult.value = null
  improvedResult.value = null
  const reader = new FileReader()
  reader.onload = e => { previewSrc.value = e.target.result }
  reader.readAsDataURL(file.raw)
}

async function doCompare() {
  if (!canCompare.value) return
  comparing.value = true
  baselineResult.value = null
  improvedResult.value = null

  let imageFile = null
  try {
    if (uploadedFile.value) {
      imageFile = uploadedFile.value
    } else if (selectedPreset.value) {
      const res = await fetch(`/ab_compare_static/${encodeURIComponent(selectedPreset.value)}`)
      if (res.ok) {
        const blob = await res.blob()
        imageFile = new File([blob], selectedPreset.value, { type: blob.type || 'image/jpeg' })
        // 同时更新预览图
        previewSrc.value = URL.createObjectURL(blob)
      } else {
        throw new Error('无法获取预置图片，请改用上传功能')
      }
    }
  } catch (e) {
    ElMessage.error(e.message || '获取图片失败')
    comparing.value = false
    return
  }

  if (!imageFile) {
    ElMessage.error('请选择或上传图片')
    comparing.value = false
    return
  }

  try {
    const [bRes, iRes] = await Promise.allSettled([
      detectBaseline(imageFile, confidence.value),
      detectImproved(imageFile, confidence.value),
    ])
    if (bRes.status === 'fulfilled') baselineResult.value = bRes.value
    else ElMessage.warning('基线模型推理失败：' + (bRes.reason?.message || ''))
    if (iRes.status === 'fulfilled') improvedResult.value = iRes.value
    else ElMessage.warning('改进模型推理失败：' + (iRes.reason?.message || ''))
  } finally {
    comparing.value = false
  }
}

onMounted(() => {
  loadPresets()
})
</script>

<style scoped>
.ab-compare { display: flex; flex-direction: column; gap: 20px; }

/* 标题 */
.ab-header { margin-bottom: 4px; }
.ab-title { display: flex; align-items: center; gap: 10px; }
.title-main {
  font-size: 22px;
  font-weight: 800;
  background: linear-gradient(90deg, #f5222d 0%, #fa8c16 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.ab-subtitle { color: #666; font-size: 13px; margin-top: 6px; }

/* 控制栏 */
.control-card {}
.control-row {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.control-group { display: flex; align-items: center; gap: 8px; }
.control-label { font-size: 13px; font-weight: 600; color: #333; white-space: nowrap; }
.control-sep { font-size: 14px; color: #aaa; font-weight: 600; }
.conf-val { font-size: 13px; font-weight: 700; color: #1677ff; min-width: 36px; }
.compare-btn { margin-left: auto; min-width: 160px; font-size: 15px; font-weight: 700; }
.file-hint { font-size: 12px; color: #888; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 预览 */
.preview-area { display: flex; justify-content: center; }
.preview-card { max-width: 400px; text-align: center; }
.preview-label { font-size: 13px; color: #888; margin-bottom: 8px; }
.preview-img { max-width: 100%; border-radius: 8px; }

/* 双屏 */
.results-row {
  display: grid;
  grid-template-columns: 1fr 60px 1fr;
  gap: 0;
  align-items: start;
}
.result-card { min-height: 200px; }
.result-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.model-badge { display: flex; align-items: center; gap: 8px; }
.model-icon { font-size: 20px; }
.model-name { font-size: 14px; font-weight: 700; }
.model-desc { font-size: 11px; color: #888; margin-top: 2px; }
.baseline-card { border-color: #91caff !important; }
.improved-card { border-color: #95de64 !important; box-shadow: 0 4px 20px rgba(22,119,255,.15) !important; }

.result-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 180px;
  gap: 10px;
  color: #999;
}
.loading-spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.result-img { width: 100%; border-radius: 8px; margin-bottom: 12px; }
.result-stats {
  display: flex;
  gap: 16px;
  background: #f8faff;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 10px;
}
.stat-item { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.stat-label { font-size: 11px; color: #888; }
.stat-value { font-size: 16px; font-weight: 800; color: #333; }
.highlight-blue { color: #1677ff !important; }

.detection-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.det-item { display: flex; align-items: center; gap: 6px; }
.det-conf { font-size: 12px; font-weight: 700; color: #555; }

.no-detect-tip {
  text-align: center;
  padding: 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  margin-top: 4px;
}
.baseline-no { background: #fff1f0; color: #cf1322; }
.improved-no { background: #f6ffed; color: #389e0d; }

/* 分隔区 */
.vs-divider {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 60px;
  gap: 8px;
}
.vs-badge {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #003a8c);
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.vs-arrow { font-size: 22px; color: #1677ff; font-weight: 700; }
.improvement-tip { text-align: center; font-size: 11px; font-weight: 700; }
.improve-plus { color: #1677ff; background: #e6f4ff; padding: 3px 8px; border-radius: 20px; }
.improve-minus { color: #fa8c16; background: #fff7e6; padding: 3px 8px; border-radius: 20px; }
.improve-same { color: #888; background: #f5f5f5; padding: 3px 8px; border-radius: 20px; }

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  background: #fff;
  border-radius: 12px;
  border: 2px dashed #d0d7e0;
  text-align: center;
  gap: 12px;
}
.empty-icon { font-size: 52px; }
.empty-title { font-size: 16px; font-weight: 700; color: #333; }
.empty-desc { font-size: 13px; color: #888; line-height: 1.8; }
.empty-hint {
  font-size: 12px;
  color: #888;
  background: #f8faff;
  border-radius: 8px;
  padding: 10px 16px;
  border: 1px solid #dde6f0;
}
.empty-hint code { color: #1677ff; background: #e6f4ff; padding: 2px 6px; border-radius: 4px; font-size: 11px; }
</style>
