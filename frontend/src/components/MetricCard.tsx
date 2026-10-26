/* ============================================================
   MetricCard:指标卡
   · 默认:feature-card + eyebrow + 大数(Geist 负字距)+ 环比
   · highlight:KPI 卡(黑底反白——纯墨色系统内的强调)
   · detail:KPI 卡的三率明细槽位
   ============================================================ */
import type { ReactNode } from 'react'
import { fmtDelta } from '../data/format'

export function MetricCard({
  label,
  value,
  sub,
  delta,
  highlight = false,
  detail,
  className = '',
}: {
  label: string
  value: string
  sub?: string
  delta?: number | null // 与上一周期比,0-1 比率
  highlight?: boolean
  detail?: ReactNode // KPI 卡明细行(如 三率)
  className?: string
}) {
  const deltaColor =
    delta == null ? '' : delta >= 0 ? 'text-link' : 'text-error'
  return (
    <div
      className={`lift rounded-card border p-8 ${highlight ? 'border-primary bg-primary text-white' : 'border-hairline bg-elevated text-ink'} ${className}`}
    >
      <div className={`eyebrow ${highlight ? 'text-white/60' : ''}`}>{label}</div>
      <div className="mt-3 text-[2.5rem] leading-[44px] font-semibold tracking-[-2px] tabular-nums">
        {value}
      </div>
      {detail ? (
        <div className="mt-2.5 flex items-center gap-3 text-body-sm text-white/70">{detail}</div>
      ) : (
        <div className="mt-2.5 flex items-center gap-2">
          {delta != null && (
            <span className={`font-mono text-[0.8125rem] font-medium ${highlight ? 'text-cyan-soft' : deltaColor}`}>
              {delta >= 0 ? '▲' : '▼'} {fmtDelta(delta).replace('+', '').replace('-', '')}
            </span>
          )}
          {sub && <span className={`text-body-sm ${highlight ? 'text-white/60' : 'text-mute'}`}>{sub}</span>}
        </div>
      )}
    </div>
  )
}
