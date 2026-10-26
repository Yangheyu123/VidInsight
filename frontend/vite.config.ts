import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// 抖音运营中台 · 前端
// 设计系统:DESIGN.md(Vercel Geist)—— 所有视觉 token 见 src/index.css
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true, // 允许局域网访问(手机看板)
    port: 5173,
    proxy: {
      // 统一走同源代理,免 CORS;后端 FastAPI @ 127.0.0.1:8787
      '/api': { target: 'http://127.0.0.1:8787', changeOrigin: true },
    },
  },
})
