/* ============================================================
   MetricCard:指标卡
   · 默认:feature-card + eyebrow + 大数(Geist 负字距)+ 环比
   · highlight:KPI 卡(黑底反白——纯墨色系统内的强调,不引入彩色)
   ============================================================ */
import { fmtDelta } from '../data/format'

export function MetricCard({
  label,
  value,
  sub,
  delta,
  highlight = false,
  className = '',
}: {
  label: string
  value: string
  sub?: string
  delta?: number | null // 与上一周期比,0-1 比率
  highlight?: boolean
  className?: string
}) {
  const deltaColor =
    delta == null ? '' : delta >= 0 ? 'text-link' : 'text-error'
  return (
    <div
      className={`rounded-card border p-8 ${highlight ? 'border-primary bg-primary text-white' : 'border-hairline bg-elevated text-ink'} ${className}`}
    >
      <div className={`eyebrow ${highlight ? 'text-white/60' : ''}`}>{label}</div>
      <div className="mt-3 text-[40px] leading-[44px] font-semibold tracking-[-2px] tabular-nums">
        {value}
      </div>
      <div className="mt-2.5 flex items-center gap-2">
        {delta != null && (
          <span className={`font-mono text-[13px] font-medium ${highlight ? 'text-cyan-soft' : deltaColor}`}>
            {delta >= 0 ? '▲' : '▼'} {fmtDelta(delta).replace('+', '').replace('-', '')}
          </span>
        )}
        {sub && <span className={`text-body-sm ${highlight ? 'text-white/60' : 'text-mute'}`}>{sub}</span>}
      </div>
    </div>
  )
}
