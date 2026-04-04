<template>
  <div class="defect-page">
    <el-card shadow="hover" class="hero-card">
      <div class="hero-title">坑洼（Pothole）</div>
      <div class="hero-desc">
        路面局部材料脱落形成坑洞，常见于车辙区和积水点，是影响行车安全与舒适性的高频缺陷之一。
      </div>
    </el-card>
    <el-card shadow="hover">
      <template #header><span class="card-title">典型示意图</span></template>
      <img class="defect-image" :src="potholeImg" alt="坑洼典型示意图" />
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">常见成因</span></template>
          <ul class="list">
            <li>雨水沿裂缝渗入基层，反复冻融或荷载作用导致结构松散。</li>
            <li>重载车辆长期碾压，使局部面层疲劳剥落。</li>
            <li>早期裂缝未及时灌缝，病害逐步扩大为坑洞。</li>
            <li>施工压实不足或材料级配不合理，耐久性下降。</li>
          </ul>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">主要危害</span></template>
          <ul class="list">
            <li>车辆经过时冲击明显，易造成轮胎或悬挂损伤。</li>
            <li>雨天积水掩盖坑洞，突发避让风险高。</li>
            <li>坑洞边缘持续破碎，病害扩展速度快。</li>
            <li>道路通行效率下降，维护成本快速增加。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">如何修补</span></template>
          <ol class="list ordered">
            <li>切边清槽：切除松散层并形成规则坑槽。</li>
            <li>清洁与喷洒黏层油，增强新旧料黏结。</li>
            <li>分层填补热拌沥青料并压实，控制平整度。</li>
            <li>雨季前重点复检，防止二次破损。</li>
          </ol>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span class="card-title">高概率发生地点</span></template>
          <ul class="list">
            <li>交叉口刹停区、公交站进出站区域。</li>
            <li>长期排水不畅的低洼路段与井盖周边。</li>
            <li>货运通道与重载车高频通行道路。</li>
            <li>曾有裂缝修补记录但养护不足的旧路段。</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import potholeImg from '../../assets/pothole.jpg'
</script>

<style scoped>
.defect-page { display: flex; flex-direction: column; gap: 16px; }
.hero-card { background: linear-gradient(135deg, #1677ff, #003a8c); color: #fff; }
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
