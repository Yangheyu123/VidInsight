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
const SOURCE_LABEL: Record<string, string> = { zhihu_hot: '知乎热榜', hitokoto: '一言' }

/** 三维评分条:墨色填充,10 分满格 */
function ScoreBar({ label, v }: { label: string; v: number | null }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-8 text-body-sm text-mute">{label}</span>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-hairline">
        <div className="h-full rounded-full bg-primary" style={{ width: `${(v ?? 0) * 10}%` }} />
      </div>
      <span className="font-mono text-[13px] tabular-nums text-body">{v?.toFixed(1) ?? '—'}</span>
    </div>
  )
}

export function Materials() {
  const [filter, setFilter] = useState('待用')
  const [list, setList] = useState<Material[]>([])
  const job = useJob(
    'materials',
    () => fetch('/api/materials/fetch', { method: 'POST' }),
  )
  const rescoreJob = useJob(
    'materials',
    () => fetch('/api/materials/rescore', { method: 'POST' }),
  )

  const load = useCallback(() => {
    const q = filter === '全部' ? '' : `?status=${encodeURIComponent(filter)}`
    void fetch(`/api/materials${q}`)
      .then((r) => r.json())
      .then(setList)
      .catch(() => setList([]))
  }, [filter])
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
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
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
      </div>
      <p className="mt-2 text-body-md text-mute">知乎热榜 + 一言 · LLM 按 相关性 × 冲突感 × 收藏潜力 打分</p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        {FILTERS.map((f) => (
          <CategoryPill key={f} active={filter === f} onClick={() => setFilter(f)}>
            {f}
          </CategoryPill>
        ))}
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
                  <div className="text-[28px] leading-9 font-semibold tracking-[-1px] tabular-nums text-ink">
                    {m.score?.toFixed(1) ?? '—'}
                  </div>
                  <div className="flex gap-2">
                    {m.status !== '已用' && (
                      <SquareGhost onClick={() => setStatus(m.id, '已用')} className="h-7 px-2 text-[13px]">
                        采用
                      </SquareGhost>
                    )}
                    {m.status !== '丢弃' && (
                      <SquareGhost onClick={() => setStatus(m.id, '丢弃')} className="h-7 px-2 text-[13px]">
                        丢弃
                      </SquareGhost>
                    )}
                    {m.status !== '待用' && (
                      <SquareGhost onClick={() => setStatus(m.id, '待用')} className="h-7 px-2 text-[13px]">
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
    </div>
  )
}
