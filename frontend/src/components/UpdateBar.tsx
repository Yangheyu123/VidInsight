/* ============================================================
   更新提示条:检测到新版本 SW 时出现,点击即刷新完成换版
   双保险:SW activate 自动刷新(主路径) + 此手动入口(兜底)
   ============================================================ */
import { useEffect, useState } from 'react'

export function UpdateBar() {
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return
    // 已被控制的页面发现新 SW 在等待:提示用户(正常已被 skipWaiting 自动接管,此为兜底)
    navigator.serviceWorker.getRegistrations().then((regs) => {
      regs.forEach((reg) => {
        if (reg.waiting) setPending(true)
        reg.addEventListener('updatefound', () => {
          const nw = reg.installing
          nw?.addEventListener('statechange', () => {
            if (nw.state === 'installed' && navigator.serviceWorker.controller) setPending(true)
          })
        })
      })
    })
  }, [])

  if (!pending) return null
  return (
    <button
      onClick={() => location.reload()}
      className="fixed inset-x-4 bottom-20 z-50 flex h-11 items-center justify-center gap-2 rounded-full bg-primary text-label-sm text-white shadow-float"
    >
      发现新版本 · 点此更新
    </button>
  )
}
