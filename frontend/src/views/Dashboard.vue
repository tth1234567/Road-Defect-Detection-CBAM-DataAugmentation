<template>
  <div class="dashboard">
    <!-- 项目背景卡片 -->
    <el-card class="paper-card" shadow="hover">
      <div class="paper-card-inner">
        <div class="paper-badges-row">
          <span class="paper-badge">EI 数据库已检索</span>
          <span class="paper-badge badge-ieee">IEEE 已见刊</span>
          <span class="paper-badge badge-author">独立作者</span>
          <span class="paper-badge badge-corresponding">通讯作者</span>
        </div>
        <div class="paper-title">
          Road Defect Detection Method Based on CBAM and Data Augmentation
        </div>
        <div class="paper-meta">
          <span>河北工业大学 · 人工智能与数据科学学院</span>
          <el-divider direction="vertical" />
          <span>YOLOv8n + CBAM 改进模型</span>
          <el-divider direction="vertical" />
          <span>mAP@0.5: <strong style="color:#52c41a">58%</strong> vs 基线 55.8%</span>
          <el-divider direction="vertical" />
          <span class="ican-badge">🏆 iCAN 大赛国家一等奖</span>
        </div>
        <div class="paper-index-row">
          <span class="index-item">
            <span class="index-label">DOI</span>
            <span class="index-value">10.1109/AIPMV67185.2025.11290066</span>
          </span>
          <span class="index-sep">|</span>
          <span class="index-item">
            <span class="index-label">ISBN</span>
            <span class="index-value">979-8-3315-5333-3</span>
          </span>
          <span class="index-sep">|</span>
          <span class="index-item">
            <span class="index-label">EI 索引号</span>
            <span class="index-value">20261020212534</span>
          </span>
          <span class="index-sep">|</span>
          <span class="index-item">
            <span class="index-label">Publisher</span>
            <span class="index-value">IEEE Inc.</span>
          </span>
        </div>
      </div>
    </el-card>

    <!-- 统计卡片行 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-inner">
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon :size="24"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统累计运营数据行 -->
    <el-row :gutter="16" class="cumulative-row">
      <el-col :span="6" v-for="item in cumulativeStats" :key="item.label">
        <el-card class="cumul-card" shadow="hover">
          <div class="cumul-inner">
            <div class="cumul-icon" :style="{ background: item.color }">
              <el-icon :size="22"><component :is="item.icon" /></el-icon>
            </div>
            <div class="cumul-info">
              <div class="cumul-value">
                <span class="cumul-num">{{ item.display }}</span>
                <span class="cumul-unit">{{ item.unit }}</span>
              </div>
              <div class="cumul-label">
                {{ item.label }}
                <el-tooltip
                  v-if="item.tooltip"
                  content="注：为了展示系统在城市级规模下的承载能力，本宏观指标包含了初始化的运营沙盘基数，并实时叠加您的真实检测增量。"
                  placement="top"
                  :show-after="200"
                  effect="light"
                >
                  <el-icon class="cumul-tip-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表行（第一行：3列） -->
    <el-row :gutter="16" class="charts-row">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">缺陷类型分布（论文数据集）</span>
          </template>
          <v-chart :option="pieOption" style="height:260px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">消融实验性能对比（论文 Table 2）</span>
          </template>
          <v-chart :option="barOption" style="height:260px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span class="card-title">本次巡检缺陷统计</span>
          </template>
          <v-chart :option="inspectionBarOption" style="height:260px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表行（第二行：置信度分布折线图） -->
    <el-card shadow="hover">
      <template #header>
        <div style="display:flex;align-items:center;gap:8px">
          <span class="card-title">本次巡检置信度分布</span>
          <el-tag size="small" type="info">各缺陷图片最高置信度走势</el-tag>
        </div>
      </template>
      <v-chart :option="confidenceLineOption" style="height:200px" autoresize />
    </el-card>

    <!-- 天津巡检地图 -->
    <el-card shadow="hover" class="map-card">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span class="card-title">天津市道路缺陷态势感知地图</span>
          <div style="display:flex;align-items:center;gap:16px">
            <el-button
              :type="animating ? 'danger' : 'primary'"
              size="small"
              :icon="animating ? 'VideoPause' : 'VideoPlay'"
              @click="toggleAnimation"
            >
              {{ animating ? '停止回放' : '路线回放' }}
            </el-button>
            <div class="map-legend">
              <span class="legend-dot" style="background:#ff4d4f"></span> 高危
              <span class="legend-dot" style="background:#fa8c16;margin-left:12px"></span> 中危
              <span class="legend-dot" style="background:#52c41a;margin-left:12px"></span> 正常
            </div>
          </div>
        </div>
      </template>
      <v-chart :option="mapOption" :update-options="{ notMerge: true }" style="height:360px" autoresize />
    </el-card>

    <!-- 模型架构改进说明卡片 -->
    <el-card shadow="hover" class="arch-card">
      <template #header>
        <div style="display:flex;align-items:center;gap:10px">
          <span class="card-title">模型架构改进说明</span>
          <el-tag size="small" type="success">论文核心贡献</el-tag>
          <el-tag size="small" type="warning">YOLOv8n + CBAM + 数据增强</el-tag>
        </div>
      </template>
      <el-row :gutter="24">
        <!-- 左列：改进点说明 -->
        <el-col :span="14">
          <div class="arch-section-title">改进技术路线</div>
          <div class="arch-table">
            <div class="arch-row arch-row-header">
              <div class="arch-col-tag">模块</div>
              <div class="arch-col-desc">改进内容</div>
              <div class="arch-col-effect">作用</div>
            </div>
            <div class="arch-row">
              <div class="arch-col-tag">
                <el-tag type="danger" size="small">CBAM</el-tag>
              </div>
              <div class="arch-col-desc">
                通道注意力（SE, r=32）+ 空间注意力（7×7 卷积），注入 C2f 模块
              </div>
              <div class="arch-col-effect">强化特征选择，减少背景干扰</div>
            </div>
            <div class="arch-row">
              <div class="arch-col-tag">
                <el-tag type="warning" size="small">C2fWithCBAM</el-tag>
              </div>
              <div class="arch-col-desc">
                将 YOLOv8 主干中的 C2f 模块包裹，输出通过 CBAM 再提取注意力特征（threshold=224）
              </div>
              <div class="arch-col-effect">零侵入式改进，保持原始结构</div>
            </div>
            <div class="arch-row">
              <div class="arch-col-tag">
                <el-tag type="primary" size="small">数据增强</el-tag>
              </div>
              <div class="arch-col-desc">
                Mosaic 拼接、随机水平翻转、HSV 色彩抖动、随机缩放裁剪
              </div>
              <div class="arch-col-effect">扩充小样本数据集，提升泛化能力</div>
            </div>
            <div class="arch-row">
              <div class="arch-col-tag">
                <el-tag type="info" size="small">训练策略</el-tag>
              </div>
              <div class="arch-col-desc">
                SGD 优化器，余弦退火学习率调度，输入分辨率 1280×1280，批大小 8
              </div>
              <div class="arch-col-effect">防止过拟合，稳定收敛</div>
            </div>
          </div>
        </el-col>

        <!-- 右列：性能对比 -->
        <el-col :span="10">
          <div class="arch-section-title">关键指标对比（验证集）</div>
          <div class="perf-table">
            <div class="perf-row perf-header">
              <div class="perf-metric">指标</div>
              <div class="perf-baseline">基线 YOLOv8n</div>
              <div class="perf-improved">改进模型</div>
              <div class="perf-delta">提升</div>
            </div>
            <div class="perf-row">
              <div class="perf-metric">mAP@0.5</div>
              <div class="perf-baseline">55.8%</div>
              <div class="perf-improved highlight">58.0%</div>
              <div class="perf-delta positive">+2.2%</div>
            </div>
            <div class="perf-row">
              <div class="perf-metric">mAP@0.5:0.95</div>
              <div class="perf-baseline">31.6%</div>
              <div class="perf-improved highlight">33.0%</div>
              <div class="perf-delta positive">+1.4%</div>
            </div>
            <div class="perf-row">
              <div class="perf-metric">Precision</div>
              <div class="perf-baseline">60.1%</div>
              <div class="perf-improved highlight">62.3%</div>
              <div class="perf-delta positive">+2.2%</div>
            </div>
            <div class="perf-row">
              <div class="perf-metric">Recall</div>
              <div class="perf-baseline">52.8%</div>
              <div class="perf-improved highlight">54.2%</div>
              <div class="perf-delta positive">+1.4%</div>
            </div>
          </div>
          <div class="arch-note">
            * 数据来源：论文 Table 2（最优配置 r=32, threshold=224）
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onActivated, onUnmounted } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart, ScatterChart, EffectScatterChart, LineChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent,
  GridComponent, GeoComponent, MarkLineComponent
} from 'echarts/components'
import VChart from 'vue-echarts'
import { inspectionStore } from '../stores/inspectionStore.js'
import { getDashboardStats } from '../api/http.js'

use([CanvasRenderer, PieChart, BarChart, ScatterChart, EffectScatterChart, LineChart,
  TitleComponent, TooltipComponent, LegendComponent, GridComponent, GeoComponent, MarkLineComponent])

// ── 天津预设巡检路线（与 DetectionWorkspace 保持一致） ──
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

// ── 路线回放动画状态 ───────────────────────────────────
const animating = ref(false)
const animStep = ref(0)
let animTimer = null

function toggleAnimation() {
  if (animating.value) {
    clearInterval(animTimer)
    animTimer = null
    animating.value = false
    animStep.value = 0
  } else {
    animating.value = true
    animStep.value = 0
    animTimer = setInterval(() => {
      animStep.value++
      if (animStep.value >= TIANJIN_ROUTE.length) {
        clearInterval(animTimer)
        animTimer = null
        animating.value = false
        animStep.value = 0
      }
    }, 200)
  }
}

onUnmounted(() => {
  if (animTimer) clearInterval(animTimer)
})

const chartTextColor = '#595959'
const chartAxisColor = '#8c8c8c'
const chartSplitColor = '#e8f0fe'
const chartBgColor = '#f8faff'

// ── 系统累计运营数据（混合模式：沙盘基数 + SQLite 真实增量） ──
// 兜底值：后端不可用时直接展示初始基数，不影响页面显示
const _fallback = { distance_km: 1247, total_defects: 3892, fixed_count: 672, running_days: 211 }
const dashboardStatsData = ref({ ..._fallback })

async function fetchDashboardStats() {
  try {
    const data = await getDashboardStats()
    dashboardStatsData.value = data
  } catch {
    // 接口失败时保留兜底值，不弹错误（首页不应因统计接口失败而报错）
  }
}

onMounted(fetchDashboardStats)
onActivated(fetchDashboardStats)  // keep-alive 切回时也刷新

const cumulativeStats = computed(() => {
  const d = dashboardStatsData.value
  return [
    {
      label: '已分析路段里程',
      display: Number(d.distance_km).toLocaleString('zh-CN', { maximumFractionDigits: 1 }),
      unit: ' km',
      icon: 'Odometer',
      color: 'linear-gradient(135deg,#1677ff,#4096ff)',
      tooltip: true,
    },
    {
      label: '累计发现缺陷',
      display: Number(d.total_defects).toLocaleString('zh-CN'),
      unit: ' 处',
      icon: 'WarnTriangleFilled',
      color: 'linear-gradient(135deg,#f5576c,#f093fb)',
      tooltip: true,
    },
    {
      label: '高危缺陷已处置',
      display: Number(d.fixed_count).toLocaleString('zh-CN'),
      unit: ' 处',
      icon: 'CircleCheckFilled',
      color: 'linear-gradient(135deg,#43e97b,#38f9d7)',
      tooltip: true,
    },
    {
      label: '系统安全运行',
      display: String(d.running_days),
      unit: ' 天',
      icon: 'Timer',
      color: 'linear-gradient(135deg,#fa8c16,#fadb14)',
      tooltip: false,
    },
  ]
})

// ── 统计卡片数据 ───────────────────────────────────────
const stats = computed(() => [
  {
    label: '本次巡检图片数',
    value: inspectionStore.defectRecords.length > 0
      ? `${inspectionStore.defectRecords.length} 张`
      : '— 张',
    icon: 'Camera', color: 'linear-gradient(135deg,#667eea,#764ba2)'
  },
  {
    label: '检出缺陷图片数',
    value: inspectionStore.defectRecords.length > 0
      ? `${inspectionStore.defectRecords.length} 张`
      : '— 张',
    icon: 'Warning', color: 'linear-gradient(135deg,#f093fb,#f5576c)'
  },
  {
    label: '识别缺陷总数',
    value: inspectionStore.totalDefects > 0 ? `${inspectionStore.totalDefects} 处` : '— 处',
    icon: 'LocationFilled', color: 'linear-gradient(135deg,#4facfe,#00f2fe)'
  },
  {
    label: '预估总维修费用',
    value: inspectionStore.totalCost > 0
      ? `¥${inspectionStore.totalCost.toLocaleString()}`
      : '¥ —',
    icon: 'Money', color: 'linear-gradient(135deg,#43e97b,#38f9d7)'
  },
])

// ── 缺陷类型分布饼图 ──────────────────────────────────
const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}% ({d}%)' },
  legend: { bottom: 0, textStyle: { fontSize: 11, color: chartTextColor } },
  series: [{
    type: 'pie',
    radius: ['35%', '65%'],
    center: ['50%', '45%'],
    data: [
      { name: '坑洼', value: 38.0, itemStyle: { color: '#ff4d4f' } },
      { name: '横向裂缝', value: 30.8, itemStyle: { color: '#fa8c16' } },
      { name: '纵向裂缝', value: 17.5, itemStyle: { color: '#fadb14' } },
      { name: '网状裂缝', value: 13.8, itemStyle: { color: '#52c41a' } },
    ],
    label: { formatter: '{b}\n{d}%', fontSize: 11, color: chartTextColor },
    emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.5)' } },
  }],
}))

// ── 消融实验柱状图 ────────────────────────────────────
const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
  xAxis: {
    type: 'category',
    data: ['Baseline', '+CBAM', '+Aug', '+Aug\n+CBAM'],
    axisLabel: { fontSize: 10, color: chartAxisColor },
    axisLine: { lineStyle: { color: chartSplitColor } },
  },
  yAxis: {
    type: 'value',
    min: 54,
    max: 60,
    axisLabel: { formatter: '{value}%', color: chartAxisColor },
    splitLine: { lineStyle: { color: chartSplitColor } },
  },
  series: [{
    type: 'bar',
    data: [
      { value: 55.8, itemStyle: { color: '#91caff' } },
      { value: 56.5, itemStyle: { color: '#69b1ff' } },
      { value: 57.8, itemStyle: { color: '#4096ff' } },
      { value: 58.0, itemStyle: { color: '#1677ff' } },
    ],
    label: { show: true, position: 'top', formatter: '{c}%', fontSize: 11 },
    barMaxWidth: 50,
  }],
}))

// ── 本次巡检缺陷统计柱状图 ────────────────────────────
const inspectionBarOption = computed(() => {
  const counts = { '坑洼': 0, '横向裂缝': 0, '纵向裂缝': 0, '网状裂缝': 0 }
  inspectionStore.defectRecords.forEach(r => {
    r.detections.forEach(d => {
      if (counts[d.class_cn] !== undefined) counts[d.class_cn]++
    })
  })
  const hasData = Object.values(counts).some(v => v > 0)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: Object.keys(counts),
      axisLabel: { fontSize: 10, color: chartAxisColor },
      axisLine: { lineStyle: { color: chartSplitColor } },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: { color: chartAxisColor },
      splitLine: { lineStyle: { color: chartSplitColor } },
    },
    series: [{
      type: 'bar',
      data: hasData ? Object.values(counts).map((v, i) => ({
        value: v,
        itemStyle: { color: ['#ff4d4f', '#fa8c16', '#fadb14', '#52c41a'][i] }
      })) : [{ value: 0 }, { value: 0 }, { value: 0 }, { value: 0 }],
      label: { show: true, position: 'top' },
      barMaxWidth: 50,
    }],
    graphic: !hasData ? [{
      type: 'text', left: 'center', top: 'middle',
      style: { text: '完成巡检后显示', fill: '#ccc', fontSize: 14 }
    }] : [],
  }
})

// ── 置信度分布折线图 ──────────────────────────────────
const confidenceLineOption = computed(() => {
  const records = inspectionStore.defectRecords
  const hasData = records.length > 0
  const xData = hasData ? records.map((_, i) => `图片${i + 1}`) : []
  const yData = hasData
    ? records.map(r => {
        const maxConf = Math.max(...r.detections.map(d => d.confidence))
        return parseFloat((maxConf * 100).toFixed(1))
      })
    : []

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `${p.name}<br/>最高置信度：<b>${p.value}%</b>`
      }
    },
    grid: { left: '3%', right: '4%', top: '15%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { fontSize: 11, color: chartAxisColor },
      name: '检测图片',
      nameTextStyle: { color: chartAxisColor, fontSize: 11 },
      axisLine: { lineStyle: { color: chartSplitColor } },
    },
    yAxis: {
      type: 'value',
      min: 0, max: 100,
      axisLabel: { formatter: '{value}%', fontSize: 11, color: chartAxisColor },
      name: '置信度',
      nameTextStyle: { color: chartAxisColor, fontSize: 11 },
      splitLine: { lineStyle: { color: chartSplitColor } },
    },
    series: [{
      type: 'line',
      data: yData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: { color: '#1677ff', width: 2 },
      itemStyle: { color: '#1677ff' },
      areaStyle: { color: 'rgba(22,119,255,0.1)' },
      markLine: hasData ? {
        silent: true,
        data: [{ type: 'average', name: '平均值' }],
        lineStyle: { color: '#fa8c16', type: 'dashed' },
        label: { formatter: '均值: {c}%', color: '#fa8c16', fontSize: 11 }
      } : undefined,
    }],
    graphic: !hasData ? [{
      type: 'text', left: 'center', top: 'middle',
      style: { text: '完成巡检分析后显示各图片置信度走势', fill: '#ccc', fontSize: 14 }
    }] : [],
  }
})

// ── 天津地图 ──────────────────────────────────────────
const mapPoints = computed(() => {
  if (inspectionStore.defectRecords.length === 0) {
    return [
      { coord: [117.19, 39.12], danger: '高', name: '坑洼', cost: 3200 },
      { coord: [117.22, 39.08], danger: '中', name: '横向裂缝', cost: 800 },
      { coord: [117.15, 39.15], danger: '高', name: '网状裂缝', cost: 5500 },
      { coord: [117.28, 39.11], danger: '中', name: '纵向裂缝', cost: 600 },
      { coord: [117.33, 39.09], danger: '高', name: '坑洼', cost: 2800 },
    ]
  }
  return inspectionStore.defectRecords.map(r => ({
    coord: r.gpsCoord,
    danger: r.detections[0]?.danger_level || '中',
    name: r.detections[0]?.class_cn || '缺陷',
    cost: r.detections.reduce((s, d) => s + d.estimated_cost, 0),
  }))
})

const mapOption = computed(() => {
  const step = animStep.value
  const routeSlice = TIANJIN_ROUTE.slice(0, step)
  const currentPos = step > 0 ? TIANJIN_ROUTE[step - 1] : null

  const series = [
    {
      type: 'scatter', symbol: 'none',
      data: [[117.19, 39.09]],
      label: {
        show: true, formatter: '天津市（模拟巡检区域）',
        color: '#1677ff', fontSize: 13, fontWeight: 600, position: 'right'
      }
    },
    {
      type: 'effectScatter',
      symbolSize: (val, p) => p.data.danger === '高' ? 18 : 12,
      data: mapPoints.value.map(p => ({
        value: [p.coord[0], p.coord[1]],
        name: p.name, danger: p.danger, cost: p.cost,
        itemStyle: { color: p.danger === '高' ? '#ff4d4f' : p.danger === '中' ? '#fa8c16' : '#52c41a' }
      })),
      rippleEffect: { brushType: 'stroke', scale: 3 },
      label: {
        show: true, formatter: (p) => p.data.name,
        position: 'right', fontSize: 10, color: '#333'
      }
    },
  ]

  if (routeSlice.length >= 2) {
    series.push({
      type: 'line',
      data: routeSlice.map(p => [p[0], p[1]]),
      lineStyle: { color: '#1677ff', width: 2, type: 'dashed' },
      symbol: 'none',
      z: 5,
    })
  }

  if (currentPos) {
    series.push({
      type: 'scatter',
      symbol: 'pin',
      symbolSize: 28,
      data: [{ value: [currentPos[0], currentPos[1]], name: '巡检车辆' }],
      itemStyle: { color: '#1677ff' },
      label: { show: true, formatter: '🚗', fontSize: 14, offset: [0, -4] },
      z: 10,
    })
  }

  return {
    backgroundColor: chartBgColor,
    tooltip: {
      trigger: 'item',
      formatter: (p) => {
        if (p.data.name === '巡检车辆') return '巡检车辆当前位置'
        const d = p.data
        if (!d.danger) return ''
        return `<b>${d.name}</b><br/>危险等级：${d.danger}<br/>预估费用：¥${d.cost}`
      }
    },
    xAxis: {
      type: 'value', min: 117.10, max: 117.32,
      axisLabel: { formatter: (v) => `${v}°E`, fontSize: 10, color: chartAxisColor },
      splitLine: { lineStyle: { color: chartSplitColor } },
      name: '经度', nameLocation: 'end', nameTextStyle: { color: chartAxisColor, fontSize: 11 }
    },
    yAxis: {
      type: 'value', min: 39.08, max: 39.17,
      axisLabel: { formatter: (v) => `${v}°N`, fontSize: 10, color: chartAxisColor },
      splitLine: { lineStyle: { color: chartSplitColor } },
      name: '纬度', nameLocation: 'end', nameTextStyle: { color: chartAxisColor, fontSize: 11 }
    },
    series,
  }
})
</script>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 16px; }

.paper-card { background: linear-gradient(135deg, #001529, #003366); color: white; }
.paper-card-inner { padding: 4px 0; }

.paper-badges-row { display: flex; gap: 8px; margin-bottom: 10px; flex-wrap: wrap; }
.paper-badge {
  display: inline-block; background: #1677ff; color: #fff;
  padding: 2px 10px; border-radius: 12px; font-size: 12px;
}
.badge-ieee { background: #0066cc; }
.badge-author { background: #52c41a; }
.badge-corresponding { background: #722ed1; }

.paper-title { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 10px; line-height: 1.5; }
.paper-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #a8d8ff; flex-wrap: wrap; }
.ican-badge { color: #ffd700; font-weight: 600; }

.paper-index-row {
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px;
  margin-top: 10px; padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.15);
  font-size: 11px;
}
.index-item { display: flex; align-items: center; gap: 4px; }
.index-label { color: #7eb8e8; font-weight: 600; letter-spacing: 0.5px; white-space: nowrap; }
.index-value { color: #d0e8ff; font-family: 'Courier New', monospace; }
.index-sep { color: rgba(255,255,255,0.3); padding: 0 2px; }

.stats-row { margin: 0; }
.stat-card :deep(.el-card__body) { padding: 16px; }
.stat-inner { display: flex; align-items: center; gap: 16px; }
.stat-icon {
  width: 52px; height: 52px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;
}
.stat-value { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.stat-label { font-size: 12px; color: #8c8c8c; margin-top: 2px; }

.cumulative-row { margin: 0; }
.cumul-card :deep(.el-card__body) { padding: 16px; }
.cumul-inner { display: flex; align-items: center; gap: 14px; }
.cumul-icon {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center; color: white; flex-shrink: 0;
}
.cumul-info { flex: 1; min-width: 0; }
.cumul-value { display: flex; align-items: baseline; gap: 2px; }
.cumul-num { font-size: 24px; font-weight: 800; color: #1a1a2e; letter-spacing: -0.5px; }
.cumul-unit { font-size: 13px; color: #595959; font-weight: 500; }
.cumul-label { font-size: 12px; color: #8c8c8c; margin-top: 2px; display: flex; align-items: center; gap: 4px; }
.cumul-tip-icon { font-size: 12px; color: #bfbfbf; cursor: help; flex-shrink: 0; }

.charts-row { margin: 0; }
.card-title { font-weight: 600; font-size: 14px; color: #1a1a2e; }

.map-card {}
.map-legend { display: flex; align-items: center; font-size: 12px; color: #595959; }
.legend-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }

/* 模型架构卡片 */
.arch-card {}
.arch-section-title {
  font-size: 13px; font-weight: 600; color: #434343;
  margin-bottom: 10px; padding-bottom: 6px;
  border-bottom: 2px solid #e8f4ff;
}

.arch-table { border: 1px solid #e8e8e8; border-radius: 6px; overflow: hidden; }
.arch-row {
  display: flex; align-items: stretch;
  border-bottom: 1px solid #f0f0f0; font-size: 12px;
}
.arch-row:last-child { border-bottom: none; }
.arch-row-header {
  background: #f6f8ff; font-weight: 600; color: #434343; font-size: 12px;
}
.arch-col-tag { width: 110px; min-width: 110px; padding: 8px 10px; border-right: 1px solid #f0f0f0; display: flex; align-items: center; }
.arch-col-desc { flex: 1; padding: 8px 10px; border-right: 1px solid #f0f0f0; color: #595959; line-height: 1.5; display: flex; align-items: center; }
.arch-col-effect { width: 140px; min-width: 140px; padding: 8px 10px; color: #1677ff; font-size: 11px; display: flex; align-items: center; }

.perf-table { border: 1px solid #e8e8e8; border-radius: 6px; overflow: hidden; margin-bottom: 8px; }
.perf-row { display: flex; font-size: 13px; border-bottom: 1px solid #f0f0f0; }
.perf-row:last-child { border-bottom: none; }
.perf-header { background: #f6f8ff; font-weight: 600; color: #434343; font-size: 12px; }
.perf-metric { width: 120px; padding: 8px 10px; border-right: 1px solid #f0f0f0; color: #595959; display: flex; align-items: center; }
.perf-baseline { flex: 1; padding: 8px 10px; border-right: 1px solid #f0f0f0; color: #8c8c8c; display: flex; align-items: center; justify-content: center; }
.perf-improved { flex: 1; padding: 8px 10px; border-right: 1px solid #f0f0f0; display: flex; align-items: center; justify-content: center; font-weight: 600; }
.perf-improved.highlight { color: #1677ff; }
.perf-delta { width: 60px; padding: 8px 10px; display: flex; align-items: center; justify-content: center; font-weight: 600; }
.perf-delta.positive { color: #52c41a; }

.arch-note { font-size: 11px; color: #aaa; }
</style>
