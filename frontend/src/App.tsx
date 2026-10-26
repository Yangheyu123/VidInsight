/* ============================================================
   应用壳:极简 hash 路由 + Nav + 页脚
   不引入路由库(5 个页面不值得),保持依赖最小
   ============================================================ */
import { useEffect, useState } from 'react'
import { Nav, type Route } from './components/Nav'
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

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  // 数据源状态:真实模式探测后端;演示模式直接标
  useEffect(() => {
    if (demo) {
      setSync({ source: 'douyin-mcp(演示)', state: 'ok', lastSync: new Date().toISOString(), detail: '演示数据(非真实)· 页脚可切回' })
      return
    }
    void mockSourcePlaceholder()
    async function mockSourcePlaceholder() {
      try {
        const r = await fetch('/api/sync-status')
        if (!r.ok) throw new Error()
        setSync(await r.json())
      } catch {
        setSync({ source: 'backend', state: 'error', lastSync: null, detail: '后端未连接 · 127.0.0.1:8787' })
      }
    }
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

  // 同步动作:后端在线 → 驱动真实采集(douyin-mcp,约2-5分钟)后刷新;
  // 后端不在线(演示态)→ 模拟心跳
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
        window.location.reload() // 数据已更新,整页刷新取新数
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
    <div className="flex min-h-screen flex-col">
      <Nav route={route} onRoute={go} sync={sync} onSync={runSync} syncing={syncing} />

      {/* 离线横幅:后端未连接时明确告知,不静默降级 */}
      {!demo && sync?.source === 'backend' && sync.state === 'error' && (
        <div className="border-b border-hairline bg-elevated">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
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
          <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2.5 sm:px-6">
            <span className="inline-block size-1.5 rounded-full bg-warning-deep" />
            <span className="text-body-md text-warning-deep">演示数据 · 数字均为虚构</span>
          </div>
        </div>
      )}

      <main className="flex-1">
        {route === 'overview' && <Overview />}
        {route === 'videos' && <Videos />}
        {route === 'templates' && <Templates />}
        {route === 'reports' && <Reports />}
        {route === 'materials' && <Materials />}
      </main>

      <footer className="border-t border-hairline">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-8 sm:px-6">
          <span className="text-body-sm text-mute">Phase 1 · 抖音数据中台</span>
          <button
            onClick={toggleDemo}
            className={`ml-auto inline-flex h-8 items-center rounded-square border px-3 text-body-sm transition-colors ${
              demo
                ? 'border-warning-deep bg-warning-soft text-warning-deep'
                : 'border-hairline bg-elevated text-mute hover:bg-hairline-soft'
            }`}
          >
            {demo ? '演示数据 · 点击切回真实' : '演示数据'}
          </button>
        </div>
      </footer>
    </div>
  )
}
