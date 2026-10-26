/* ============================================================
   按钮语言(DESIGN.md 双形状规则):
   · 营销/大动作 = 黑色胶囊 pill(100px 圆角)
   · 应用内/导航 = 6px 方角 square
   同一上下文不混用两种形状
   ============================================================ */
import type { ButtonHTMLAttributes, ReactNode } from 'react'

type BaseProps = ButtonHTMLAttributes<HTMLButtonElement>

/** button-primary-sm:应用内的黑色方角按钮(导航 CTA、工具动作) */
export function SquarePrimary({ children, className = '', ...rest }: BaseProps) {
  return (
    <button
      className={`inline-flex h-8 items-center gap-1.5 rounded-square bg-primary px-3 text-label-sm text-white transition-colors hover:bg-ink disabled:opacity-40 ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}

/** button-ghost-sm:应用内白底描边方角按钮 */
export function SquareGhost({ children, className = '', ...rest }: BaseProps) {
  return (
    <button
      className={`inline-flex h-8 items-center gap-1.5 rounded-square border border-hairline bg-elevated px-3 text-label-sm text-ink transition-colors hover:bg-hairline-soft disabled:opacity-40 ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}

/** button-category-pill:分类筛选胶囊(选中态 = 黑底白字) */
export function CategoryPill({
  active = false,
  children,
  className = '',
  ...rest
}: BaseProps & { active?: boolean }) {
  return (
    <button
      className={`inline-flex h-9 items-center rounded-[64px] px-4 text-label-sm transition-colors ${
        active
          ? 'bg-primary text-white'
          : 'border border-hairline bg-elevated text-ink hover:bg-hairline-soft'
      } ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}

/** button-primary:黑色营销胶囊(大动作,页面级唯一) */
export function PillPrimary({ children, className = '', ...rest }: BaseProps) {
  return (
    <button
      className={`inline-flex h-11 items-center rounded-full bg-primary px-4 text-body-lg text-white transition-colors hover:bg-ink disabled:cursor-not-allowed disabled:opacity-40 ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}

/** text-input:DESIGN.md 输入框 token */
export function TextInput({
  value,
  onChange,
  placeholder,
  className = '',
}: {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  className?: string
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`h-9 w-full rounded-square border border-hairline bg-elevated px-3 text-body-md text-ink outline-none transition-colors placeholder:text-faint focus:border-link ${className}`}
    />
  )
}

/** 爆款徽章:黑底白字小标签 */
export function ViralBadge({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-primary px-2 py-0.5 text-body-sm font-medium text-white ${className}`}
    >
      爆款
    </span>
  )
}

/** 模板小标签:发丝线描边 */
export function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-hairline px-2 py-0.5 text-body-sm text-body">
      {children}
    </span>
  )
}
