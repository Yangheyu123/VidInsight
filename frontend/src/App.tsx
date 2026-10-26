/* ============================================================
   应用壳:左侧中台侧边栏 + 主区(横幅/页面/页脚)
   极简 hash 路由(5 页不值得路由库)
   ============================================================ */
import { useEffect, useState } from 'react'
import { Sidebar, type Route } from './components/Sidebar'
import { Overview } from './pages/Overview'
import { Videos } from './pages/Videos'
import { Templates } from './pages/Templates'
import { Reports } from './pages/Reports'
import { Materials } from './pages/Materials'
import { isDemoMode } from './data/source'
import type { SyncStatus } from './types'

const VALID: Route[] = ['overview', 'videos', 'templates', 'reports', 'materials']

function routeFromHash(): Route {
  const h = window.location.hash.replace('#/', '') as Route
  return VALID.includes(h) ? h : 'overview'
}

export default function App() {
  const [route, setRoute] = useState<Route>(routeFromHash)
  const [sync, setSync] = useState<SyncStatus | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [demo] = useState(isDemoMode())
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  // 数据源状态:真实模式探测后端;演示模式直接标
  useEffect(() => {
    if (demo) {
      setSync({ source: 'douyin-mcp(演示)', state: 'ok', lastSync: new Date().toISOString(), detail: '演示数据(非真实)· 侧栏可切回' })
      return
    }
    void (async () => {
      try {
        const r = await fetch('/api/sync-status')
        if (!r.ok) throw new Error()
        setSync(await r.json())
      } catch {
        setSync({ source: 'backend', state: 'error', lastSync: null, detail: '后端未连接 · 127.0.0.1:8787' })
      }
    })()
  }, [demo])

  const go = (r: Route) => {
    window.location.hash = `/${r}`
    setRoute(r)
    window.scrollTo({ top: 0 })
  }

  const toggleDemo = () => {
    localStorage.setItem('ops.demo', demo ? '0' : '1')
    window.location.reload()
  }

  // 同步动作:后端在线 → 驱动真实采集(无头后台,约2-5分钟)后刷新
  const runSync = async () => {
    setSyncing(true)
    let online = false
    try {
      const r = await fetch('/api/sync', { method: 'POST' })
      online = r.ok
    } catch {
      online = false
    }
    if (online) {
      try {
        for (;;) {
          await new Promise((res) => setTimeout(res, 4000))
          const s = await fetch('/api/sync-status').then((x) => x.json())
          setSync(s)
          if (!s.running) break
        }
        window.location.reload()
        return
      } catch {
        /* 轮询中断按演示态收尾 */
      }
    }
    setTimeout(() => {
      setSync({ source: 'douyin-mcp', state: 'ok', lastSync: new Date().toISOString(), detail: '演示模式 · 后端未启动' })
      setSyncing(false)
    }, 900)
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar
        route={route}
        onRoute={go}
        sync={sync}
        onSync={runSync}
        syncing={syncing}
        demo={demo}
        onToggleDemo={toggleDemo}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
      />

      <div className="min-w-0 flex-1">
        {/* 移动端顶栏 */}
        <div className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-hairline bg-canvas/85 px-4 backdrop-blur-md md:hidden">
          <button
            onClick={() => setMenuOpen(true)}
            className="flex size-8 items-center justify-center rounded-square border border-hairline bg-elevated text-ink"
            aria-label="菜单"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
              <path d="M2 4h12M2 8h12M2 12h12" />
            </svg>
          </button>
          <span className="size-3.5 rounded-[2px] bg-primary" aria-hidden />
          <span className="text-label-sm text-ink">VidInsight</span>
        </div>

        {/* 离线横幅:后端未连接时明确告知,不静默降级 */}
        {!demo && sync?.source === 'backend' && sync.state === 'error' && (
          <div className="border-b border-hairline bg-elevated">
            <div className="flex flex-wrap items-center gap-3 px-6 py-3 lg:px-10">
              <span className="inline-block size-1.5 rounded-full bg-error" />
              <span className="text-body-md text-ink">后端未连接</span>
              <code className="rounded-square border border-hairline bg-canvas px-2 py-0.5 font-mono text-xs text-body">
                .venv\Scripts\python -m uvicorn backend.api:app --port 8787
              </code>
            </div>
          </div>
        )}
        {/* 演示横幅:开启演示时全站可见的醒目标识 */}
        {demo && (
          <div className="border-b border-hairline bg-warning-soft">
            <div className="flex items-center gap-2 px-6 py-2.5 lg:px-10">
              <span className="inline-block size-1.5 rounded-full bg-warning-deep" />
              <span className="text-body-md text-warning-deep">演示数据 · 数字均为虚构</span>
            </div>
          </div>
        )}

        <main className="flex-1">
          <div key={route} className="page-enter">
            {route === 'overview' && <Overview />}
            {route === 'videos' && <Videos />}
            {route === 'templates' && <Templates />}
            {route === 'reports' && <Reports />}
            {route === 'materials' && <Materials />}
          </div>
        </main>

        <footer className="border-t border-hairline">
          <div className="flex items-center gap-4 px-6 py-6 lg:px-10">
            <span className="text-body-sm text-mute">Phase 1 · 抖音数据中台</span>
            <span className="text-faint">·</span>
            <span className="text-body-sm text-mute">douyin-mcp → SQLite → React</span>
          </div>
        </footer>
      </div>
    </div>
  )
}
