/* ============================================================
   图表共享皮肤:Recharts 按 Geist 灰阶重绘
   · 轴/网格:发丝线 + mute 等宽字
   · 数据主色:墨色;强调:link 蓝 / 渐变三件套起点色
   ============================================================ */
import type { ReactNode } from 'react'

export const MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace"

export const axisProps = {
  tick: { fill: '#8f8f8f', fontSize: 13, fontFamily: MONO },
  axisLine: { stroke: '#ebebeb' },
  tickLine: false as const,
}

export const gridProps = {
  stroke: '#ebebeb',
  vertical: false,
}

/** 悬浮卡:白底发丝线方角,mono 数值 */
export function ChartTooltip({
  title,
  rows,
}: {
  title: ReactNode
  rows: { label: ReactNode; value: ReactNode; color?: string }[]
}) {
  return (
    <div className="rounded-square border border-hairline bg-elevated px-3 py-2 shadow-float">
      <div className="eyebrow mb-1">{title}</div>
      {rows.map((r, i) => (
        <div key={i} className="flex items-center gap-2 text-body-md">
          {r.color && <span className="size-2 rounded-[2px]" style={{ background: r.color }} />}
          <span className="text-body">{r.label}</span>
          <span className="ml-auto pl-4 font-mono text-xs text-ink">{r.value}</span>
        </div>
      ))}
    </div>
  )
}

/** 图表配色常量(与 DESIGN.md token 对应) */
export const INK = '#171717'
export const LINK = '#0070f3'
export const GRAD = {
  develop: '#007cf0',
  preview: '#7928ca',
  ship: '#ff4d4d',
}
