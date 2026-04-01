import axios from 'axios'
import { ElMessage } from 'element-plus'

/** 与页面同源时用相对路径 `/api`（走 Vite 代理），会话 Cookie 才能生效；生产可设 VITE_API_BASE */
const API_BASE =
  import.meta.env.VITE_API_BASE ||
  (import.meta.env.DEV || import.meta.env.MODE === 'preview'
    ? '/api'
    : 'http://127.0.0.1:8000/api')

const http = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  withCredentials: true,
})

function formatApiDetail(detail) {
  if (detail == null) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (e && typeof e === 'object' && 'msg' in e ? e.msg : JSON.stringify(e)))
      .join('；')
  }
  if (typeof detail === 'object') return JSON.stringify(detail)
  return String(detail)
}

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const url = error.config?.url || ''
    const onAuthPage = typeof window !== 'undefined' && window.location.pathname.startsWith('/auth')
    if (
      status === 401 &&
      !url.includes('/auth/me') &&
      !onAuthPage
    ) {
      const redir = encodeURIComponent(window.location.pathname + window.location.search)
      window.location.assign(`/auth?redirect=${redir}`)
      return Promise.reject(error)
    }
    const raw = error.response?.data?.detail
    const msg = formatApiDetail(raw) || error.message || '请求失败'
    if (!(status === 401 && url.includes('/auth/me'))) {
      ElMessage.error(`请求错误：${msg}`)
    }
    return Promise.reject(error)
  }
)

export function login(body) {
  return http.post('/auth/login', body)
}

export function register(body) {
  return http.post('/auth/register', body)
}

export function logout() {
  return http.post('/auth/logout')
}

export function getAuthMe() {
  return http.get('/auth/me')
}

export function getDefectPie({ startDate = null, endDate = null } = {}) {
  const params = {}
  if (startDate) params.start_date = startDate
  if (endDate) params.end_date = endDate
  return http.get('/history/defect-pie', { params })
}

export function detectImage(imageFile, confidence = 0.25, abTest = false) {
  const formData = new FormData()
  formData.append('file', imageFile)
  formData.append('confidence', confidence)
  formData.append('ab_test', abTest)
  return http.post('/detect', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getDemoImages() {
  return http.get('/demo-images')
}

export function checkHealth() {
  return http.get('/health')
}

export function getHistoryTasks(limit = 50, offset = 0) {
  return http.get('/history', { params: { limit, offset } })
}

export function getHistoryTask(taskId) {
  return http.get(`/history/${taskId}`)
}

export function deleteHistoryTask(taskId) {
  return http.delete(`/history/${taskId}`)
}

export function getHistoryCount() {
  return http.get('/history-count')
}

export function getDashboardStats() {
  return http.get('/stats/dashboard')
}

export function submitVideo(videoFile, confidence = 0.25) {
  const formData = new FormData()
  formData.append('file', videoFile)
  formData.append('confidence', confidence)
  return http.post('/video/submit', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}

export function submitDemoVideo(filename, confidence = 0.25) {
  const formData = new FormData()
  formData.append('filename', filename)
  formData.append('confidence', confidence)
  return http.post('/video/submit-demo', formData)
}

export function getVideoProgress(taskId) {
  return http.get(`/video/progress/${taskId}`)
}

export function getVideoResult(taskId) {
  return http.get(`/video/result/${taskId}`)
}

export function getVideoDemos() {
  return http.get('/video/demos')
}

export function downloadAnnotatedVideo(taskId) {
  const base = String(API_BASE).replace(/\/$/, '')
  window.open(`${base}/video/download/${taskId}`, '_blank')
}
