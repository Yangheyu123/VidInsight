import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Geist 字体(FontSource 本地打包,离线可用;DESIGN.md 指定字族)
import '@fontsource/geist-sans/400.css'
import '@fontsource/geist-sans/500.css'
import '@fontsource/geist-sans/600.css'
import '@fontsource/geist-mono/400.css'
import '@fontsource/geist-mono/500.css'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

// PWA:注册 Service Worker(Android Chrome「安装应用」的可安装性判定必需)
if ('serviceWorker' in navigator && location.protocol === 'https:') {
  navigator.serviceWorker.register('/sw.js').catch(() => {})
}
