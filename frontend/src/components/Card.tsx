/* ============================================================
   基础卡片与版式组件 —— 对应 DESIGN.md components:
   feature-card / feature-card-elevated / mono-eyebrow
   ============================================================ */
import type { ReactNode } from 'react'

/** feature-card:白底 + 1px 发丝线 + 12px 圆角 + 24px 内边距 */
export function Card({
  children,
  elevated = false,
  className = '',
  padded = true,
}: {
  children: ReactNode
  elevated?: boolean // Level-1 whisper 阴影
  className?: string
  padded?: boolean
}) {
  return (
    <div
      className={`rounded-card border border-hairline bg-elevated ${elevated ? 'shadow-whisper' : ''} ${padded ? 'p-8' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

/** 区块头:mono eyebrow + 标题 + 可选说明 */
export function SectionHeader({
  eyebrow,
  title,
  desc,
  right,
}: {
  eyebrow: string
  title: string
  desc?: string
  right?: ReactNode
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2 className="mt-1 text-heading-md text-ink">{title}</h2>
        {desc && <p className="mt-1 text-body-md text-body">{desc}</p>}
      </div>
      {right}
    </div>
  )
}
