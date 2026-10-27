/* ============================================================
   剧本发布前预检:网页AI给的剧本 → 粘贴体检 → 通过再喂 agent
   规则层(时长/开场/结尾/断句)本地秒判 + GLM 对照数据铁律深检
   ============================================================ */
import { useState } from 'react'
import { Card } from '../components/Card'
import { SquarePrimary, SquareGhost } from '../components/Buttons'
import { useJob } from './Reports'

interface Issue {
  severity: 'high' | 'mid' | 'low'
  location: string
  problem: string
  fix: string
}

interface Evidence {
  kind: 'own_video' | 'bench' | 'report'
  title: string
  text: string
  age_days: number
}

interface PrecheckResult {
  score: number
  verdict: string
  items: Issue[]
  strengths: string[]
  rewrite_hook: string
  rewrite: string
  evidence: Evidence[]
  stats: { chars: number; sentences: number; est_seconds: number }
  llm_ok: boolean
  error?: string
}

const SEV: Record<string, { label: string; cls: string }> = {
  high: { label: '高危', cls: 'bg-[#dc2626]/10 text-[#b91c1c]' },
  mid: { label: '建议改', cls: 'bg-[#d97706]/10 text-[#b45309]' },
  low: { label: '微调', cls: 'bg-hairline-soft text-body' },
}

const VERDICT: Record<string, { cls: string; hint: string }> = {
  可发: { cls: 'bg-[#059669]/10 text-[#047857]', hint: '可以喂 agent 了' },
  小改: { cls: 'bg-[#d97706]/10 text-[#b45309]', hint: '按下面高危/建议改完再发' },
  重写: { cls: 'bg-[#dc2626]/10 text-[#b91c1c]', hint: '结构性问题,建议带着改法回网页AI重生成' },
}

export function Precheck() {
  const [text, setText] = useState('')
  const [result, setResult] = useState<PrecheckResult | null>(null)
  const [copied, setCopied] = useState(false)
  const job = useJob('precheck', () =>
    fetch('/api/precheck', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  )

  const run = () => {
    if (text.trim().length < 20) {
      setResult({ error: '剧本太短(至少 20 字)' } as PrecheckResult)
      return
    }
    setResult(null)
    job.trigger(async () => {
      const s = await fetch('/api/jobs').then((x) => x.json())
      setResult(s?.precheck?.result ?? { error: s?.precheck?.error ?? '无结果' })
    })
  }

  const v = result && !result.error ? VERDICT[result.verdict] ?? VERDICT['小改'] : null

  return (
    <div className="mx-auto max-w-4xl px-5 py-7 sm:px-6 sm:py-10 lg:px-10">
      <div className="eyebrow">发布前干预</div>
      <h1 className="mt-1 text-heading-lg text-ink">剧本预检</h1>
      <p className="mt-2 max-w-xl text-body-md text-body">
        网页 AI 给你剧本之后、喂 agent 之前,粘进来 10 秒体检:开场具象度、钩子、结尾评论钩子、时长语速——全部对照你自己的账号数据铁律。
      </p>

      <Card className="mt-6">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="把剧本全文粘到这里…" /* eslint-disable-line */
          rows={12}
          className="w-full resize-y rounded-square border border-hairline bg-white px-3.5 py-3 text-body-md text-ink outline-none transition focus:border-ink"
        />
        <div className="mt-4 flex items-center justify-between">
          <span className="font-mono text-xs text-mute">
            {text.replace(/\s/g, '').length} 字 · ≈{(text.replace(/\s/g, '').length / 4.5).toFixed(0)}s
          </span>
          <SquarePrimary onClick={run} disabled={job.running}>
            {job.running ? '体检中…' : '开始体检'}
          </SquarePrimary>
        </div>
      </Card>

      {result?.error && (
        <Card className="mt-5">
          <p className="text-body-md text-[#b91c1c]">{result.error}</p>
        </Card>
      )}

      {result && !result.error && (
        <>
          <Card className="mt-5">
            <div className="flex flex-wrap items-center gap-4">
              <span className={`inline-flex items-center rounded-full px-3.5 py-1.5 font-mono text-sm font-semibold ${v?.cls}`}>
                {result.verdict} · {result.score}分
              </span>
              <span className="text-body-md text-body">{v?.hint}</span>
              <span className="ml-auto font-mono text-xs text-mute">
                {result.stats.chars}字 · {result.stats.sentences}句 · ≈{result.stats.est_seconds}s
                {result.llm_ok ? ' · AI深检' : ' · 仅规则层(AI未响应)'}
              </span>
            </div>
            {result.rewrite_hook && (
              <div className="mt-4 rounded-square bg-[#059669]/5 px-4 py-3">
                <div className="eyebrow">备用开场(可直接抄)</div>
                <p className="mt-1 text-body-md text-ink">{result.rewrite_hook}</p>
              </div>
            )}
          </Card>

          {result.items.length > 0 && (
            <div className="mt-5 space-y-3">
              {result.items.map((it, i) => (
                <Card key={i}>
                  <div className="flex items-center gap-2.5">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-xs font-medium ${SEV[it.severity]?.cls ?? SEV.low.cls}`}>
                      {SEV[it.severity]?.label ?? it.severity}
                    </span>
                    <span className="text-label-sm text-ink">{it.location}</span>
                  </div>
                  <p className="mt-2.5 text-body-md text-body">{it.problem}</p>
                  {it.fix && (
                    <p className="mt-2 rounded-square bg-hairline-soft px-3.5 py-2.5 text-body-md text-ink">
                      <span className="font-medium">改法:</span>
                      {it.fix}
                    </p>
                  )}
                </Card>
              ))}
            </div>
          )}

          {result.rewrite && (
            <Card className="mt-5">
              <div className="flex items-center justify-between">
                <div className="eyebrow">修正稿(可直接用)</div>
                <SquareGhost
                  onClick={() => {
                    navigator.clipboard.writeText(result.rewrite)
                    setCopied(true)
                    setTimeout(() => setCopied(false), 1600)
                  }}
                >
                  {copied ? '已复制' : '复制全文'}
                </SquareGhost>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-body-md text-ink">{result.rewrite}</p>
            </Card>
          )}

          {result.evidence?.length > 0 && (
            <Card className="mt-5">
              <div className="eyebrow">本次评审依据(账号真实数据,按新旧加权)</div>
              <div className="mt-3 space-y-2.5">
                {result.evidence.map((e, i) => (
                  <details key={i} className="group">
                    <summary className="flex cursor-pointer list-none items-center gap-2.5 text-body-md text-body hover:text-ink">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 font-mono text-xs ${
                        e.kind === 'own_video' ? 'bg-ink/5 text-ink' : e.kind === 'report' ? 'bg-[#d97706]/10 text-[#b45309]' : 'bg-hairline-soft text-body'
                      }`}>
                        {e.kind === 'own_video' ? `自有·${e.age_days}天前` : e.kind === 'report' ? `报告·${e.age_days}天前` : `爆款·${e.age_days}天前`}
                      </span>
                      <span className="truncate">{e.title}</span>
                    </summary>
                    <p className="mt-2 whitespace-pre-wrap border-l-2 border-hairline pl-3 text-body-sm text-body">
                      {e.text}
                    </p>
                  </details>
                ))}
              </div>
            </Card>
          )}

          {result.strengths.length > 0 && (
            <Card className="mt-5">
              <div className="eyebrow">保留的亮点</div>
              <ul className="mt-2 space-y-1.5">
                {result.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-3 text-body-md text-body">
                    <span className="mt-1.5 size-1.5 shrink-0 rounded-[2px] bg-[#059669]" aria-hidden />
                    {s}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
