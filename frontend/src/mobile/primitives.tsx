/* ============================================================
   移动层原语(GitHub mobile / Primer 哲学)
   1. 列表→详情:列表行只承载 标题+一行元信息,数据进展开区
   2. 可点行 ≥44px,单列 16px 边距,每屏一个主操作
   3. 渐进披露:指标/操作默认收起
   4. 排版三级:标题600粗 / 元信息灰 / 数字mono
   桌面代码不引用本层;App 按 useIsMobile 切换。
   ============================================================ */
import { useEffect, useState, type ReactNode } from 'react'

/** <md 视口判定(与底部Tab栏断点一致) */
export function useIsMobile(): boolean {
  const [m, setM] = useState(() => window.matchMedia('(max-width: 767px)').matches)
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const on = () => setM(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return m
}

/** 移动页壳:整页不滚动——标题+内容+分页全部落在可视区(100dvh 减顶底栏) */
export function MobilePage({
  title,
  desc,
  action,
  children,
}: {
  title: string
  desc?: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="mx-auto flex min-h-[calc(100dvh-7rem)] w-full max-w-3xl flex-col px-4 pb-3 pt-5">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-heading-md text-ink">{title}</h1>
          {desc && <p className="mt-1 text-body-sm text-mute">{desc}</p>}
        </div>
        {action}
      </div>
      <div className="mt-4 flex flex-1 flex-col">{children}</div>
    </div>
  )
}

/** 列表容器:占满剩余高度,行多时仅列表内部滚动(页面本身不滚) */
export function MobileList({ children }: { children: ReactNode }) {
  return (
    <div className="divide-y divide-hairline overflow-y-auto rounded-card border border-hairline bg-elevated">
      {children}
    </div>
  )
}

/** 可展开列表行:收起=标题+元信息+chevron(44px+);展开=任意详情。
 * 列表→详情 + 渐进披露的落地件。 */
export function MobileRow({
  title,
  meta,
  badges,
  children,
  open,
  onToggle,
}: {
  title: ReactNode
  meta?: ReactNode
  badges?: ReactNode
  children?: ReactNode // 展开区(详情数据/操作)
  open?: boolean
  onToggle?: () => void
}) {
  return (
    <div>
      <button
        onClick={onToggle}
        className="flex min-h-[3.25rem] w-full items-center gap-3 px-4 py-3 text-left active:bg-hairline-soft"
      >
        <div className="min-w-0 flex-1">
          {badges && <div className="mb-1 flex flex-wrap items-center gap-1.5">{badges}</div>}
          <div className="line-clamp-2 font-medium leading-snug text-ink">{title}</div>
          {meta && <div className="mt-1 line-clamp-2 text-body-sm leading-snug text-mute">{meta}</div>}
        </div>
        {children && (
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`shrink-0 text-faint transition-transform ${open ? 'rotate-90' : ''}`}
            aria-hidden
          >
            <path d="m6 3.5 4.5 4.5L6 12.5" />
          </svg>
        )}
      </button>
      {open && children && (
        <div className="max-h-[42dvh] overflow-y-auto border-t border-hairline bg-canvas px-4 py-3.5">{children}</div>
      )}
    </div>
  )
}

/** 指标行(展开区内用):label 灰小字 + mono 数字的横排组 */
export function MobileStats({ items }: { items: { label: string; value: ReactNode; strong?: boolean }[] }) {
  return (
    <div className="grid grid-cols-3 gap-x-3 gap-y-3">
      {items.map((it) => (
        <div key={it.label}>
          <div className="text-body-sm text-mute">{it.label}</div>
          <div className={`mt-0.5 font-mono text-[0.9375rem] tabular-nums ${it.strong ? 'font-semibold text-link-deep' : 'text-ink'}`}>
            {it.value ?? '—'}
          </div>
        </div>
      ))}
    </div>
  )
}

/** 分页器:上一页/下一页,替代无限下滑(拇指区大按钮) */
export function MobilePager({
  page,
  pages,
  onChange,
}: {
  page: number
  pages: number
  onChange: (p: number) => void
}) {
  if (pages <= 1) return null
  return (
    <div className="mt-auto flex items-center gap-3 pt-3">
      <button
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
        className="h-11 flex-1 rounded-square border border-hairline bg-elevated text-label-sm text-ink disabled:opacity-40"
      >
        ← 上一页
      </button>
      <span className="font-mono text-body-sm text-mute">
        {page}/{pages}
      </span>
      <button
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
        className="h-11 flex-1 rounded-square border border-hairline bg-elevated text-label-sm text-ink disabled:opacity-40"
      >
        下一页 →
      </button>
    </div>
  )
}
