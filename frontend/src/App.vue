<template>
  <router-view v-if="route.path === '/auth'" />
  <el-container v-else class="app-layout">
    <!-- 左侧导航栏 -->
    <el-aside width="220px" class="sidebar">
      <div class="logo-area">
        <div class="logo-icon">🛣</div>
        <div class="logo-text">
          <div class="logo-title">智巡</div>
          <div class="logo-sub">SmartInspect</div>
        </div>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="side-menu"
      >
        <!-- ── 核心展示区 ──────────────────────────── -->
        <div class="menu-section-label">核心展示</div>
        <el-menu-item index="/cockpit">
          <el-icon><DataAnalysis /></el-icon>
          <span>算法成果驾驶舱</span>
        </el-menu-item>
        <el-menu-item index="/ab-compare">
          <el-icon><Cpu /></el-icon>
          <span>A/B 对比实验室</span>
        </el-menu-item>

        <!-- ── 应用演示 ─────────────────────────────── -->
        <div class="menu-section-label" style="margin-top:8px">应用演示</div>
        <el-sub-menu index="/app-demo" popper-class="demo-submenu-popper">
          <template #title>
            <el-icon><Monitor /></el-icon>
            <span>应用演示</span>
          </template>
          <el-menu-item index="/detection">
            <el-icon><Search /></el-icon>
            <span>智能检测工作台</span>
          </el-menu-item>
          <el-menu-item index="/video-inspect">
            <el-icon><VideoPlay /></el-icon>
            <span>视频巡检</span>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><Document /></el-icon>
            <span>维修任务报告</span>
          </el-menu-item>
          <el-menu-item index="/history-tasks">
            <el-icon><Timer /></el-icon>
            <span>历史巡检任务</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>

      <div class="sidebar-footer">
        <div class="status-dot" :class="backendOnline ? 'online' : 'offline'"></div>
        <span>{{ backendOnline ? '后端已连接' : '后端未启动' }}</span>
      </div>
    </el-aside>

    <!-- 右侧内容区 -->
    <el-container class="main-container">
      <!-- 顶部 Header -->
      <el-header class="app-header">
        <div class="header-title">
          <span class="header-title-text">道路缺陷智能巡检系统</span>
          <el-tag type="success" size="small" style="margin-left:12px">EI 会议论文成果</el-tag>
        </div>
        <div class="header-right">
          <template v-if="currentUser">
            <el-tag size="small" :type="currentUser.role === 'admin' ? 'danger' : 'primary'" style="margin-right:8px">
              {{ currentUser.username }} · {{ currentUser.role === 'admin' ? '管理员' : '巡检员' }}
            </el-tag>
            <el-button size="small" @click="onLogout">退出登录</el-button>
          </template>
          <span class="header-info" style="margin-left:12px">河北工业大学 · 人工智能赛道</span>
        </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { checkHealth, getAuthMe, logout } from './api/http.js'

const route = useRoute()
const router = useRouter()
const backendOnline = ref(false)
const currentUser = ref(null)

async function refreshUser() {
  if (route.path === '/auth') {
    currentUser.value = null
    return
  }
  try {
    currentUser.value = await getAuthMe()
  } catch {
    currentUser.value = null
  }
}

async function onLogout() {
  try {
    await logout()
  } catch { /* ignore */ }
  currentUser.value = null
  router.push('/auth')
}

onMounted(async () => {
  try {
    await checkHealth()
    backendOnline.value = true
  } catch {
    backendOnline.value = false
  }
  await refreshUser()
})

watch(() => route.path, () => {
  refreshUser()
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  background: #e8eef6;
  color: #1a1a2e;
}

.app-layout { height: 100vh; overflow: hidden; }

.sidebar {
  background: #001529;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.logo-area {
  display: flex;
  align-items: center;
  padding: 20px 16px;
  border-bottom: 1px solid #002140;
  gap: 10px;
}
.logo-icon { font-size: 28px; }
.logo-title { color: #fff; font-size: 18px; font-weight: 700; letter-spacing: 2px; }
.logo-sub { color: #5b8db8; font-size: 11px; letter-spacing: 1px; }

.side-menu { border-right: none; flex: 1; }
.side-menu.el-menu {
  background-color: transparent !important;
  color: #a6adb4 !important;
}
.side-menu .el-menu-item,
.side-menu .el-sub-menu__title {
  color: #a6adb4 !important;
}
.side-menu .el-menu-item.is-active { background-color: #1677ff !important; color: #ffffff !important; }
.side-menu .el-menu-item:hover,
.side-menu .el-sub-menu__title:hover { background-color: rgba(22,119,255,.15) !important; }
.side-menu .el-sub-menu.is-active > .el-sub-menu__title { color: #ffffff !important; }
.side-menu .el-menu--inline {
  background: #0a2240 !important;
}
.side-menu .el-menu--inline .el-menu-item {
  color: #c6d8f3 !important;
}
.side-menu .el-menu--inline .el-menu-item:hover {
  background: #143762 !important;
}
.side-menu .el-menu--inline .el-menu-item.is-active {
  background: #1d4f8c !important;
  color: #ffffff !important;
}

.sidebar-footer {
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6e7b8a;
  font-size: 12px;
  border-top: 1px solid #002140;
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; }
.status-dot.online { background: #52c41a; box-shadow: 0 0 6px #52c41a; }
.status-dot.offline { background: #ff4d4f; }

.main-container { display: flex; flex-direction: column; overflow: hidden; }

.app-header {
  background: #fff;
  border-bottom: 2px solid #1677ff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  box-shadow: 0 2px 8px rgba(22,119,255,.10);
}
.header-title {
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
}
.header-title-text {
  background: linear-gradient(90deg, #1677ff 0%, #003a8c 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.header-info { color: #8c8c8c; font-size: 13px; }

.app-main { flex: 1; overflow-y: auto; padding: 20px; background: #e8eef6; color: #1a1a2e; }

/* 菜单分组标签 */
.menu-section-label {
  padding: 10px 16px 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #3d5978;
  text-transform: uppercase;
}

/* 全局卡片视觉升级：蓝调边框 + 默认可见阴影 */
.el-card {
  border: 1px solid #dde6f0 !important;
  box-shadow: 0 2px 12px rgba(22,119,255,.08) !important;
}
.el-card.is-hover-shadow:hover,
.el-card.is-always-shadow {
  box-shadow: 0 6px 24px rgba(22,119,255,.15) !important;
}

</style>
