/* ============================================================
   中台侧边栏(ops-platform 骨架):常驻左侧 + 图标导航 + 分组
   底部:采集心跳 + 立即同步 + 演示开关 —— 全局状态常驻可见
   ============================================================ */
import type { ReactNode } from 'react'
import type { SyncStatus } from '../types'
import { fmtDate } from '../data/format'

export type Route = 'overview' | 'videos' | 'templates' | 'reports' | 'materials'

const I = {
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  fill: 'none',
}

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" {...I} aria-hidden>
      {children}
    </svg>
  )
}

const ICONS: Record<Route, ReactNode> = {
  overview: (
    <Icon>
      <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.2" />
      <rect x="9" y="1.5" width="5.5" height="5.5" rx="1.2" />
      <rect x="1.5" y="9" width="5.5" height="5.5" rx="1.2" />
      <rect x="9" y="9" width="5.5" height="5.5" rx="1.2" />
    </Icon>
  ),
  videos: (
    <Icon>
      <path d="M1.5 3.5h13M1.5 8h13M1.5 12.5h9" />
    </Icon>
  ),
  templates: (
    <Icon>
      <path d="M8 1.5 14.5 5 8 8.5 1.5 5 8 1.5Z" />
      <path d="m1.5 8.5 6.5 3.5 6.5-3.5" />
    </Icon>
  ),
  reports: (
    <Icon>
      <path d="M3 1.5h7l3 3V14.5H3V1.5Z" />
      <path d="M9.5 1.5v3.5H13M5.5 8h5M5.5 11h5" />
    </Icon>
  ),
  materials: (
    <Icon>
      <path d="M1.5 6 8 2l6.5 4v8h-13V6Z" />
      <path d="M6 14v-4h4v4" />
    </Icon>
  ),
}

const GROUPS: { label: string; items: { key: Route; label: string }[] }[] = [
  { label: '数据', items: [{ key: 'overview', label: '总览' }, { key: 'videos', label: '作品明细' }] },
  { label: '分析', items: [{ key: 'templates', label: '模板对比' }, { key: 'reports', label: '报告中心' }] },
  { label: '采集', items: [{ key: 'materials', label: '素材库' }] },
]

function StateDot({ state }: { state: SyncStatus['state'] }) {
  const color = state === 'ok' ? 'bg-link' : state === 'stale' ? 'bg-warning' : 'bg-error'
  return <span className={`inline-block size-1.5 rounded-full ${color}`} />
}

export type JobsState = {
  report?: { running: boolean; progress?: { done: number; total: number; failed: number } | null }
  materials?: { running: boolean }
  radar?: { running: boolean; progress?: { done: number; total: number; failed: number } | null }
  scripts?: { running: boolean }
}

const JOB_LABEL: Record<string, string> = {
  report: '报告生成',
  materials: '素材抓取',
  radar: '雷达采集',
  scripts: '脚本转写',
}

function JobStrip({ jobs }: { jobs: JobsState | null }) {
  const running = Object.entries(jobs ?? {}).filter(([, v]) => v?.running)
  if (!running.length) return null
  return (
    <div className="mt-2 space-y-2 border-t border-hairline pt-2.5">
      {running.map(([key, v]) => {
        const p = (v as { progress?: { done: number; total: number } | undefined })?.progress
        const pct = p && p.total > 0 ? Math.round((p.done / p.total) * 100) : null
        return (
          <div key={key}>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-body-sm text-ink">
                <span className="inline-block size-1.5 animate-pulse rounded-full bg-link" />
                {JOB_LABEL[key] ?? key}
              </span>
              <span className="font-mono text-body-sm text-mute">
                {pct != null && p ? `${p.done}/${p.total}` : '进行中'}
              </span>
            </div>
            {pct != null && (
              <div className="mt-1 h-1 overflow-hidden rounded-full bg-hairline">
                <div className="h-full rounded-full bg-primary transition-all duration-500" style={{ width: `${pct}%` }} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function Sidebar({
  route,
  onRoute,
  sync,
  onSync,
  syncing,
  demo,
  onToggleDemo,
  open,
  onClose,
  onOpenPalette,
  jobs,
}: {
  route: Route
  onRoute: (r: Route) => void
  sync: SyncStatus | null
  onSync: () => void
  syncing: boolean
  demo: boolean
  onToggleDemo: () => void
  open: boolean
  onClose: () => void
  onOpenPalette: () => void
  jobs?: JobsState | null
}) {
  const nav = (
    <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
      {GROUPS.map((g) => (
        <div key={g.label}>
          <div className="eyebrow mb-1.5 px-2.5">{g.label}</div>
          <div className="space-y-0.5">
            {g.items.map((it) => (
              <button
                key={it.key}
                onClick={() => {
                  onRoute(it.key)
                  onClose()
                }}
                className={`btn-press flex w-full items-center gap-2.5 rounded-square px-2.5 py-2 text-label-sm ${
                  route === it.key
                    ? 'bg-hairline-soft text-ink'
                    : 'text-body hover:bg-hairline-soft/60 hover:text-ink'
                }`}
              >
                {ICONS[it.key]}
                {it.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </nav>
  )

  const status = (
    <div className="border-t border-hairline p-3">
      <div className="rounded-card border border-hairline bg-canvas p-3.5">
        <JobStrip jobs={jobs ?? null} />
        <div className="flex items-center gap-2">
          {sync && <StateDot state={sync.state} />}
          <span className="font-mono text-xs text-body">
            {sync ? (sync.lastSync ? fmtDate(sync.lastSync, true) : '未连接') : '…'}
          </span>
        </div>
        <div className="mt-0.5 truncate text-body-sm text-mute">{sync?.source ?? 'douyin-mcp'}</div>
        {sync?.detail && (
          <div className="mt-0.5 truncate text-body-sm text-faint" title={sync.detail}>
            {sync.detail}
          </div>
        )}
        <button
          onClick={onSync}
          disabled={syncing}
          className="btn-press mt-3 h-8 w-full rounded-square bg-primary text-label-sm text-white hover:bg-ink disabled:opacity-50"
        >
          {syncing ? '同步中…' : '立即同步'}
        </button>
        <button
          onClick={onToggleDemo}
          className={`mt-2 h-7 w-full rounded-square border text-body-sm transition-colors ${
            demo
              ? 'border-warning-deep bg-warning-soft text-warning-deep'
              : 'border-hairline bg-elevated text-mute hover:bg-hairline-soft'
          }`}
        >
          {demo ? '演示数据 · 点击切回' : '演示数据'}
        </button>
        <button
          onClick={onOpenPalette}
          className="mt-2 flex h-7 w-full items-center justify-center gap-1.5 rounded-square border border-hairline bg-elevated text-body-sm text-mute transition-colors hover:bg-hairline-soft hover:text-ink"
        >
          命令面板
          <kbd className="rounded-[3px] border border-hairline bg-canvas px-1 font-mono text-[0.625rem]">⌘K</kbd>
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* 移动端遮罩 */}
      {open && <button aria-label="关闭菜单" className="fade-enter fixed inset-0 z-40 bg-black/10 md:hidden" onClick={onClose} />}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-hairline bg-elevated transition-transform duration-200 md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center gap-2.5 border-b border-hairline px-5">
          <span className="size-4 rounded-[3px] bg-primary" aria-hidden />
          <span className="text-label-sm text-ink">VidInsight</span>
          <span className="eyebrow ml-auto">OPS</span>
        </div>
        {nav}
        {status}
      </aside>
    </>
  )
}
