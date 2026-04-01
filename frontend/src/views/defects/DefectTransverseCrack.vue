<template>
  <div class="defect-page">
    <el-card shadow="hover" class="hero-card">
      <div class="hero-title">横向裂缝（Transverse Crack）</div>
      <div class="hero-desc">
        与道路行车方向大致垂直的裂缝，常表现为周期性条状分布，通常与温缩、基层反射裂缝有关。
      </div>
    </el-card>
    <el-card shadow="hover">
      <template #header><span class="card-title">典型示意图</span></template>
      <img class="defect-image" :src="transverseImg" alt="横向裂缝典型示意图" />
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">常见成因</span></template>
          <ul class="list">
            <li>温度骤降引起面层收缩，超过材料抗拉极限。</li>
            <li>基层或旧面层裂缝向上反射至新铺层。</li>
            <li>沥青老化变脆，抗裂能力下降。</li>
            <li>施工温度与压实窗口控制不佳，形成弱面。</li>
          </ul>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">主要危害</span></template>
          <ul class="list">
            <li>裂缝成为雨水通道，易引发基层病害。</li>
            <li>冬季冻胀加剧裂缝扩展，病害发展快。</li>
            <li>车辆通过时产生振动冲击，舒适性下降。</li>
            <li>若不治理，可能演化为块裂与坑洼。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">如何修补</span></template>
          <ol class="list ordered">
            <li>裂缝初期采用热灌缝封闭，防止水损害。</li>
            <li>反射裂缝严重时，可加铺抗裂层后重铺面层。</li>
            <li>局部密集裂缝区域采用铣刨重铺。</li>
            <li>建立季节性复测机制，重点跟踪冬季后状态。</li>
          </ol>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">高概率发生地点</span></template>
          <ul class="list">
            <li>昼夜温差大的开放路段与桥头区域。</li>
            <li>旧路罩面改造后的反射裂缝高发区。</li>
            <li>高寒或冬季较长地区的主干道路面。</li>
            <li>养护频次低、老化程度高的次干道。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import transverseImg from '../../assets/lateral_crack.jpg'
</script>

<style scoped>
.defect-page { display: flex; flex-direction: column; gap: 16px; }
.hero-card { background: linear-gradient(135deg, #fa8c16, #d46b08); color: #fff; }
.hero-title { font-size: 22px; font-weight: 700; }
.hero-desc { margin-top: 8px; line-height: 1.7; color: #fff3d8; }
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
