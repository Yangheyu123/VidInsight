/* ============================================================
   P3 素材库:抓取(异步)+ 三维评分条 + 状态流转(待用/已用/丢弃)
   ============================================================ */
import { useCallback, useEffect, useState } from 'react'
import { Card } from '../components/Card'
import { CategoryPill, SquareGhost, SquarePrimary } from '../components/Buttons'
import { useJob } from './Reports'

interface Material {
  id: number
  source: string
  category?: string | null
  title: string
  content: string | null
  url: string | null
  relevance: number | null
  conflict: number | null
  save_potential: number | null
  score: number | null
  suggestion: string | null
  tags: string | null
  status: string
  created_at: string
}

const FILTERS = ['全部', '待用', '已用', '丢弃']
const CATEGORIES = ['全部', '热点爆款', '传统哲学', '小众潜力', '爆款脚本', '爆款评论']
const SOURCE_LABEL: Record<string, string> = {
  zhihu_hot: '知乎热榜',
  weibo_hot: '微博热搜',
  baidu_hot: '百度热搜',
  bili_hot: 'B站热门',
  bili_philosophy: 'B站哲学区',
  hitokoto: '一言',
  v2ex: 'V2EX',
  hackernews: 'HackerNews',
  bench_video: '对标逐字稿',
  bili_comments: '对标评论区',
}

/** 三维评分条:墨色填充,10 分满格 */
function ScoreBar({ label, v }: { label: string; v: number | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-8 text-body-sm text-mute">{label}</span>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-hairline">
        <div className="h-full rounded-full bg-primary" style={{ width: `${(v ?? 0) * 10}%` }} />
      </div>
      <span className="font-mono text-[0.8125rem] tabular-nums text-body">{v?.toFixed(1) ?? '—'}</span>
    </div>
  )
}

export function Materials() {
  const [filter, setFilter] = useState('待用')
  const [category, setCategory] = useState('全部')
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [list, setList] = useState<Material[]>([])
  const job = useJob(
    'materials',
    () => fetch('/api/materials/fetch', { method: 'POST' }),
  )
  const rescoreJob = useJob(
    'materials',
    () => fetch('/api/materials/rescore', { method: 'POST' }),
  )
  const scriptsJob = useJob(
    'scripts',
    () => fetch('/api/scripts/ingest', { method: 'POST' }),
  )

  const load = useCallback(() => {
    const params = new URLSearchParams()
    if (filter !== '全部') params.set('status', filter)
    if (category !== '全部') params.set('category', category)
    params.set('page', String(page))
    void fetch(`/api/materials?${params}`)
      .then((r) => r.json())
      .then((d: { items: Material[]; pages: number; total: number }) => {
        setList(d.items ?? [])
        setPages(d.pages ?? 1)
        setTotal(d.total ?? 0)
      })
      .catch(() => setList([]))
  }, [filter, category, page])
  useEffect(load, [load])

  const setStatus = async (id: number, status: string) => {
    await fetch(`/api/materials/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    })
    load()
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
      <div className="eyebrow">Materials</div>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-heading-lg text-ink">素材库</h1>
        <SquarePrimary onClick={() => job.trigger(load)} disabled={job.running}>
          {job.running ? '抓取打分中…' : '抓取新素材'}
        </SquarePrimary>
        <button
          onClick={() => rescoreJob.trigger(load)}
          disabled={rescoreJob.running}
          className="inline-flex h-8 items-center rounded-square border border-hairline bg-elevated px-3 text-label-sm text-ink transition-colors hover:bg-hairline-soft disabled:opacity-50"
        >
          {rescoreJob.running ? '重评中…' : '按画像重评'}
        </button>
        <button
          onClick={() => scriptsJob.trigger(load)}
          disabled={scriptsJob.running}
          className="inline-flex h-8 items-center rounded-square border border-hairline bg-elevated px-3 text-label-sm text-ink transition-colors hover:bg-hairline-soft disabled:opacity-50"
        >
          {scriptsJob.running ? '转写提炼中(约5分钟)…' : '提取爆款脚本'}
        </button>
      </div>
      <p className="mt-2 text-body-md text-mute">八源抓取 · LLM 三维打分 · 仅收 7 分以上 · 爆款脚本:对标逐字稿(音频即取即删)</p>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {CATEGORIES.map((c) => (
          <CategoryPill
            key={c}
            active={category === c}
            onClick={() => {
              setCategory(c)
              setPage(1)
            }}
          >
            {c}
          </CategoryPill>
        ))}
        <span className="mx-1 hidden h-5 w-px bg-hairline sm:block" />
        {FILTERS.map((f) => (
          <CategoryPill
            key={f}
            active={filter === f}
            onClick={() => {
              setFilter(f)
              setPage(1)
            }}
          >
            {f}
          </CategoryPill>
        ))}
        <span className="ml-auto font-mono text-[0.8125rem] text-mute">{total} 条</span>
      </div>

      <Card className="mt-4" padded={false}>
        <div className="divide-y divide-hairline">
          {list.map((m) => (
            <div key={m.id} className="px-8 py-5">
              <div className="flex flex-wrap items-start gap-x-6 gap-y-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full border border-hairline px-2 py-0.5 text-body-sm text-body">
                      {SOURCE_LABEL[m.source] ?? m.source}
                    </span>
                    {m.category && (
                      <span className="rounded-full bg-hairline-soft px-2 py-0.5 text-body-sm text-body">
                        {m.category}
                      </span>
                    )}
                    <span className="text-body-sm text-mute">{m.status}</span>
                  </div>
                  <a
                    href={m.url ?? '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 block text-label-sm text-ink hover:text-link"
                  >
                    {m.title}
                  </a>
                  {m.suggestion && <p className="mt-1.5 text-body-md text-mute">{m.suggestion}</p>}
                  <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
                    <ScoreBar label="相关" v={m.relevance} />
                    <ScoreBar label="冲突" v={m.conflict} />
                    <ScoreBar label="收藏" v={m.save_potential} />
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <div className="text-[1.75rem] leading-9 font-semibold tracking-[-1px] tabular-nums text-ink">
                    {m.score?.toFixed(1) ?? '—'}
                  </div>
                  <div className="flex gap-2">
                    {m.status !== '已用' && (
                      <SquareGhost onClick={() => setStatus(m.id, '已用')} className="h-7 px-2 text-[0.8125rem]">
                        采用
                      </SquareGhost>
                    )}
                    {m.status !== '丢弃' && (
                      <SquareGhost onClick={() => setStatus(m.id, '丢弃')} className="h-7 px-2 text-[0.8125rem]">
                        丢弃
                      </SquareGhost>
                    )}
                    {m.status !== '待用' && (
                      <SquareGhost onClick={() => setStatus(m.id, '待用')} className="h-7 px-2 text-[0.8125rem]">
                        恢复
                      </SquareGhost>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          {list.length === 0 && (
            <div className="px-8 py-12 text-center text-mute">
              该状态暂无素材 · 点右上角「抓取新素材」
            </div>
          )}
        </div>
      </Card>

      {/* 分页器 */}
      {pages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="btn-press inline-flex h-8 items-center rounded-square border border-hairline bg-elevated px-3 text-label-sm text-ink disabled:opacity-40"
          >
            ← 上一页
          </button>
          <span className="font-mono text-[0.8125rem] text-body">
            {page} / {pages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(pages, p + 1))}
            disabled={page >= pages}
            className="btn-press inline-flex h-8 items-center rounded-square border border-hairline bg-elevated px-3 text-label-sm text-ink disabled:opacity-40"
          >
            下一页 →
          </button>
        </div>
      )}
    </div>
  )
}
