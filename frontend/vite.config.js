import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发/预览时把 /api 和静态资源代理到后端
const backendProxy = {
  '/api': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/aug_examples': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
  '/ab_compare_static': {
    target: 'http://127.0.0.1:8000',
    changeOrigin: true,
  },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: { proxy: backendProxy },
  preview: { proxy: backendProxy },
})
