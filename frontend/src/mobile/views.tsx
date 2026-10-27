/* ============================================================
   移动视图层:列表→详情 + 渐进披露(GitHub mobile 哲学)
   桌面版独立存在,互不引用。
   ============================================================ */
import { useEffect, useState } from 'react'
import { fmtDate, fmtNum, fmtPct } from '../data/format'
import { isViral } from '../data/stats'
import type { Video } from '../types'
import { useJob } from '../pages/Reports'
import { MobileList, MobilePage, MobilePager, MobileRow, MobileStats } from './primitives'

const PAGE_SIZE = 10
const PLATFORM: Record<string, string> = { douyin: '抖音', bilibili: 'B站', youtube: 'YT' }

/* ---------------- 作品明细 ---------------- */

export function VideosMobile() {
  const [videos, setVideos] = useState<Video[]>([])
  const [scope, setScope] = useState<'all' | 'own' | 'bench'>('own')
  const [openId, setOpenId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [syncing, setSyncing] = useState(false)
  const load = () => {
    fetch(`/api/videos?scope=all`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setVideos)
      .catch(() => setVideos([]))
  }
  useEffect(load, [])
  const rows = videos.filter((v) =>
    scope === 'all' ? true : scope === 'own' ? v.isOwn : !v.isOwn,
  )
  const pages = Math.ceil(rows.length / PAGE_SIZE)
  const slice = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
  const sync = async () => {
    setSyncing(true)
    await fetch('/api/sync', { method: 'POST' }).catch(() => {})
    setTimeout(load, 8000) // ingest 是异步任务,稍后拉取
    setTimeout(() => setSyncing(false), 9000)
  }
  return (
    <MobilePage
      title="作品明细"
      desc={`${rows.length} 条 · 点行看全量数据`}
      action={
        <button
          onClick={sync}
          disabled={syncing}
          className="h-10 shrink-0 rounded-square bg-primary px-3.5 text-label-sm text-white disabled:opacity-50"
        >
          {syncing ? '同步中…' : '同步'}
        </button>
      }
    >
      <div className="mb-4 flex gap-2">
        {([['own', '自有'], ['bench', '对标'], ['all', '全部']] as const).map(([k, label]) => (
          <button
            key={k}
            onClick={() => { setScope(k); setPage(1) }}
            className={`h-10 flex-1 rounded-square text-label-sm ${
              scope === k ? 'bg-primary text-white' : 'border border-hairline bg-elevated text-body'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <MobileList>
        {slice.map((v) => (
          <MobileRow
            key={v.videoId}
            open={openId === v.videoId}
            onToggle={() => setOpenId(openId === v.videoId ? null : v.videoId)}
            badges={
              <>
                <span className="rounded-full border border-hairline px-2 py-0.5 text-body-sm text-body">
                  {PLATFORM[v.platform] ?? v.platform}
                </span>
                {isViral(v, videos) && (
                  <span className="rounded-full bg-primary px-2 py-0.5 text-body-sm font-medium text-white">爆款</span>
                )}
              </>
            }
            title={v.title}
            meta={`${fmtDate(v.publishTime)} · 播放 ${fmtNum(v.views)} · 收藏率 ${fmtPct(v.views ? v.favorites / v.views : null)}`}
          >
            <MobileStats
              items={[
                { label: '播放', value: fmtNum(v.views) },
                { label: '点赞', value: fmtNum(v.likes) },
                { label: '收藏', value: fmtNum(v.favorites) },
                { label: '完播率', value: fmtPct(v.completionRate) },
                { label: '5s完播', value: fmtPct(v.completion5sRate) },
                { label: '2秒跳出', value: fmtPct(v.skip2sRate) },
                { label: '评论', value: fmtNum(v.comments) },
                { label: '分享', value: fmtNum(v.shares) },
                { label: '时长', value: `${v.durationSec ?? '—'}s` },
              ]}
            />
            {v.url && (
              <a href={v.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-body-sm text-link">
                在创作中心打开 →
              </a>
            )}
          </MobileRow>
        ))}
        {slice.length === 0 && <div className="px-4 py-10 text-center text-mute">暂无作品</div>}
      </MobileList>
      <MobilePager page={page} pages={pages} onChange={setPage} />
    </MobilePage>
  )
}

/* ---------------- 素材库 ---------------- */

interface MaterialItem {
  id: number
  title: string
  url: string | null
  source: string
  category: string | null
  status: string
  score: number | null
  suggestion: string | null
  relevance: number | null
  conflict: number | null
  save_potential: number | null
}

export function MaterialsMobile() {
  const [list, setList] = useState<MaterialItem[]>([])
  const [total, setTotal] = useState(0)
  const [filter, setFilter] = useState('待用')
  const [openId, setOpenId] = useState<number | null>(null)
  const [page, setPage] = useState(1)
  const fetchJob = useJob('materials', () =>
    fetch('/api/materials/fetch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }),
  )

  const load = () => {
    fetch(`/api/materials?status=${encodeURIComponent(filter)}&page=${page}&page_size=${PAGE_SIZE}`)
      .then((r) => (r.ok ? r.json() : { items: [], total: 0, pages: 1 }))
      .then((d) => {
        setList(d.items ?? [])
        setTotal(d.total ?? 0)
      })
      .catch(() => setList([]))
  }
  useEffect(load, [filter, page])

  const setStatus = async (id: number, status: string) => {
    await fetch(`/api/materials/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    }).catch(() => {})
    load()
  }

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <MobilePage
      title="素材库"
      desc={`${total} 条 · 点行看建议与操作`}
      action={
        <button
          onClick={() => fetchJob.trigger(load)}
          disabled={fetchJob.running}
          className="h-10 shrink-0 rounded-square bg-primary px-3.5 text-label-sm text-white disabled:opacity-50"
        >
          {fetchJob.running ? '抓取中…' : '抓取'}
        </button>
      }
    >
      <div className="mb-4 flex gap-2 overflow-x-auto">
        {['待用', '已用', '丢弃', ''].map((f) => (
          <button
            key={f || 'all'}
            onClick={() => { setFilter(f); setPage(1) }}
            className={`h-10 shrink-0 rounded-square px-4 text-label-sm ${
              filter === f ? 'bg-primary text-white' : 'border border-hairline bg-elevated text-body'
            }`}
          >
            {f || '全部'}
          </button>
        ))}
      </div>
      <MobileList>
        {list.map((m) => (
          <MobileRow
            key={m.id}
            open={openId === m.id}
            onToggle={() => setOpenId(openId === m.id ? null : m.id)}
            badges={
              <>
                <span className="rounded-full border border-hairline px-2 py-0.5 text-body-sm text-body">
                  {m.source}
                </span>
                <span className="ml-auto font-mono text-[0.9375rem] font-semibold tabular-nums text-ink">
                  {m.score?.toFixed(1) ?? '—'}
                </span>
              </>
            }
            title={m.title}
            meta={m.category ?? undefined}
          >
            {m.suggestion && <p className="text-body-sm leading-relaxed text-body">{m.suggestion}</p>}
            <div className="mt-3">
              <MobileStats
                items={[
                  { label: '相关', value: fmtNum(m.relevance) },
                  { label: '冲突', value: fmtNum(m.conflict) },
                  { label: '收藏潜力', value: fmtNum(m.save_potential) },
                ]}
              />
            </div>
            <div className="mt-3 flex gap-2">
              {m.status !== '已用' && (
                <button onClick={() => setStatus(m.id, '已用')} className="h-10 flex-1 rounded-square bg-primary text-label-sm text-white">
                  采用
                </button>
              )}
              {m.status !== '丢弃' && (
                <button onClick={() => setStatus(m.id, '丢弃')} className="h-10 flex-1 rounded-square border border-hairline bg-elevated text-label-sm text-ink">
                  丢弃
                </button>
              )}
              {m.url && (
                <a href={m.url} target="_blank" rel="noreferrer" className="flex h-10 flex-1 items-center justify-center rounded-square border border-hairline bg-elevated text-label-sm text-link">
                  原文
                </a>
              )}
            </div>
          </MobileRow>
        ))}
        {list.length === 0 && <div className="px-4 py-10 text-center text-mute">该状态暂无素材</div>}
      </MobileList>
      <MobilePager page={page} pages={pages} onChange={setPage} />
    </MobilePage>
  )
}

/* ---------------- 报告中心 ---------------- */

interface ReportMeta {
  id: number
  title: string
  engine: string
  created_at: string
}

export function ReportsMobile() {
  const [list, setList] = useState<ReportMeta[]>([])
  const [openId, setOpenId] = useState<number | null>(null)
  const [html, setHtml] = useState<Record<number, string>>({})
  const [page, setPage] = useState(1)
  const genJob = useJob('report', () =>
    fetch('/api/report/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scope: 'own' }),
    }),
  )

  const load = () => {
    fetch('/api/reports')
      .then((r) => (r.ok ? r.json() : []))
      .then(setList)
      .catch(() => setList([]))
  }
  useEffect(load, [])

  const open = async (id: number) => {
    if (openId === id) return setOpenId(null)
    setOpenId(id)
    if (!html[id]) {
      const r = await fetch(`/api/reports/${id}`).then((x) => x.json()).catch(() => null)
      if (r?.content_md) {
        const { marked } = await import('marked')
        setHtml((h) => ({ ...h, [id]: marked.parse(r.content_md, { async: false }) as string }))
      }
    }
  }

  const pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE))
  const slice = list.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <MobilePage
      title="报告中心"
      desc={`${list.length} 份 · 点行阅读`}
      action={
        <button
          onClick={() => genJob.trigger(load)}
          disabled={genJob.running}
          className="h-10 shrink-0 rounded-square bg-primary px-3.5 text-label-sm text-white disabled:opacity-50"
        >
          {genJob.running ? '生成中…' : '生成'}
        </button>
      }
    >
      <MobileList>
        {slice.map((r) => (
          <MobileRow
            key={r.id}
            open={openId === r.id}
            onToggle={() => open(r.id)}
            badges={
              <span className={`rounded-full px-2 py-0.5 text-body-sm ${r.engine === 'llm' ? 'bg-primary text-white' : 'bg-warning-soft text-warning-deep'}`}>
                {r.engine === 'llm' ? 'AI' : '统计'}
              </span>
            }
            title={r.title}
            meta={r.created_at.slice(5, 16).replace('T', ' ')}
          >
            {html[r.id] ? (
              <div className="md text-body-sm" dangerouslySetInnerHTML={{ __html: html[r.id] }} />
            ) : (
              <div className="text-body-sm text-mute">加载中…</div>
            )}
          </MobileRow>
        ))}
        {list.length === 0 && <div className="px-4 py-10 text-center text-mute">暂无报告</div>}
      </MobileList>
      <MobilePager page={page} pages={pages} onChange={setPage} />
    </MobilePage>
  )
}
