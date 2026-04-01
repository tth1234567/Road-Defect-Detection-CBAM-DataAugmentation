<template>
  <div class="defect-page">
    <el-card shadow="hover" class="hero-card">
      <div class="hero-title">纵向裂缝（Longitudinal Crack）</div>
      <div class="hero-desc">
        与道路行车方向大致平行的裂缝，多出现在车道边缘或施工接缝位置，早期易被忽视但扩展性较强。
      </div>
    </el-card>
    <el-card shadow="hover">
      <template #header><span class="card-title">典型示意图</span></template>
      <img class="defect-image" :src="longitudinalImg" alt="纵向裂缝典型示意图" />
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">常见成因</span></template>
          <ul class="list">
            <li>纵向施工接缝处理不当，形成薄弱带。</li>
            <li>路基不均匀沉降，导致纵向拉应力集中。</li>
            <li>边缘车道承载不足，长期荷载诱发疲劳开裂。</li>
            <li>温度收缩与老化叠加，面层抗拉性能下降。</li>
          </ul>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">主要危害</span></template>
          <ul class="list">
            <li>雨水渗入后导致基层松散，演化为更严重破损。</li>
            <li>裂缝延伸后影响行驶平顺性与舒适性。</li>
            <li>边缘裂缝可进一步发展成网裂或坑洼。</li>
            <li>对道路寿命影响明显，后期修复成本升高。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">如何修补</span></template>
          <ol class="list ordered">
            <li>窄裂缝采用热灌缝封闭，阻断水分渗入。</li>
            <li>中等裂缝可局部开槽后灌缝并贴缝带。</li>
            <li>裂缝密集区域建议铣刨重铺，恢复结构完整性。</li>
            <li>配合边沟排水治理，降低病害复发概率。</li>
          </ol>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">高概率发生地点</span></template>
          <ul class="list">
            <li>车道与路肩连接处、拓宽段拼接位置。</li>
            <li>旧路加铺后的纵向接缝区域。</li>
            <li>高填方路段与软土地基过渡区。</li>
            <li>长期受重载通行影响的右侧慢车道。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import longitudinalImg from '../../assets/longitudinal_crack.jpg'
</script>

<style scoped>
.defect-page { display: flex; flex-direction: column; gap: 16px; }
.hero-card { background: linear-gradient(135deg, #2f54eb, #1d39c4); color: #fff; }
.hero-title { font-size: 22px; font-weight: 700; }
.hero-desc { margin-top: 8px; line-height: 1.7; color: #dbeafe; }
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
