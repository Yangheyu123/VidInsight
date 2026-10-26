/* ============================================================
   演示数据 —— 赛道:青年思辨哲学(18-23 岁男性,核心 KPI 收藏率)
   说明:后端接入前使用;数字手工调校,保证统计故事成立
   (均值 ≈ 7.5万,3 倍阈值 ≈ 22.4万 → 恰好筛出 2 条爆款)
   ============================================================ */
import type { DailyStat, SyncStatus, Template, Video } from '../types'

const now = new Date()
const daysAgo = (n: number, hour = 21, min = 30): string => {
  const d = new Date(now)
  d.setDate(d.getDate() - n)
  d.setHours(hour, min, 0, 0)
  return d.toISOString()
}

/* ---- videos:12 条自有作品,3 个模板各 4 条 ---- */
export const VIDEOS: Video[] = [
  // T1 反常识开场
  {
    videoId: '7410293847561', platform: 'douyin', url: '#',
    title: '为什么聪明人反而更容易迷茫?', publishTime: daysAgo(3, 21, 12),
    durationSec: 52, views: 280400, likes: 21400, favorites: 24900, comments: 1860, shares: 4120,
    completionRate: 0.481, completion5sRate: 0.712, avgWatchSec: 25.0, exposure: 3_120_000,
    followersGained: 3860, isOwn: true, templateId: 'T1', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7408112653498', platform: 'douyin', url: '#',
    title: '你不是懒,你是被"意义感"饿着了', publishTime: daysAgo(12, 20, 45),
    durationSec: 47, views: 46200, likes: 4100, favorites: 3480, comments: 402, shares: 610,
    completionRate: 0.412, completion5sRate: 0.664, avgWatchSec: 19.4, exposure: 512_000,
    followersGained: 520, isOwn: true, templateId: 'T1', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7405221988377', platform: 'douyin', url: '#',
    title: '25岁前一定要想清楚的一件事', publishTime: daysAgo(24, 22, 5),
    durationSec: 58, views: 22100, likes: 1650, favorites: 1180, comments: 190, shares: 240,
    completionRate: 0.344, completion5sRate: 0.602, avgWatchSec: 20.0, exposure: 260_000,
    followersGained: 210, isOwn: true, templateId: 'T1', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7401888273645', platform: 'douyin', url: '#',
    title: '无聊,是被低估的天赋', publishTime: daysAgo(45, 21, 40),
    durationSec: 41, views: 8200, likes: 520, favorites: 296, comments: 64, shares: 78,
    completionRate: 0.298, completion5sRate: 0.548, avgWatchSec: 12.2, exposure: 96_000,
    followersGained: 60, isOwn: true, templateId: 'T1', collectedAt: daysAgo(0, 9, 0),
  },
  // T2 深夜拷问体
  {
    videoId: '7411555801292', platform: 'douyin', url: '#',
    title: '如果人生没有意义,你敢直接承认吗', publishTime: daysAgo(8, 23, 15),
    durationSec: 63, views: 420800, likes: 35600, favorites: 39500, comments: 3240, shares: 7830,
    completionRate: 0.524, completion5sRate: 0.781, avgWatchSec: 33.0, exposure: 4_650_000,
    followersGained: 6120, isOwn: true, templateId: 'T2', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7409664722815', platform: 'douyin', url: '#',
    title: '深夜11点,你敢回答这3个问题吗', publishTime: daysAgo(17, 23, 2),
    durationSec: 55, views: 27300, likes: 2380, favorites: 2210, comments: 288, shares: 395,
    completionRate: 0.438, completion5sRate: 0.694, avgWatchSec: 24.1, exposure: 310_000,
    followersGained: 340, isOwn: true, templateId: 'T2', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7406339184476', platform: 'douyin', url: '#',
    title: '存在主义救不了你,但能让你不再装睡', publishTime: daysAgo(31, 22, 48),
    durationSec: 68, views: 12400, likes: 980, favorites: 812, comments: 106, shares: 152,
    completionRate: 0.372, completion5sRate: 0.621, avgWatchSec: 25.3, exposure: 148_000,
    followersGained: 130, isOwn: true, templateId: 'T2', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7403112759608', platform: 'douyin', url: '#',
    title: '你刷的不是手机,是逃避自由的成本', publishTime: daysAgo(52, 23, 30),
    durationSec: 49, views: 6800, likes: 470, favorites: 342, comments: 52, shares: 71,
    completionRate: 0.318, completion5sRate: 0.566, avgWatchSec: 15.6, exposure: 82_000,
    followersGained: 48, isOwn: true, templateId: 'T2', collectedAt: daysAgo(0, 9, 0),
  },
  // T3 哲学家翻译机
  {
    videoId: '7408998341723', platform: 'douyin', url: '#',
    title: '叔本华:人最大的愚蠢,是用健康换任何东西', publishTime: daysAgo(14, 12, 20),
    durationSec: 44, views: 31600, likes: 2480, favorites: 1690, comments: 214, shares: 305,
    completionRate: 0.326, completion5sRate: 0.588, avgWatchSec: 14.3, exposure: 355_000,
    followersGained: 260, isOwn: true, templateId: 'T3', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7407441928364', platform: 'douyin', url: '#',
    title: '世界上没有"来不及"这回事,斯多葛这么说', publishTime: daysAgo(21, 12, 15),
    durationSec: 51, views: 18300, likes: 1340, favorites: 860, comments: 128, shares: 187,
    completionRate: 0.291, completion5sRate: 0.541, avgWatchSec: 14.8, exposure: 210_000,
    followersGained: 150, isOwn: true, templateId: 'T3', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7404669302187', platform: 'douyin', url: '#',
    title: '为什么你越努力越焦虑?尼采早就说透了', publishTime: daysAgo(38, 12, 40),
    durationSec: 57, views: 15200, likes: 1180, favorites: 720, comments: 96, shares: 130,
    completionRate: 0.274, completion5sRate: 0.522, avgWatchSec: 15.6, exposure: 178_000,
    followersGained: 120, isOwn: true, templateId: 'T3', collectedAt: daysAgo(0, 9, 0),
  },
  {
    videoId: '7402558173940', platform: 'douyin', url: '#',
    title: '别人问你工资多少时,哲学在想什么', publishTime: daysAgo(58, 12, 8),
    durationSec: 46, views: 9500, likes: 690, favorites: 396, comments: 72, shares: 88,
    completionRate: 0.252, completion5sRate: 0.498, avgWatchSec: 11.6, exposure: 112_000,
    followersGained: 66, isOwn: true, templateId: 'T3', collectedAt: daysAgo(0, 9, 0),
  },
]

/* ---- templates:爆款拆解沉淀的三个范式 ---- */
export const TEMPLATES: Template[] = [
  {
    id: 'T1',
    name: '反常识开场',
    hook: '"你以为是 A,真相恰恰相反"——前 3 秒掀翻观众的默认认知',
    structure: '3s 反常识断言 → 15s 案例或思想实验 → 20s 哲学框架翻译 → 10s 收藏指令("存下来,迷茫时再看")',
    accent: 'develop',
    stats: { videos: 4, avgViews: 89_175, avgCompletion: 0.384, avg5s: 0.632, avgFavRate: 0.058 },
  },
  {
    id: 'T2',
    name: '深夜拷问体',
    hook: '23 点档,连续三问,不给答案,让观众自己坐不住',
    structure: '3s 场景锚定(深夜/独自) → 25s 三连问逐层加压 → 15s 哲学家金句接住 → 8s 开放结尾引导评论',
    accent: 'preview',
    stats: { videos: 4, avgViews: 116_675, avgCompletion: 0.413, avg5s: 0.666, avgFavRate: 0.070 },
  },
  {
    id: 'T3',
    name: '哲学家翻译机',
    hook: '把一句哲学原话,翻译成 18-23 岁的生存处境',
    structure: '3s 金句上屏 → 10s 白话翻译 → 25s 联系具体处境(实习/考研/比较) → 8s 金句回收',
    accent: 'ship',
    stats: { videos: 4, avgViews: 18_650, avgCompletion: 0.286, avg5s: 0.537, avgFavRate: 0.033 },
  },
]

/* ---- dailyStats:由作品发布日确定性推导(基线波动 + 发布日脉冲衰减) ---- */
export function buildDailyStats(days: number): DailyStat[] {
  const out: DailyStat[] = []
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    d.setHours(0, 0, 0, 0)
    const idx = days - 1 - i
    // 基线:两个周期叠加的有机波动
    const base = 2600 + 900 * Math.sin(idx / 3.7) + 420 * Math.sin(idx / 1.9 + 1)
    // 发布脉冲:发布日起 3 天衰减注入播放
    let spike = 0
    let spikeWeight = 0
    for (const v of VIDEOS) {
      const pub = new Date(v.publishTime)
      const diff = Math.floor((d.getTime() - pub.getTime()) / 86_400_000)
      if (diff >= 0 && diff <= 2) spike += (v.views / 10) * [1, 0.55, 0.25][diff]
      if (diff >= 0 && diff <= 6) spikeWeight += v.completionRate ?? 0.3
    }
    const plays = Math.round(base + spike)
    const newFollowers = Math.round(plays * 0.011 + spike * 0.014)
    const avgCompletion = Math.min(0.62, 0.29 + 0.03 * Math.sin(idx / 5) + spikeWeight * 0.004)
    out.push({
      date: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`,
      plays,
      newFollowers,
      avgCompletion,
    })
  }
  return out
}

/* ---- 采集源心跳 ---- */
export const SYNC_STATUS: SyncStatus = {
  source: 'douyin-mcp',
  state: 'ok', // 接入真实调度后:ok=今日已同步 stale=过期 error=失败(触发推送)
  lastSync: daysAgo(0, 9, 0),
  detail: '每日 09:00 · SQLite platform.db',
}

/* ---- 爆款判定:播放 ≥ 3 × 账号均值(与爆款雷达同一公式) ---- */
export function viralThreshold(videos: Video[]): number {
  return videos.length ? (videos.reduce((s, v) => s + v.views, 0) / videos.length) * 3 : 0
}
export const isViral = (v: Video, videos: Video[]): boolean => v.views >= viralThreshold(videos)
