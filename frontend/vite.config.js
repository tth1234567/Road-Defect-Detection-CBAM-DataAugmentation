import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发/预览时把 /api 代理到后端，避免「localhost 页面 + 127.0.0.1 API」跨站导致会话 Cookie 不发送
const apiProxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
})
