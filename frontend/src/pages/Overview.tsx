/* ============================================================
   总览页:hero(唯一的 mesh 渐变出现处)+ 五指标卡
   + 播放/涨粉趋势 + 完播率曲线 + 近期作品速览 + 数据链路状态
   ============================================================ */
import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, SectionHeader } from '../components/Card'
import { MetricCard } from '../components/MetricCard'
import { ViralBadge } from '../components/Buttons'
import { axisProps, ChartTooltip, gridProps, INK, LINK } from '../components/charts'
import { fmtDate, fmtNum, fmtPct } from '../data/format'
import { isViral, viralThreshold } from '../data/stats'
import type { DailyStat, Video } from '../types'
import { getSource } from '../data/source'

const RANGES = [7, 30, 90] as const

/** 区间对比:当前窗口合计 vs 上一窗口合计 → 环比 */
function deltaOf(cur: number[], prev: number[]): number | null {
  const c = cur.reduce((s, x) => s + x, 0)
  const p = prev.reduce((s, x) => s + x, 0)
  return p > 0 ? (c - p) / p : null
}

export function Overview() {
  const [days, setDays] = useState<(typeof RANGES)[number]>(30)
  const [daily, setDaily] = useState<DailyStat[]>([])
  const [dailyMode, setDailyMode] = useState<'increment' | 'cumulative'>('cumulative')
  const [videos, setVideos] = useState<Video[]>([])
  const [all, setAll] = useState<Video[]>([])
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    void (async () => {
      const ds = await getSource()
      try {
        const r = await fetch(`/api/daily?days=${days}`)
        if (r.ok) {
          const d = await r.json()
          setDaily(d.items ?? [])
          setDailyMode(d.mode ?? 'cumulative')
        } else {
          setDaily(await ds.dailyStats(days))
          setDailyMode('cumulative')
        }
      } catch {
        setDaily(await ds.dailyStats(days))
        setDailyMode('cumulative')
      }
      setVideos(await ds.videos())
      // 全局视野数据(自有+对标);后端离线时退化为空
      try {
        const r = await fetch('/api/videos?scope=all')
        setAll(r.ok ? await r.json() : [])
      } catch {
        setAll([])
      }
      setLoaded(true)
    })()
  }, [days])

  // 指标:来自作品层(完播/5s/收藏率)与逐日层(播放/涨粉)
  const stats = useMemo(() => {
    const cur = daily
    const firstHalf = cur.slice(0, Math.floor(cur.length / 2))
    const latterHalf = cur.slice(Math.floor(cur.length / 2))
    const own = videos.filter((v) => v.isOwn)
    const recent = own.filter(
      (v) => Date.now() - new Date(v.publishTime).getTime() <= days * 86_400_000,
    )
    const avg = (xs: (number | null)[]) =>
      xs.filter((x): x is number => x != null).reduce((s, x) => s + x, 0) / (xs.length || 1)
    // 互动三率:点赞/评论/收藏(÷播放)——KPI 卡的三合一
    const interOf = (v: Video) =>
      v.views ? (v.likes + v.comments + v.favorites) / v.views : null
    return {
      plays: cur.reduce((s, d) => s + d.plays, 0),
      playsDelta: deltaOf(
        latterHalf.map((d) => d.plays),
        firstHalf.map((d) => d.plays),
      ),
      followers: cur.reduce((s, d) => s + d.newFollowers, 0),
      followersDelta: deltaOf(
        latterHalf.map((d) => d.newFollowers),
        firstHalf.map((d) => d.newFollowers),
      ),
      completion: avg(recent.map((v) => v.completionRate)),
      completion5s: avg(recent.map((v) => v.completion5sRate)),
      skip2s: avg(recent.map((v) => v.skip2sRate ?? null)),
      interRate: avg(recent.map(interOf)),
      likeRate: avg(recent.map((v) => (v.views ? v.likes / v.views : null))),
      commentRate: avg(recent.map((v) => (v.views ? v.comments / v.views : null))),
      favRate: avg(recent.map((v) => (v.views ? v.favorites / v.views : null))),
    }
  }, [daily, videos, days])

  // 全局视野:自有 vs 对标散点(时长 × 播放,对数轴),爆款大点
  const scatter = useMemo(() => {
    const pool = all.length ? all : videos
    const valid = pool.filter((v) => (v.views ?? 0) > 0) // log 轴不收 0/null
    const th = viralThreshold(pool)
    const pt = (v: Video) => ({
      x: v.durationSec || 0,
      y: v.views || 0,
      name: v.title.slice(0, 24),
      platform: v.platform,
    })
    const viralSet = valid.filter((v) => (v.views ?? 0) >= th)
    return {
      own: valid.filter((v) => v.isOwn && (v.views ?? 0) < th).map(pt),
      bench: valid.filter((v) => !v.isOwn && (v.views ?? 0) < th).map(pt),
      viral: viralSet.map(pt),
      ownCount: pool.filter((v) => v.isOwn).length,
      benchCount: pool.filter((v) => !v.isOwn).length,
      ownMean: Math.round(
        pool.filter((v) => v.isOwn).reduce((s, v) => s + (v.views ?? 0), 0) /
          Math.max(1, pool.filter((v) => v.isOwn).length),
      ),
      benchMean: Math.round(
        pool.filter((v) => !v.isOwn).reduce((s, v) => s + (v.views ?? 0), 0) /
          Math.max(1, pool.filter((v) => !v.isOwn).length),
      ),
      viralLine: th,
    }
  }, [all, videos])

  const topVideos = useMemo(
    () => [...videos].sort((a, b) => b.views - a.views).slice(0, 5),
    [videos],
  )

  const chartData = daily.map((d) => ({
    ...d,
    label: d.date.slice(5).replace('-', '/'),
  }))

  return (
    <div>
      {/* ---- hero band:白画布 + mesh 渐变(全站唯一装饰) ---- */}
      <section className="relative overflow-hidden border-b border-hairline">
        <div className="mesh-bloom -top-24 right-0 h-80 w-[620px] rotate-6" aria-hidden />
        <div className="relative mx-auto flex max-w-7xl flex-wrap items-end justify-between gap-4 px-6 py-7 sm:gap-6 sm:py-16 lg:px-10">
          <div className="min-w-0">
            <div className="eyebrow">Douyin Ops</div>
            <h1 className="mt-1.5 text-heading-md text-ink sm:mt-2 sm:text-heading-lg">总览</h1>
            <p className="mt-1.5 text-body-sm text-mute sm:mt-3 sm:text-body-md">青年思辨哲学 · 18–23 男性 · 核心指标 收藏率</p>
          </div>
          <div className="flex overflow-x-auto rounded-square border border-hairline bg-elevated p-0.5">
            {RANGES.map((r) => (
              <button
                key={r}
                onClick={() => setDays(r)}
                className={`h-8 rounded-[4px] px-3.5 font-mono text-[0.875rem] transition-colors ${
                  days === r ? 'bg-primary text-white' : 'text-body hover:text-ink'
                }`}
              >
                {r}D
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-6 px-5 py-7 sm:space-y-8 sm:px-6 sm:py-10 lg:px-10">
        {/* 加载骨架屏(真实数据到达前的呼吸感) */}
        {!loaded ? (
          <>
            <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="rounded-card border border-hairline bg-elevated p-8">
                  <div className="skeleton h-4 w-16 rounded-[3px]" />
                  <div className="skeleton mt-4 h-10 w-24 rounded-[6px]" />
                  <div className="skeleton mt-3 h-4 w-20 rounded-[3px]" />
                </div>
              ))}
            </div>
            <div className="skeleton h-80 rounded-card" />
          </>
        ) : videos.length === 0 ? (
          <Card>
            <div className="eyebrow">No Data</div>
            <h2 className="mt-1 text-heading-md text-ink">暂无作品数据</h2>
            <p className="mt-2 text-body-md text-body">
              后端未连接或统一库为空。启动后端并触发一次同步:
            </p>
            <code className="mt-3 inline-block rounded-square border border-hairline bg-canvas px-3 py-1.5 font-mono text-[0.875rem] text-body">
              .venv\Scripts\python -m uvicorn backend.api:app --port 8787
            </code>
            <p className="mt-3 text-body-sm text-mute">
              想预览界面效果?页脚「切换演示数据」可显式开启虚构样例(带全站横幅标识)。
            </p>
          </Card>
        ) : (
          <>
        {/* ---- 六指标卡(KPI=互动三率 ---- */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-6">
          <MetricCard
            label="播放量"
            value={fmtNum(stats.plays)}
            delta={dailyMode === 'increment' ? stats.playsDelta : null}
            sub={dailyMode === 'increment' ? `${days} 天增量` : '作品累计'}
          />
          <MetricCard label="完播率" value={fmtPct(stats.completion)} />
          <MetricCard label="5s完播" value={fmtPct(stats.completion5s)} />
          <MetricCard label="2秒跳出" value={fmtPct(stats.skip2s)} />
          <MetricCard
            label="互动率 · KPI"
            value={fmtPct(stats.interRate)}
            highlight
            detail={
              <>
                <span>赞 {fmtPct(stats.likeRate)}</span>
                <span className="text-white/30">·</span>
                <span>评 {fmtPct(stats.commentRate)}</span>
                <span className="text-white/30">·</span>
                <span>藏 {fmtPct(stats.favRate)}</span>
              </>
            }
          />
          <MetricCard
            label="涨粉"
            value={fmtNum(stats.followers)}
            delta={dailyMode === 'increment' ? stats.followersDelta : null}
            sub={dailyMode === 'increment' ? `${days} 天增量` : '作品累计'}
          />
        </div>

        {/* ---- 全局视野:时长 × 播放散点(自有 vs 对标 vs 爆款,对数轴) ---- */}
        <Card className="min-w-0" padded={false}>
          <div className="flex flex-wrap items-end justify-between gap-4 px-6 pt-8 sm:px-8">
            <SectionHeader eyebrow="Landscape" title="全局视野" />
            <div className="flex items-center gap-4 pb-1 font-mono text-[0.875rem] text-mute">
              <span>自有 {scatter.ownCount} · 均 {fmtNum(scatter.ownMean)}</span>
              <span className="text-faint">|</span>
              <span>对标 {scatter.benchCount} · 均 {fmtNum(scatter.benchMean)}</span>
              <span className="text-faint">|</span>
              <span>爆款线 {fmtNum(scatter.viralLine)}</span>
            </div>
          </div>
          <div className="h-80 px-2 pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 12, right: 16, bottom: 8, left: 8 }}>
                <CartesianGrid {...gridProps} />
                <XAxis
                  dataKey="x"
                  name="时长"
                  type="number"
                  domain={[0, 'auto']}
                  {...axisProps}
                  tickFormatter={(v: number) => (v >= 60 ? `${Math.round(v / 60)}m` : `${v}s`)}
                />
                <YAxis
                  dataKey="y"
                  name="播放"
                  scale="log"
                  domain={['auto', 'auto']}
                  allowDataOverflow
                  {...axisProps}
                  tickFormatter={(v: number) => fmtNum(v)}
                  width={56}
                />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3', stroke: '#ebebeb' }}
                  content={({ active, payload }) =>
                    active && payload?.length ? (
                      <ChartTooltip
                        title={payload[0]?.payload?.name ?? ''}
                        rows={[
                          { label: '平台', value: payload[0]?.payload?.platform ?? '—' },
                          { label: '时长', value: `${payload[0]?.payload?.x ?? 0}s` },
                          { label: '播放', value: fmtNum(payload[0]?.payload?.y), color: INK },
                        ]}
                      />
                    ) : null
                  }
                />
                <Scatter name="对标" data={scatter.bench} fill={LINK} fillOpacity={0.55} shape="square" />
                <Scatter name="自有" data={scatter.own} fill={INK} fillOpacity={0.75} />
                <Scatter
                  name="爆款(≥3×均值)"
                  data={scatter.viral}
                  fill={INK}
                  shape="circle"
                  fillOpacity={1}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* ---- 播放/涨粉趋势 ---- */}
        <Card className="min-w-0" padded={false}>
          <div className="px-6 pt-8 sm:px-8">
            <SectionHeader
              eyebrow="Trend"
              title={dailyMode === 'increment' ? '播放与涨粉' : '作品累计播放 · 按发布日'}
              right={
                <span className="pb-1 font-mono text-[0.875rem] text-faint">
                  {dailyMode === 'increment' ? '日增量' : '冷启动口径 · 满2天自动切换日增量'}
                </span>
              }
            />
          </div>
          <div className="h-80 px-2 pb-4">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 8 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="label" {...axisProps} />
                <YAxis
                  yAxisId="left"
                  {...axisProps}
                  tickFormatter={(v: number) => (v >= 10000 ? `${v / 10000}万` : `${v}`)}
                  width={52}
                />
                <YAxis yAxisId="right" orientation="right" {...axisProps} width={36} />
                <Tooltip
                  cursor={{ fill: '#f2f2f2' }}
                  content={({ active, payload, label }) =>
                    active && payload?.length ? (
                      <ChartTooltip
                        title={label as string}
                        rows={[
                          { label: '播放', value: fmtNum(payload[0]?.payload.plays), color: INK },
                          {
                            label: '涨粉',
                            value: `+${payload[0]?.payload.newFollowers ?? 0}`,
                            color: LINK,
                          },
                          {
                            label: '完播',
                            value: fmtPct(payload[0]?.payload.avgCompletion),
                          },
                        ]}
                      />
                    ) : null
                  }
                />
                <Bar yAxisId="left" dataKey="plays" fill={INK} radius={[3, 3, 0, 0]} maxBarSize={26} />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="newFollowers"
                  stroke={LINK}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 3, fill: LINK, strokeWidth: 0 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* ---- 完播率曲线 + 近期作品速览 ---- */}
        <div className="grid gap-6 lg:grid-cols-5">
          <Card className="min-w-0 lg:col-span-3" padded={false}>
            <div className="px-6 pt-8 sm:px-8">
              <SectionHeader eyebrow="Retention" title="完播率" />
            </div>
            <div className="h-64 px-2 pb-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 8 }}>
                  <defs>
                    <linearGradient id="compFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={LINK} stopOpacity={0.25} />
                      <stop offset="100%" stopColor={LINK} stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="label" {...axisProps} />
                  <YAxis
                    {...axisProps}
                    domain={['auto', 'auto']}
                    tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                    width={52}
                  />
                  <Tooltip
                    cursor={{ stroke: '#ebebeb' }}
                    content={({ active, payload, label }) =>
                      active && payload?.length ? (
                        <ChartTooltip
                          title={label as string}
                          rows={[
                            {
                              label: '平均完播率',
                              value: fmtPct(payload[0]?.payload.avgCompletion),
                              color: LINK,
                            },
                          ]}
                        />
                      ) : null
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="avgCompletion"
                    stroke={LINK}
                    strokeWidth={2}
                    fill="url(#compFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <Card className="min-w-0 lg:col-span-2" padded={false}>
            <div className="px-6 pt-8 sm:px-8">
              <SectionHeader eyebrow="Top 5" title="作品" />
            </div>
            <div className="divide-y divide-hairline">
              {topVideos.map((v) => (
                <div key={v.videoId} className="flex items-center gap-3 px-6 py-3.5 sm:px-8">
                  <div className="min-w-0 flex-1">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="truncate text-body-md text-ink">{v.title}</span>
                      {isViral(v, videos) && <ViralBadge />}
                    </div>
                    <div className="mt-0.5 font-mono text-[0.875rem] text-mute">
                      {fmtDate(v.publishTime)} · {fmtNum(v.views)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono text-[0.9375rem] text-ink">{fmtPct(v.views ? v.favorites / v.views : null)}</div>
                    <div className="text-body-sm text-mute">收藏率</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
          </>
        )}
      </div>
    </div>
  )
}
