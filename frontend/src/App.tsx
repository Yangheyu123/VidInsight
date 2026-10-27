/* ============================================================
   应用壳:左侧中台侧边栏 + 主区(横幅/页面/页脚)
   极简 hash 路由(5 页不值得路由库)
   ============================================================ */
import { useEffect, useMemo, useState } from 'react'
import { Sidebar, type JobsState, type Route } from './components/Sidebar'
import { CommandPalette, type CommandAction } from './components/CommandPalette'
import { Overview } from './pages/Overview'
import { Videos } from './pages/Videos'
import { Templates } from './pages/Templates'
import { Reports } from './pages/Reports'
import { Materials } from './pages/Materials'
import { Precheck } from './pages/Precheck'
import { isDemoMode } from './data/source'
import type { SyncStatus } from './types'

const VALID: Route[] = ['overview', 'videos', 'templates', 'reports', 'materials', 'precheck']

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
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [jobs, setJobs] = useState<JobsState | null>(null)

  // 全局任务心跳:每 5 秒轮询,刷新页面不丢后台任务状态(雷达/报告/素材/脚本)
  useEffect(() => {
    let alive = true
    const poll = async () => {
      try {
        const r = await fetch('/api/jobs')
        if (r.ok && alive) setJobs(await r.json())
      } catch {
        /* 离线由横幅兜底 */
      }
    }
    void poll()
    const t = setInterval(poll, 5000)
    return () => {
      alive = false
      clearInterval(t)
    }
  }, [])

  // ⌘K / Ctrl+K 命令面板
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      } else if (e.key === 'Escape') {
        setPaletteOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

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

  // ⌘K 命令集:导航 + 动作(动作类触发后跳转对应页面查看进度)
  const actions = useMemo<CommandAction[]>(
    () => [
      { id: 'go-overview', label: '前往总览', group: '导航', hint: 'G 1', run: () => go('overview') },
      { id: 'go-videos', label: '前往作品明细', group: '导航', run: () => go('videos') },
      { id: 'go-templates', label: '前往模板对比', group: '导航', run: () => go('templates') },
      { id: 'go-reports', label: '前往报告中心', group: '导航', run: () => go('reports') },
      { id: 'go-precheck', label: '前往剧本预检', group: '导航', run: () => go('precheck') },
      { id: 'go-materials', label: '前往素材库', group: '导航', run: () => go('materials') },
      { id: 'act-sync', label: '立即同步抖音数据(无头后台)', group: '数据', run: () => void runSync() },
      {
        id: 'act-report',
        label: '生成拆解报告(自有数据)',
        group: '分析',
        run: () => {
          void fetch('/api/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scope: 'own' }),
          })
          go('reports')
        },
      },
      {
        id: 'act-report-bench',
        label: '生成对标爆款拆解',
        group: '分析',
        run: () => {
          void fetch('/api/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scope: 'bench' }),
          })
          go('reports')
        },
      },
      {
        id: 'act-materials',
        label: '抓取新素材(八源严选)',
        group: '分析',
        run: () => {
          void fetch('/api/materials/fetch', { method: 'POST' })
          go('materials')
        },
      },
      {
        id: 'act-scripts',
        label: '提取爆款脚本(对标逐字稿转写)',
        group: '分析',
        run: () => {
          void fetch('/api/scripts/ingest', { method: 'POST' })
          go('materials')
        },
      },
      { id: 'act-demo', label: demo ? '切回真实数据' : '切换演示数据', group: '数据', run: toggleDemo },
    ],
    [demo], // eslint-disable-line react-hooks/exhaustive-deps
  )

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
        onOpenPalette={() => setPaletteOpen(true)}
        jobs={jobs}
      />

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} actions={actions} />

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
            {route === 'precheck' && <Precheck />}
          </div>
        </main>

        <footer className="border-t border-hairline">
          <div className="flex items-center gap-4 px-6 py-6 lg:px-10">
            <span className="text-body-sm text-mute">Phase 1 · 抖音数据中台</span>
            <span className="text-faint">·</span>
            <span className="text-body-sm text-mute">douyin-mcp → SQLite → React</span>
          </div>
          {/* 手机端底部留白,避免内容被 Tab 栏盖住 */}
          <div className="h-20 md:hidden" aria-hidden />
        </footer>
      </div>

      {/* ---- 手机端底部 Tab 栏(拇指区导航) ---- */}
      <nav
        className="fixed inset-x-0 bottom-0 z-30 flex border-t border-hairline bg-canvas md:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        aria-label="主导航"
      >
        {([
          ['overview', '总览', 'M2 4h12M2 8h12M2 12h9'],
          ['videos', '作品', 'M1.5 2.5h13v8h-13zM5 13.5h6M8 10.5v3'],
          ['precheck', '预检', 'M8 1.5a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13Zm-2.5 6.5 1.8 1.8L10.8 6.3'],
          ['reports', '报告', 'M3 1.5h7l3 3v10H3zM10 1.5v3h3'],
          ['materials', '素材', 'M8 2 14.5 5 8 8.5 1.5 5 8 2Zm-6.5 6 6.5 3.5 6.5-3.5'],
        ] as const).map(([key, label, d]) => (
          <button
            key={key}
            onClick={() => go(key)}
            className={`flex h-14 flex-1 flex-col items-center justify-center gap-1 ${
              route === key ? 'text-ink' : 'text-mute'
            }`}
          >
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d={d} />
            </svg>
            <span className={`text-[0.6875rem] ${route === key ? 'font-semibold' : ''}`}>{label}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}
