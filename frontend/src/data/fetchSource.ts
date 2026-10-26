/* ============================================================
   真实数据源:FastAPI(backend/api.py)
   经 Vite 同源代理 /api → 127.0.0.1:8787,免 CORS
   ============================================================ */
import type { DataSource } from '../types'

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${path} → ${r.status}`)
  return r.json() as Promise<T>
}

export const fetchSource: DataSource = {
  videos: () => get('/api/videos'),
  dailyStats: (days: number) => get(`/api/daily?days=${days}`),
  templates: () => get('/api/templates'),
  syncStatus: () => get('/api/sync-status'),
}
