<template>
  <div class="defect-page">
    <el-card shadow="hover" class="hero-card">
      <div class="hero-title">网状裂缝（Alligator Crack）</div>
      <div class="hero-desc">
        由多条裂缝交织形成类似龟甲纹的破损形态，通常代表结构层承载能力不足，属于需要优先处置的严重病害。
      </div>
    </el-card>
    <el-card shadow="hover">
      <template #header><span class="card-title">典型示意图</span></template>
      <img class="defect-image" :src="alligatorImg" alt="网状裂缝典型示意图" />
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">常见成因</span></template>
          <ul class="list">
            <li>面层和基层长期疲劳，结构强度衰减明显。</li>
            <li>超载车辆高频通行，重复弯拉应力累积。</li>
            <li>排水不良导致基层含水率高，承载下降。</li>
            <li>早期裂缝和坑槽未及时维护，病害联动扩散。</li>
          </ul>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">主要危害</span></template>
          <ul class="list">
            <li>路面整体破坏风险高，快速发展为坑槽群。</li>
            <li>车辆通过冲击大，存在较明显安全隐患。</li>
            <li>雨水深入结构层，导致大范围次生病害。</li>
            <li>若延迟处置，维修范围和成本会成倍增加。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">如何修补</span></template>
          <ol class="list ordered">
            <li>先做结构性评估，确定破坏深度和范围。</li>
            <li>对失效层实施铣刨或挖补，必要时补强基层。</li>
            <li>重新铺筑面层并保证压实与接缝质量。</li>
            <li>同步优化排水与交通组织，降低复发风险。</li>
          </ol>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">高概率发生地点</span></template>
          <ul class="list">
            <li>货运走廊、港口周边及物流园主通道。</li>
            <li>公交专用道与长期重载通行路段。</li>
            <li>地下水位高且排水条件差的道路。</li>
            <li>老旧道路结构层已接近寿命末期区域。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import alligatorImg from '../../assets/alligator_crack.jpg'
</script>

<style scoped>
.defect-page { display: flex; flex-direction: column; gap: 16px; }
.hero-card { background: linear-gradient(135deg, #3a6fb0, #284d7a); color: #fff; }
.hero-title { font-size: 22px; font-weight: 700; }
.hero-desc { margin-top: 8px; line-height: 1.7; color: #e0edff; }
.card-title { font-weight: 600; }
.defect-image {
  width: 100%;
  max-height: 340px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #dbe5f1;
}
.list { margin-left: 18px; line-height: 1.8; color: #4b5563; }
.ordered { margin-left: 20px; }
</style>
