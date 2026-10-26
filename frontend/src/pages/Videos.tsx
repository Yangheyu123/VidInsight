/* ============================================================
   作品明细页:筛选胶囊 + 搜索 + 排序表格 + 右侧详情抽屉
   抽屉 = Level-2 悬浮(shadow-float + 发丝线)
   ============================================================ */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer } from 'recharts'
import { Card } from '../components/Card'
import { CategoryPill, Tag, TextInput, ViralBadge } from '../components/Buttons'
import { INK, MONO } from '../components/charts'
import { fmtDate, fmtDur, fmtNum, fmtPct } from '../data/format'
import { isViral, viralThreshold } from '../data/stats'
import type { Template, Video } from '../types'
import { getSource } from '../data/source'
import { useJob } from './Reports'

type SortKey = 'publishTime' | 'views' | 'completionRate' | 'favorites' | 'favRate'
type FilterKey = 'all' | 'viral' | '7d' | '30d'
type Scope = 'own' | 'bench' | 'all'

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'viral', label: '仅爆款' },
  { key: '7d', label: '近 7 天' },
  { key: '30d', label: '近 30 天' },
]

const SCOPES: { key: Scope; label: string }[] = [
  { key: 'own', label: '自有' },
  { key: 'bench', label: '对标' },
  { key: 'all', label: '全部' },
]

const PLATFORM_LABEL: Record<string, string> = { douyin: '抖音', bilibili: 'B站', youtube: 'YouTube' }

const COLUMNS: { key: SortKey | null; label: string; align?: 'right' }[] = [
  { key: null, label: '标题' },
  { key: 'publishTime', label: '发布' },
  { key: null, label: '时长' },
  { key: 'views', label: '播放', align: 'right' },
  { key: 'completionRate', label: '完播率', align: 'right' },
  { key: null, label: '5s完播', align: 'right' },
  { key: null, label: '2s跳出', align: 'right' },
  { key: 'favRate', label: '收藏率', align: 'right' },
  { key: 'favorites', label: '收藏', align: 'right' },
]

export function Videos() {
  const [videos, setVideos] = useState<Video[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [filter, setFilter] = useState<FilterKey>('all')
  const [scope, setScope] = useState<Scope>('own')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: 'publishTime', dir: -1 })
  const [selected, setSelected] = useState<Video | null>(null)
  const [dailyRows, setDailyRows] = useState<{ date: string; views: number }[]>([])

  // 雷达采集(对标模式专用):关键词 + 平台
  const [kw, setKw] = useState('哲学 思辨')
  const [plat, setPlat] = useState<'bilibili' | 'youtube'>('bilibili')
  const radarJob = useJob(
    'radar',
    () =>
      fetch('/api/radar/collect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'search', platform: plat, keyword: kw, limit: 10 }),
      }),
  )

  // 抽屉打开时拉取该作品的天级真实曲线,不足 2 点则回退衰减模型
  useEffect(() => {
    if (!selected) return
    setDailyRows([])
    fetch(`/api/videos/${selected.videoId}/daily`)
      .then((r) => (r.ok ? r.json() : []))
      .then((rows: { date: string; views: number }[]) => setDailyRows(rows))
      .catch(() => setDailyRows([]))
  }, [selected?.videoId])

  const load = useCallback(async () => {
    try {
      const ds = await getSource()
      setVideos(await fetch(`/api/videos?scope=${scope}`).then((r) => (r.ok ? r.json() : ds.videos())))
      setTemplates(await ds.templates())
    } catch {
      /* 离线态由全局横幅兜底 */
    }
  }, [scope])
  useEffect(() => {
    void load()
  }, [load])

  const threshold = useMemo(() => viralThreshold(videos), [videos])

  const rows = useMemo(() => {
    const favR = (v: Video) => (v.views ? v.favorites / v.views : -1)
    let list = [...videos]
    if (filter === 'viral') list = list.filter((v) => v.views >= threshold)
    if (filter === '7d') list = list.filter((v) => Date.now() - new Date(v.publishTime).getTime() <= 7 * 86_400_000)
    if (filter === '30d') list = list.filter((v) => Date.now() - new Date(v.publishTime).getTime() <= 30 * 86_400_000)
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter((v) => v.title.toLowerCase().includes(q))
    }
    const val = (v: Video): number | string =>
      sort.key === 'favRate' ? favR(v) : sort.key === 'publishTime' ? v.publishTime : (v[sort.key] as number)
    list.sort((a, b) => {
      const va = val(a)
      const vb = val(b)
      return (va < vb ? -1 : va > vb ? 1 : 0) * sort.dir
    })
    return list
  }, [videos, filter, query, sort, threshold])

  const toggleSort = (key: SortKey | null) => {
    if (!key) return
    setSort((s) => (s.key === key ? { key, dir: s.dir === 1 ? -1 : 1 } : { key, dir: -1 }))
  }

  const templateName = (id: string | null) => templates.find((t) => t.id === id)?.name ?? '—'

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      {/* 页头 */}
      <div className="eyebrow">Videos</div>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-heading-lg text-ink">作品明细</h1>
        <div className="font-mono text-xs text-mute">
          {rows.length} 条 · 爆款线 {fmtNum(threshold)}
        </div>
      </div>

      {/* 数据域:自有 / 对标 / 全部 */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        {SCOPES.map((s) => (
          <CategoryPill key={s.key} active={scope === s.key} onClick={() => setScope(s.key)}>
            {s.label}
          </CategoryPill>
        ))}
        <span className="mx-1 hidden h-5 w-px bg-hairline sm:block" />
        {FILTERS.map((f) => (
          <CategoryPill key={f.key} active={filter === f.key} onClick={() => setFilter(f.key)}>
            {f.label}
          </CategoryPill>
        ))}
        <div className="ml-auto w-56">
          <TextInput value={query} onChange={setQuery} placeholder="搜索标题…" />
        </div>
      </div>

      {/* 对标模式:雷达采集条 */}
      {scope !== 'own' && (
        <div className="mt-4 flex flex-wrap items-center gap-2 rounded-card border border-hairline bg-elevated p-2.5">
          <span className="eyebrow ml-1">Radar</span>
          <div className="flex rounded-square border border-hairline p-0.5">
            {(['bilibili', 'youtube'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPlat(p)}
                className={`h-8 rounded-[4px] px-3 font-mono text-[13px] transition-colors ${
                  plat === p ? 'bg-primary text-white' : 'text-body hover:text-ink'
                }`}
              >
                {p === 'bilibili' ? 'B站' : 'YouTube'}
              </button>
            ))}
          </div>
          <div className="w-52">
            <TextInput value={kw} onChange={setKw} placeholder="关键词…" />
          </div>
          <button
            onClick={() => radarJob.trigger(load)}
            disabled={radarJob.running}
            className="inline-flex h-9 items-center rounded-square bg-primary px-3 text-label-sm text-white transition-colors hover:bg-ink disabled:opacity-50"
          >
            {radarJob.running ? '采集中(限流慢采)…' : '雷达采集'}
          </button>
          <span className="text-body-sm text-mute">yt-dlp 两阶段 · B站2-4s/条限流</span>
        </div>
      )}

      {/* 表格 */}
      <Card className="mt-4" padded={false}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[880px] border-collapse text-body-md">
            <thead>
              <tr className="border-b border-hairline">
                {COLUMNS.map((c) => (
                  <th
                    key={c.label}
                    onClick={() => toggleSort(c.key)}
                    className={`px-4 py-3.5 font-mono text-[13px] font-medium uppercase tracking-normal text-mute ${
                      c.key ? 'cursor-pointer select-none hover:text-ink' : ''
                    } ${c.align === 'right' ? 'text-right' : 'text-left'}`}
                  >
                    {c.label}
                    {c.key && sort.key === c.key && <span className="ml-1 text-ink">{sort.dir === -1 ? '↓' : '↑'}</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((v) => {
                const viral = isViral(v, videos)
                const fr = v.views ? v.favorites / v.views : null
                return (
                  <tr
                    key={v.videoId}
                    onClick={() => setSelected(v)}
                    className="cursor-pointer border-b border-hairline last:border-0 hover:bg-hairline-soft"
                  >
                    <td className="max-w-[280px] px-4 py-3.5">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full border border-hairline px-2 py-0.5 text-body-sm text-body">
                          {PLATFORM_LABEL[v.platform] ?? v.platform}
                        </span>
                        <span className="truncate text-ink">{v.title}</span>
                        {viral && <ViralBadge />}
                      </div>
                      <div className="mt-0.5 text-body-sm text-mute">
                        {v.accountId ?? templateName(v.templateId)}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-[13px] text-body">{fmtDate(v.publishTime)}</td>
                    <td className="px-4 py-3.5 font-mono text-[13px] text-body">{fmtDur(v.durationSec)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] tabular-nums text-ink">{fmtNum(v.views)}</td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] tabular-nums text-body">
                      {fmtPct(v.completionRate)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] tabular-nums text-body">
                      {fmtPct(v.completion5sRate)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] tabular-nums text-body">
                      {fmtPct(v.skip2sRate)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] font-medium tabular-nums text-link-deep">
                      {fmtPct(fr)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono text-[13px] tabular-nums text-body">{fmtNum(v.favorites)}</td>
                  </tr>
                )
              })}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={COLUMNS.length} className="px-4 py-12 text-center text-mute">
                    {videos.length === 0
                      ? scope === 'bench'
                        ? '对标库为空 · 去「雷达采集」抓对标(见报告中心旁的模板页说明)或让 R 跑一次'
                        : '后端未连接或未同步 · 此界面不显示模拟数据'
                      : '没有匹配的作品'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* 详情抽屉(L2 悬浮) */}
      {selected && (
        <>
          <button
            aria-label="关闭"
            className="fixed inset-0 z-40 h-full w-full cursor-default bg-black/5"
            onClick={() => setSelected(null)}
          />
          <aside className="fixed right-0 top-0 z-50 flex h-full w-full max-w-[460px] flex-col overflow-y-auto border-l border-hairline bg-elevated shadow-float">
            <div className="flex items-center justify-between border-b border-hairline px-8 py-4">
              <span className="eyebrow">Video Detail</span>
              <button
                onClick={() => setSelected(null)}
                className="flex size-8 items-center justify-center rounded-full text-body hover:bg-hairline-soft hover:text-ink"
              >
                ✕
              </button>
            </div>
            <div className="space-y-7 px-8 py-7">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <Tag>抖音</Tag>
                  <Tag>{templateName(selected.templateId)}</Tag>
                  {isViral(selected, videos) && <ViralBadge />}
                </div>
                <h2 className="mt-3 text-heading-md text-ink">{selected.title}</h2>
                <div className="mt-1 font-mono text-[13px] text-mute">
                  {fmtDate(selected.publishTime, true)}
                </div>
              </div>

              {/* 指标网格:全量字段 15 格(页面显示什么,这里就有什么) */}
              <div className="grid grid-cols-3 gap-px overflow-hidden rounded-card border border-hairline bg-hairline">
                {[
                  { label: '播放', v: fmtNum(selected.views) },
                  { label: '曝光', v: fmtNum(selected.exposure) },
                  { label: '涨粉', v: selected.followersGained != null ? `+${fmtNum(selected.followersGained)}` : '—' },
                  { label: '完播率', v: fmtPct(selected.completionRate) },
                  { label: '5s完播', v: fmtPct(selected.completion5sRate) },
                  { label: '2s跳出', v: fmtPct(selected.skip2sRate) },
                  { label: '均观看', v: selected.avgWatchSec != null ? `${selected.avgWatchSec.toFixed(1)}s` : '—' },
                  { label: '收藏率', v: fmtPct(selected.views ? selected.favorites / selected.views : null) },
                  { label: '点赞率', v: fmtPct(selected.views ? selected.likes / selected.views : null) },
                  { label: '弹幕', v: selected.danmaku != null ? fmtNum(selected.danmaku) : '—' },
                  { label: '脱粉', v: selected.unfollows != null ? `-${fmtNum(selected.unfollows)}` : '—' },
                  { label: '评论', v: fmtNum(selected.comments) },
                  { label: '不感兴趣率', v: fmtPct(selected.dislikeRate) },
                  { label: '粉丝播放占比', v: fmtPct(selected.followerPlayRatio) },
                  { label: '均播放占比', v: fmtPct(selected.avgPlayRatio) },
                ].map((m) => (
                  <div key={m.label} className="bg-elevated px-3.5 py-3">
                    <div className="text-body-sm text-mute">{m.label}</div>
                    <div className="mt-1 font-mono text-sm tabular-nums text-ink">{m.v}</div>
                  </div>
                ))}
              </div>

              {/* 天级播放曲线:只画真实数据;不足 2 点如实说明,不造假曲线 */}
              <div>
                <div className="eyebrow mb-2">Views · Daily(真实天级)</div>
                {dailyRows.length >= 2 ? (
                  <>
                    <div className="h-32">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart
                          data={dailyRows.map((d) => ({
                            label: d.date.slice(5).replace('-', '/'),
                            v: d.views,
                          }))}
                          margin={{ top: 4, right: 4, bottom: 0, left: 4 }}
                        >
                          <defs>
                            <linearGradient id="drawerFill" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor={INK} stopOpacity={0.18} />
                              <stop offset="100%" stopColor={INK} stopOpacity={0.02} />
                            </linearGradient>
                          </defs>
                          <Area type="monotone" dataKey="v" stroke={INK} strokeWidth={1.5} fill="url(#drawerFill)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="text-right font-mono text-[10px] text-faint" style={{ fontFamily: MONO }}>
                      天级真实累计(video_daily)
                    </div>
                  </>
                ) : (
                  <div className="rounded-card border border-hairline bg-canvas px-4 py-3 text-body-sm text-mute">
                    天级曲线积累中 · 每日 09:05 自动 +1
                  </div>
                )}
              </div>

              {/* 模板归属(P2 沉淀后显示) */}
              {selected.templateId && (
                <div className="rounded-card border border-hairline bg-canvas p-4">
                  <div className="eyebrow">Template</div>
                  <div className="mt-1 text-label-sm text-ink">{templateName(selected.templateId)}</div>
                </div>
              )}
            </div>
          </aside>
        </>
      )}
    </div>
  )
}
