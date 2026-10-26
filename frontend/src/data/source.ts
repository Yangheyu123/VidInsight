/* ============================================================
   数据源选择:真实优先,离线显式,演示需手动开启
   · 后端在线 → fetchSource(真实数据)
   · 后端离线 → offlineSource(空数据 + 红点提示,绝不伪装)
   · 演示数据 → 仅当 localStorage ops.demo=1 时启用(页脚开关)
   ============================================================ */
import type { DailyStat, DataSource, SyncStatus, Template, Video } from '../types'
import { SYNC_STATUS, TEMPLATES, VIDEOS, buildDailyStats } from './mock'
import { fetchSource } from './fetchSource'

/** 演示数据源(仅显式开启) */
export const mockSource: DataSource = {
  async videos(): Promise<Video[]> {
    return VIDEOS
  },
  async dailyStats(days: number): Promise<DailyStat[]> {
    return buildDailyStats(days)
  },
  async templates(): Promise<Template[]> {
    return TEMPLATES
  },
  async syncStatus(): Promise<SyncStatus> {
    return { ...SYNC_STATUS, detail: '演示数据(非真实)· 页脚可切回真实' }
  },
}

/** 离线源:空数据 + 明确报错,不造假 */
export const offlineSource: DataSource = {
  async videos(): Promise<Video[]> {
    return []
  },
  async dailyStats(): Promise<DailyStat[]> {
    return []
  },
  async templates(): Promise<Template[]> {
    return []
  },
  async syncStatus(): Promise<SyncStatus> {
    return {
      source: 'backend',
      state: 'error',
      lastSync: null,
      detail: '后端未连接 · 127.0.0.1:8787',
    }
  },
}

export function isDemoMode(): boolean {
  return typeof localStorage !== 'undefined' && localStorage.getItem('ops.demo') === '1'
}

export async function getSource(): Promise<DataSource> {
  if (isDemoMode()) return mockSource
  try {
    await fetchSource.syncStatus()
    return fetchSource
  } catch {
    return offlineSource
  }
}

export { fetchSource }
