/* ============================================================
   P2 报告中心:列表 + 生成(异步轮询)+ Markdown 详情
   引擎标识:AI 版 = 墨色标签;统计版 = 琥珀标签(降级)
   ============================================================ */
import { useEffect, useState } from 'react'
import { marked } from 'marked'
import { Card } from '../components/Card'
import { SquareGhost, SquarePrimary } from '../components/Buttons'

interface ReportMeta {
  id: number
  type: string
  title: string
  engine: string
  created_at: string
}

/** 通用异步任务轮询:POST 启动 → 轮询 /api/jobs 直到 running=false */
export function useJob(jobName: 'report' | 'materials' | 'radar', start: () => Promise<Response>) {
  const [running, setRunning] = useState(false)
  const trigger = async (onDone: () => void) => {
    const r = await start()
    if (!r.ok) return
    setRunning(true)
    for (;;) {
      await new Promise((res) => setTimeout(res, 3000))
      try {
        const s = await fetch(`/api/jobs`).then((x) => x.json())
        if (!s?.[jobName]?.running) break
      } catch {
        break
      }
    }
    setRunning(false)
    onDone()
  }
  return { running, trigger }
}

export function Reports() {
  const [list, setList] = useState<ReportMeta[]>([])
  const [detail, setDetail] = useState<{ title: string; html: string } | null>(null)
  const job = useJob(
    'report',
    () => fetch('/api/report/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scope: 'own' }) }),
  )
  const benchJob = useJob(
    'report',
    () => fetch('/api/report/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scope: 'bench' }) }),
  )

  const load = () => {
    void fetch('/api/reports')
      .then((r) => r.json())
      .then(setList)
      .catch(() => setList([]))
  }
  useEffect(load, [])

  const open = async (id: number) => {
    const r = await fetch(`/api/reports/${id}`).then((x) => x.json())
    if (r.content_md) {
      setDetail({ title: r.title, html: marked.parse(r.content_md, { async: false }) as string })
    }
  }

  if (detail) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
        <button
          onClick={() => setDetail(null)}
          className="mb-6 flex items-center gap-2 text-body-md text-body hover:text-ink"
        >
          ← 返回列表
        </button>
        <div className="mb-2 eyebrow">{detail.title}</div>
        <Card>
          <div className="md" dangerouslySetInnerHTML={{ __html: detail.html }} />
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
      <div className="eyebrow">Reports</div>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-heading-lg text-ink">报告中心</h1>
        <div className="flex flex-wrap gap-2">
          <SquarePrimary onClick={() => job.trigger(load)} disabled={job.running}>
            {job.running ? '生成中(约3分钟)…' : '生成报告(自有数据)'}
          </SquarePrimary>
          <SquareGhost
            onClick={() => benchJob.trigger(load)}
            disabled={benchJob.running}
            className="h-8"
          >
            {benchJob.running ? '对标拆解中…' : '对标爆款拆解(B站/YouTube/手动)'}
          </SquareGhost>
        </div>
      </div>

      <Card className="mt-8" padded={false}>
        <div className="divide-y divide-hairline">
          {list.map((r) => (
            <button
              key={r.id}
              onClick={() => open(r.id)}
              className="flex w-full items-center gap-4 px-8 py-4 text-left hover:bg-hairline-soft"
            >
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-body-sm ${
                  r.engine === 'llm' ? 'bg-primary text-white' : 'bg-warning-soft text-warning-deep'
                }`}
              >
                {r.engine === 'llm' ? 'AI' : '统计'}
              </span>
              <span className="min-w-0 flex-1 truncate text-body-md text-ink">{r.title}</span>
              <span className="font-mono text-[13px] text-mute">{r.created_at.slice(5, 16).replace('T', ' ')}</span>
            </button>
          ))}
          {list.length === 0 && (
            <div className="px-8 py-12 text-center text-mute">还没有报告,点右上角生成第一份</div>
          )}
        </div>
      </Card>
    </div>
  )
}
