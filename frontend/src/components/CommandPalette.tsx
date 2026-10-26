/* ============================================================
   ⌘K 命令面板(Geist/Vercel 产品签名):
   Ctrl/⌘+K 唤起,↑↓ 选择,Enter 执行,Esc 关闭
   ============================================================ */
import { useEffect, useMemo, useRef, useState } from 'react'

export interface CommandAction {
  id: string
  label: string
  group: '导航' | '数据' | '分析'
  hint?: string
  run: () => void
}

export function CommandPalette({
  open,
  onClose,
  actions,
}: {
  open: boolean
  onClose: () => void
  actions: CommandAction[]
}) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return q ? actions.filter((a) => a.label.toLowerCase().includes(q) || a.group.includes(q)) : actions
  }, [actions, query])

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      requestAnimationFrame(() => inputRef.current?.focus())
    }
  }, [open])

  useEffect(() => setSelected(0), [query])

  if (!open) return null

  const run = (i: number) => {
    const a = filtered[i]
    if (!a) return
    onClose()
    a.run()
  }

  return (
    <div className="fade-enter fixed inset-0 z-[70] bg-black/10 backdrop-blur-[2px]" onClick={onClose}>
      <div
        className="mx-auto mt-[12vh] w-[min(35rem,90vw)] overflow-hidden rounded-panel border border-hairline bg-elevated shadow-float"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              setSelected((s) => Math.min(filtered.length - 1, s + 1))
            } else if (e.key === 'ArrowUp') {
              e.preventDefault()
              setSelected((s) => Math.max(0, s - 1))
            } else if (e.key === 'Enter') {
              e.preventDefault()
              run(selected)
            } else if (e.key === 'Escape') {
              onClose()
            }
          }}
          placeholder="搜索命令…(导航 / 同步 / 报告 / 素材)"
          className="h-12 w-full border-b border-hairline bg-transparent px-4 text-body-lg text-ink outline-none placeholder:text-faint"
        />
        <div className="max-h-80 overflow-y-auto py-1.5">
          {filtered.map((a, i) => (
            <button
              key={a.id}
              onMouseEnter={() => setSelected(i)}
              onClick={() => run(i)}
              className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-body-md ${
                i === selected ? 'bg-hairline-soft text-ink' : 'text-body'
              }`}
            >
              <span className="flex items-center gap-3">
                <span className="font-mono text-body-sm text-faint">{a.group}</span>
                {a.label}
              </span>
              {a.hint && <span className="font-mono text-body-sm text-mute">{a.hint}</span>}
            </button>
          ))}
          {filtered.length === 0 && (
            <div className="px-4 py-8 text-center text-mute">没有匹配的命令</div>
          )}
        </div>
        <div className="flex items-center gap-4 border-t border-hairline px-4 py-2.5">
          <span className="font-mono text-body-sm text-mute">↑↓ 选择</span>
          <span className="font-mono text-body-sm text-mute">↵ 执行</span>
          <span className="font-mono text-body-sm text-mute">esc 关闭</span>
          <span className="ml-auto font-mono text-body-sm text-faint">VidInsight</span>
        </div>
      </div>
    </div>
  )
}
