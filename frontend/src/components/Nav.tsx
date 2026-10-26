/* ============================================================
   顶部导航 nav-bar:画布底 + 底部发丝线 + 圆角幽灵链接
   右侧:采集心跳 chip + 应用方角按钮(6px,不与胶囊混用)
   ============================================================ */
import type { SyncStatus } from '../types'
import { fmtDate } from '../data/format'

export type Route = 'overview' | 'videos' | 'templates' | 'reports' | 'materials'

const LINKS: { key: Route; label: string }[] = [
  { key: 'overview', label: '总览' },
  { key: 'videos', label: '作品明细' },
  { key: 'templates', label: '模板对比' },
  { key: 'reports', label: '报告中心' },
  { key: 'materials', label: '素材库' },
]

/** 采集心跳点:ok=蓝 / stale=琥珀 / error=红 */
function StateDot({ state }: { state: SyncStatus['state'] }) {
  const color = state === 'ok' ? 'bg-link' : state === 'stale' ? 'bg-warning' : 'bg-error'
  return <span className={`inline-block size-1.5 rounded-full ${color}`} />
}

export function Nav({
  route,
  onRoute,
  sync,
  onSync,
  syncing,
}: {
  route: Route
  onRoute: (r: Route) => void
  sync: SyncStatus | null
  onSync: () => void
  syncing: boolean
}) {
  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-canvas/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-2 px-4 sm:px-6">
        {/* 品牌区:黑方块字标 + 名称 */}
        <button className="flex items-center gap-2.5" onClick={() => onRoute('overview')}>
          <span className="size-4 rounded-[3px] bg-primary" aria-hidden />
          <span className="text-label-sm text-ink">运营中台</span>
        </button>

        {/* 导航链接:ghost 圆角,激活态墨色 */}
        <nav className="ml-4 hidden items-center gap-0.5 md:flex">
          {LINKS.map((l) => (
            <button
              key={l.key}
              onClick={() => onRoute(l.key)}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-body-md transition-colors ${
                route === l.key ? 'bg-hairline-soft text-ink' : 'text-body hover:text-ink'
              }`}
            >
              {l.label}
            </button>
          ))}
        </nav>

        <div className="flex-1" />

        {/* 采集心跳 */}
        {sync && (
          <div className="hidden items-center gap-2 rounded-full border border-hairline bg-elevated px-3 py-1.5 lg:flex">
            <StateDot state={sync.state} />
            <span className="font-mono text-xs text-body">
              {sync.source} · {sync.lastSync ? fmtDate(sync.lastSync, true) : '—'}
            </span>
          </div>
        )}

        {/* 应用动作为方角按钮 */}
        <button
          onClick={onSync}
          disabled={syncing}
          className="inline-flex h-8 items-center rounded-square bg-primary px-3 text-label-sm text-white transition-colors hover:bg-ink disabled:opacity-50"
        >
          {syncing ? '同步中…' : '立即同步'}
        </button>
      </div>
    </header>
  )
}
