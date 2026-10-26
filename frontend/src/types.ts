/* ============================================================
   统一数据模型 —— 与总架构 §5 SQLite schema 一一对应
   后端(FastAPI + platform.db)就绪后,前端零改动切换
   ============================================================ */

export type Platform = 'douyin' | 'bilibili' | 'youtube'

/** videos 表:作品主表(自有 + 对标统一,is_own 区分) */
export interface Video {
  videoId: string
  platform: Platform
  accountId?: string | null
  url: string
  title: string
  publishTime: string // ISO 8601
  durationSec: number
  views: number
  likes: number
  favorites: number
  comments: number
  shares: number
  /** 以下为抖音自有数据(douyin-mcp 采集),对标视频为 null */
  completionRate: number | null // 完播率 0-1
  completion5sRate: number | null // 5秒完播率 0-1
  skip2sRate?: number | null // 2秒跳出率 0-1(越低越好)
  avgWatchSec: number | null
  exposure: number | null // 曝光量
  followersGained: number | null // 涨粉
  /** 全量补充字段(raw_metric_json 解析,页面显示什么存什么) */
  danmaku?: number | null // 弹幕量
  unfollows?: number | null // 脱粉量
  followerPlayRatio?: number | null // 粉丝播放占比
  avgPlayRatio?: number | null // 平均播放占比
  dislikeRate?: number | null // 不感兴趣率
  likeRate?: number | null // 平台口径点赞率
  commentRate?: number | null // 平台口径评论率
  shareRate?: number | null // 平台口径分享率
  favoriteRate?: number | null // 平台口径收藏率
  coverUrl?: string | null
  status?: string | null
  isOwn: boolean
  templateId: string | null
  collectedAt: string
}

/** 派生指标(展示层计算,不落库) */
export const favRate = (v: Video): number | null =>
  v.views > 0 ? v.favorites / v.views : null
export const likeRate = (v: Video): number | null =>
  v.views > 0 ? v.likes / v.views : null

/** snapshots 表聚合:账号级逐日数据(趋势图用) */
export interface DailyStat {
  date: string // YYYY-MM-DD
  plays: number
  newFollowers: number
  avgCompletion: number | null // 0-1;无快照日为 null
}

/** templates 表:从爆款拆解沉淀的创作模板 */
export interface Template {
  id: string
  name: string
  hook: string // 开场钩子范式
  structure: string // 脚本节奏(开头/中段/结尾)
  accent: 'develop' | 'preview' | 'ship' // 图表强调色(渐变三件套)
  stats: {
    videos: number
    avgViews: number
    avgCompletion: number
    avg5s: number
    avgFavRate: number
  }
}

/** 采集源健康状态(调度层心跳) */
export interface SyncStatus {
  source: string // 如 douyin-mcp
  state: 'ok' | 'stale' | 'error'
  lastSync: string | null // ISO
  detail: string
  running?: boolean // 后端扩展:同步进行中
  lastResult?: { found: number; new: number } | null
  error?: string | null
}

/** 数据源接口:mock 与未来 FastAPI 实现同一契约 */
export interface DataSource {
  videos(): Promise<Video[]>
  dailyStats(days: number): Promise<DailyStat[]>
  templates(): Promise<Template[]>
  syncStatus(): Promise<SyncStatus>
}
