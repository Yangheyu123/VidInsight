/* ============================================================
   模板对比页:模板卡(渐变三件套作卡顶强调线)
   + A/B 选择 + 分组柱状对比 + 结论卡
   回答一个业务问题:下一条视频该套哪个模板?
   ============================================================ */
import { useEffect, useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, SectionHeader } from '../components/Card'
import { axisProps, ChartTooltip, GRAD, gridProps } from '../components/charts'
import { fmtNum, fmtPct } from '../data/format'
import type { Template } from '../types'
import { getSource } from '../data/source'
import { Placeholder } from './Placeholder'

const ACCENT_LINE: Record<Template['accent'], string> = {
  develop: 'grad-develop',
  preview: 'grad-preview',
  ship: 'grad-ship',
}

export function Templates() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [aId, setAId] = useState('T1')
  const [bId, setBId] = useState('T2')

  useEffect(() => {
    void (async () => {
      const ds = await getSource()
      const t = await ds.templates()
      setTemplates(t)
    })()
  }, [])

  // 真实模式:模板由 P2 报告中心沉淀,接入前为空 → 占位说明
  if (templates.length === 0) {
    return (
      <Placeholder
        eyebrow="Templates · Awaiting Data"
        title="模板库待沉淀"
        desc="模板从爆款拆解报告中沉淀生成。触发条件:作品数据积累 + 报告中心(P2)接入。"
        phase="P2 前为空"
        bullets={[
          '当前已在采集的数据:每条作品的完播率 / 5s完播 / 收藏率 / 涨粉',
          'P2 报告中心上线后,LLM 按数据表现自动归纳模板(钩子/结构/指标)',
          '模板对比页将基于真实模板数据自动激活',
        ]}
      />
    )
  }

  const a = templates.find((t) => t.id === aId)
  const b = templates.find((t) => t.id === bId)

  const compareData = useMemo(() => {
    if (!a || !b) return []
    return [
      { metric: '完播率', A: a.stats.avgCompletion, B: b.stats.avgCompletion },
      { metric: '5s完播', A: a.stats.avg5s, B: b.stats.avg5s },
      { metric: '收藏率', A: a.stats.avgFavRate, B: b.stats.avgFavRate },
    ]
  }, [a, b])

  const winner = useMemo(() => {
    if (!a || !b) return null
    const score = (t: Template) => t.stats.avgCompletion + t.stats.avgFavRate * 6
    return score(a) >= score(b) ? a : b
  }, [a, b])

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <div className="eyebrow">Templates</div>
      <h1 className="mt-1 text-heading-lg text-ink">模板对比</h1>
      <p className="mt-2 max-w-xl text-body-lg text-body">
        从爆款拆解沉淀的创作范式。数据回流越多,模板胜率越准。
      </p>

      {/* 模板卡片:卡顶 3px 渐变强调线(系统允许的插画级点缀) */}
      <div className="mt-8 grid gap-4 md:grid-cols-3">
        {templates.map((t) => (
          <Card key={t.id} padded={false} className="overflow-hidden">
            <div className={`h-[3px] w-full ${ACCENT_LINE[t.accent]}`} aria-hidden />
            <div className="p-8">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-xs text-faint">{t.id}</span>
                <span className="font-mono text-xs text-mute">{t.stats.videos} 条作品</span>
              </div>
              <h3 className="mt-2 text-heading-md text-ink">{t.name}</h3>
              <p className="mt-2 border-l-2 border-link pl-3 text-body-md text-body">{t.hook}</p>
              <div className="mt-4 grid grid-cols-3 gap-2 border-t border-hairline pt-4">
                <div>
                  <div className="text-body-sm text-mute">完播率</div>
                  <div className="font-mono text-sm tabular-nums text-ink">{fmtPct(t.stats.avgCompletion)}</div>
                </div>
                <div>
                  <div className="text-body-sm text-mute">5s完播</div>
                  <div className="font-mono text-sm tabular-nums text-ink">{fmtPct(t.stats.avg5s)}</div>
                </div>
                <div>
                  <div className="text-body-sm text-mute">收藏率</div>
                  <div className="font-mono text-sm font-medium tabular-nums text-link-deep">
                    {fmtPct(t.stats.avgFavRate)}
                  </div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* A/B 对比 */}
      <Card className="mt-8" padded={false}>
        <div className="px-6 pt-6">
          <SectionHeader
            eyebrow="A / B Test"
            title="模板对照"
            desc="同一指标,两个模板正面对比"
            right={
              <div className="flex items-center gap-2">
                {([
                  ['A', aId, setAId],
                  ['B', bId, setBId],
                ] as const).map(([slot, cur, set]) => (
                  <label key={slot} className="flex items-center gap-1.5">
                    <span className="font-mono text-xs text-mute">{slot}</span>
                    <select
                      value={cur}
                      onChange={(e) => set(e.target.value)}
                      className="h-9 rounded-square border border-hairline bg-elevated px-2 text-body-md text-ink outline-none focus:border-link"
                    >
                      {templates.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
            }
          />
        </div>
        <div className="h-80 px-2 pb-4">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={compareData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }} barGap={8}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="metric" {...axisProps} />
              <YAxis
                {...axisProps}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                width={52}
              />
              <Tooltip
                cursor={{ fill: '#f2f2f2' }}
                content={({ active, payload, label }) =>
                  active && payload?.length ? (
                    <ChartTooltip
                      title={label as string}
                      rows={[
                        { label: a?.name ?? 'A', value: fmtPct(payload[0]?.payload.A), color: GRAD.develop },
                        { label: b?.name ?? 'B', value: fmtPct(payload[0]?.payload.B), color: GRAD.preview },
                      ]}
                    />
                  ) : null
                }
              />
              <Legend
                formatter={(v) => <span className="text-body-md text-body">{v}</span>}
                iconType="square"
                iconSize={8}
              />
              <Bar name={a?.name ?? 'A'} dataKey="A" fill={GRAD.develop} radius={[3, 3, 0, 0]} maxBarSize={40} />
              <Bar name={b?.name ?? 'B'} dataKey="B" fill={GRAD.preview} radius={[3, 3, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 结论卡:下一条视频的建议 */}
      {winner && a && b && (
        <Card className="mt-6 border-primary">
          <div className="flex flex-wrap items-start gap-6">
            <div className="min-w-0 flex-1">
              <div className="eyebrow">Verdict</div>
              <h3 className="mt-1 text-heading-md text-ink">
                下一优先模板:{winner.name}
              </h3>
              <p className="mt-2 text-body-md text-body">
                以「完播率 + 6×收藏率」加权,{winner.name} 领先。
                其平均播放 {fmtNum(winner.stats.avgViews)},收藏率 {fmtPct(winner.stats.avgFavRate)},
                显著高于对照模板。建议下一条按此结构出稿;若连续两条数据回落,回看 5s 完播是否先于完播率下滑。
              </p>
            </div>
            <div className="flex gap-px overflow-hidden rounded-card border border-hairline bg-hairline">
              {[
                { l: '完播率', v: fmtPct(winner.stats.avgCompletion) },
                { l: '收藏率', v: fmtPct(winner.stats.avgFavRate) },
                { l: '均播放', v: fmtNum(winner.stats.avgViews) },
              ].map((m) => (
                <div key={m.l} className="bg-elevated px-4 py-2.5">
                  <div className="text-body-sm text-mute">{m.l}</div>
                  <div className="font-mono text-sm tabular-nums text-ink">{m.v}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
