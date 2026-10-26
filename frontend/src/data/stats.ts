/* ============================================================
   统计口径:爆款判定(与爆款雷达同一公式,全平台复用)
   爆款 = 播放 ≥ 3 × 账号历史均值(频道/搜索模式同逻辑)
   ============================================================ */
import type { Video } from '../types'

export function viralThreshold(videos: Video[]): number {
  // views 可能为 null(对标采集缺字段):按 0 参与均值,防 TypeError 整页崩
  return videos.length
    ? (videos.reduce((s, v) => s + (v.views ?? 0), 0) / videos.length) * 3
    : 0
}

export const isViral = (v: Video, videos: Video[]): boolean =>
  (v.views ?? 0) >= viralThreshold(videos)
