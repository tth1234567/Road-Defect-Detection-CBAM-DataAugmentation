import { createRouter, createWebHistory } from 'vue-router'
import { getAuthMe } from '../api/http.js'
import AlgoCockpit from '../views/AlgoCockpit.vue'
import ABCompare from '../views/ABCompare.vue'
import Dashboard from '../views/Dashboard.vue'
import DetectionWorkspace from '../views/DetectionWorkspace.vue'
import HistoryReports from '../views/HistoryReports.vue'
import HistoryTasks from '../views/HistoryTasks.vue'
import VideoInspect from '../views/VideoInspect.vue'
import Auth from '../views/Auth.vue'
import DefectPothole from '../views/defects/DefectPothole.vue'
import DefectLongitudinalCrack from '../views/defects/DefectLongitudinalCrack.vue'
import DefectTransverseCrack from '../views/defects/DefectTransverseCrack.vue'
import DefectAlligatorCrack from '../views/defects/DefectAlligatorCrack.vue'

const routes = [
  { path: '/auth', name: 'Auth', component: Auth, meta: { title: '登录' } },
  { path: '/', redirect: '/cockpit' },
  { path: '/cockpit', name: 'AlgoCockpit', component: AlgoCockpit, meta: { title: '算法成果驾驶舱' } },
  { path: '/ab-compare', name: 'ABCompare', component: ABCompare, meta: { title: 'A/B 对比实验室' } },
  { path: '/dashboard', name: 'Dashboard', component: Dashboard, meta: { title: '巡检仪表盘' } },
  { path: '/detection', name: 'Detection', component: DetectionWorkspace, meta: { title: '智能检测工作台' } },
  { path: '/video-inspect', name: 'VideoInspect', component: VideoInspect, meta: { title: '视频巡检' } },
  { path: '/reports', name: 'Reports', component: HistoryReports, meta: { title: '维修任务报告' } },
  { path: '/history-tasks', name: 'HistoryTasks', component: HistoryTasks, meta: { title: '历史巡检任务' } },
  { path: '/defects/pothole', name: 'DefectPothole', component: DefectPothole, meta: { title: '缺陷类型-坑洼' } },
  { path: '/defects/longitudinal-crack', name: 'DefectLongitudinalCrack', component: DefectLongitudinalCrack, meta: { title: '缺陷类型-纵向裂缝' } },
  { path: '/defects/transverse-crack', name: 'DefectTransverseCrack', component: DefectTransverseCrack, meta: { title: '缺陷类型-横向裂缝' } },
  { path: '/defects/alligator-crack', name: 'DefectAlligatorCrack', component: DefectAlligatorCrack, meta: { title: '缺陷类型-网状裂缝' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 智巡` : '智巡 SmartInspect'

  if (to.path === '/auth') {
    try {
      await getAuthMe()
      next({ path: '/cockpit' })
    } catch {
      next()
    }
    return
  }

  try {
    await getAuthMe()
    next()
  } catch {
    next({ path: '/auth', query: { redirect: to.fullPath } })
  }
})

export default router
