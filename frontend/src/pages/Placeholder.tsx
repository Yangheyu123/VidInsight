/* ============================================================
   占位页:报告中心(P2)/ 素材库(P3)
   空状态同样按 Geist 语言设计,给 roadmap 明确的视觉锚点
   ============================================================ */
import { Card } from '../components/Card'

export function Placeholder({
  eyebrow,
  title,
  desc,
  phase,
  bullets,
}: {
  eyebrow: string
  title: string
  desc: string
  phase: string
  bullets: string[]
}) {
  return (
    <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
      <div className="eyebrow">{eyebrow}</div>
      <h1 className="mt-1 text-heading-lg text-ink">{title}</h1>
      <p className="mt-2 max-w-xl text-body-lg text-body">{desc}</p>

      <Card className="mt-8">
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center rounded-full bg-hairline-soft px-3 py-1 font-mono text-xs text-body">
            {phase}
          </span>
          <span className="text-body-md text-mute">按路线图开发中</span>
        </div>
        <ul className="mt-5 space-y-2.5">
          {bullets.map((b) => (
            <li key={b} className="flex items-start gap-3 text-body-md text-body">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-[2px] bg-faint" aria-hidden />
              {b}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
