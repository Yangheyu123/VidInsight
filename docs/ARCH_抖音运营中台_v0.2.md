# 总架构:抖音运营中台 v0.2(待评审)

> 本文档是项目顶层设计,原《PRD_爆款雷达_V1.0》降级为中台的一个采集模块文档。
> 核心原则:**能组合复用就不重复造轮子;全自动为主,少数环节人工。**

| 项 | 内容 |
|---|---|
| 日期 | 2026-10-26 |
| 状态 | ⏸ 等待评审,通过后按"一期"开工 |

---

## 1. 项目最终目标 → 能力地图

| # | 目标 | 承接能力 | 复用 | 自建 |
|---|---|---|---|---|
| G1 | 分析同赛道爆火视频模板并产出 | 对标采集 + 爆款统计 + LLM 拆解 | yt-dlp(B站/YT)、douyin-mcp | 统计引擎、拆解报告引擎 |
| G2 | 不断优化视频产出工作流 | 数据回流 → 模板库 → 脚本生成 → 复盘闭环 | LLM API | 模板沉淀、复盘对比 |
| G3 | 随时看到我的数据 | 统一数据库 + 看板 | **Streamlit**、SQLite | 看板页面(少量) |
| G4 | 自动抓取适合的文字素材/创作模式 | 素材引擎 | **RSSHub**(知乎/微博/名言源) | 采集适配 + LLM 筛选打分 |
| G5 | 全自动运行 | 定时调度 + 失败通知 | Windows 任务计划、Server酱/飞书 webhook | 调度脚本 |

**自建部分只有四块**:统一数据层、统计/拆解引擎、看板页面、素材筛选。其余全部站在开源肩膀上。

---

## 2. 分层架构

```
┌─────────────────────── 应用层(看到的) ───────────────────────┐
│  Streamlit 看板                  LLM 拆解报告(定时生成/推送)   │
│  ·我的数据 ·对标爆款 ·素材库 ·模板库 ·报告中心                 │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌─────────────────────── 分析层(自建核心) ─────────────────────┐
│  统计引擎(爆款判定/时段/标题/时长/完播率)  → 沿用爆款雷达设计    │
│  LLM 引擎(拆解报告/素材打分/脚本生成)                          │
└────────────────────────────┬─────────────────────────────────┘
                             ▼
┌─────────────────────── 数据层(自建核心) ─────────────────────┐
│  SQLite 统一库 platform.db                                    │
│  videos / snapshots / reports / materials / templates         │
│  (全平台统一 schema,列名映射层吃各种来源)                      │
└──────┬─────────────────┬─────────────────┬───────────────────┘
       ▼                 ▼                 ▼
┌────────────┐  ┌────────────────┐  ┌────────────────┐
│ 抖音自数据  │  │ B站/YouTube 对标│  │ 文字素材        │
│ douyin-mcp │  │ 爆款雷达(yt-dlp)│  │ RSSHub+爬虫    │
│ (复用开源)  │  │ (自建,已评审)   │  │ (复用RSSHub)   │
└────────────┘  └────────────────┘  └────────────────┘
       ▼                 ▼                 ▼
┌─────────────────── 调度层(全复用) ───────────────────────────┐
│  Windows 任务计划:每日 sync / 每周采集 / 每日素材 / 失败通知    │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 一期:抖音数据中台(当前最关键,先做)

### 3.1 范围
**目标:你的账号数据每天自动进库、自动算指标、随时打开看板看。**

| 模块 | 内容 | 来源 |
|---|---|---|
| A1 采集接入 | douyin-mcp 定时 sync:播放/曝光/完播率/5秒完播/平均观看时长/涨粉/赞评藏分享 → CSV | 复用开源,每日 1 次 |
| A2 列名映射 | douyin-mcp 导出表 → 统一 schema(该映射层同时兼容抖音后台手动导出 Excel、爆款雷达 CSV) | 自建,薄层 |
| A3 统一数据库 | SQLite,5 张表(见 §5);每次 sync 存快照,支持增量趋势 | 自建 |
| A4 指标引擎 | 收藏率/完播率/5s完播/涨粉效率 + 自有视频纵向对比(哪条视频模板有效) | 自建(复用爆款雷达统计代码) |
| A5 看板 | Streamlit 三页:①总览(指标卡+趋势线) ②作品明细(排序/筛爆款) ③对比(模板 A vs B 的完播差异) | 框架复用,页面自建 |
| A6 自动化 | 调度器:sources 表驱动(next_fetch_at 到期即抓)+ fetch_run 审计 + 健康状态机(连续失败→退避→告警);Windows 任务计划只负责触发 tick;失败/cookie 过期 → 飞书/Server酱 分级推送(含恢复上报) | 复用系统调度 + 自建轻量调度内核 |

### 3.2 人工节点(仅此处例外)
- cookie 过期后重新扫码(约每月一次,收到推送再操作)
- 看板看数、拍板选题(本来就是人干的事)

### 3.3 一期验收标准
1. 连续 7 天无人工干预,数据每日自动入库
2. 看板打开即见:总播放/平均完播率/平均5s完播/收藏率/累计涨粉 五张指标卡 + 30 天趋势线
3. 作品表按完播率/收藏率排序,单条视频能看到逐日数据变化
4. cookie 失效时,手机能收到"该扫码了"推送

## 4. 二期~四期路线

| 期 | 内容 | 依赖 |
|---|---|---|
| 二期 | 爆款雷达接入(PRD_爆款雷达_V1.0 原样执行):B站/YouTube 对标采集+拆解报告 → 写入同一数据库(is_own=0),看板加"对标爆款页" | 一期库表 |
| 三期 | 素材引擎:RSSHub 抓知乎热榜/哲学话题/名言金句 → LLM 按"赛道相关性×冲突感×收藏潜力"打分 → 素材库 + 每日推送 Top10 | 一二期 |
| 四期 | 生产工作流:模板库沉淀 → LLM 按模板写脚本 → 人工终审 →(可选)TTS+自动剪辑+douyin-creator 自动发布 | 全部 |

## 5. 统一库 schema(核心,所有模块对齐这张表)

```sql
videos      -- 作品主表(自有+对标统一)
  platform, video_id, url, title, publish_time, duration_sec,
  views, likes, favorites, comments, shares,
  completion_rate, completion_5s_rate, avg_watch_sec,   -- 抖音自有
  exposure, followers_gained,                            -- 抖音自有
  is_own,                                               -- 1=我的 0=对标
  collected_at

snapshots   -- 逐日快照(增量/趋势)
  video_id, date, views, likes, favorites, comments, completion_rate...

sources     -- 采集源注册表(移植自 AIHOT sources + 毕设 data_source,两版合并)
  id, name, kind(douyin_self/bilibili/youtube_rss/external...), config(json),
  enabled, health(ok/degraded/failing/paused), fail_count, last_error,
  cursor(json 水位线), next_fetch_at, interval_minutes

fetch_runs  -- 每次抓取审计行(两个项目均有同构表,强验证)
  source_id, started_at, status(success/partial/failed),
  found_count, new_count, duration_ms, error

reports     -- LLM 报告
  id, type(拆解/复盘/素材简报), title, content_md, created_at

materials   -- 素材库
  id, source(rss/知乎/名言), title, content, url, score, status(待用/已用/丢弃), tags

templates   -- 模板库(从爆款拆解中沉淀)
  id, name, hook, structure_md, avg_completion_rate, source_report_id
```

## 6. 前端决策(已按需求方指定更新)

**结论:正式 React 前端,设计系统 = Vercel 官方 DESIGN.md(Geist),不走 Figma 流程。**
- 设计规范已安装至根目录 `DESIGN.md`(`npx getdesign add vercel`),作为所有 UI 的唯一视觉依据
- 技术栈:Vite + React + TypeScript + Tailwind CSS v4(tokens 直接映射 DESIGN.md 色板/字阶/圆角)+ Recharts(按 Geist 灰阶重皮肤)
- 页面结构不变:总览 / 作品明细 / 模板对比 三页 + 报告、素材占位页
- 数据层:`DataSource` 接口 + 类型化 mock(与统一 SQLite schema 一一对应),后端 FastAPI 就绪后一行切换

## 7. 技术栈总表

| 层 | 选型 | 性质 |
|---|---|---|
| 采集 | douyin-mcp / yt-dlp / RSSHub | 复用 |
| 存储 | SQLite(标准库自带) | 复用 |
| 分析 | pandas + jieba + openai SDK | 复用 |
| 看板 | Streamlit | 复用框架 |
| 调度 | Windows 任务计划 + bat | 复用 |
| 通知 | Server酱 / 飞书 webhook | 复用 |
| **自建** | 统一 schema、映射层、指标引擎、看板页面、LLM prompt 体系 | **约 6 个 Python 文件的工作量** |

## 8. 采集链路复用资产(aimonitor 双项目侦察结论)

> 侦察对象:`D:\个人项目\aimonitor\AIHOT`(开源,TS/Postgres)与 `aimonitor-microservices`(毕设,Java/Spring)。
> 两者都没有抖音/视频采集"弹药",但独立演化出同构的采集调度"骨架",设计互相印证。

### 8.1 直接移植(设计 → 我们的 SQLite)

| 移植物 | 来源 | 去处 |
|---|---|---|
| 健康状态机 ok→degraded→failing→告警→恢复 | 毕设 `SourceHealthService` + AIHOT `health` 字段 | sources 表 + A6 调度器 |
| 失败退避:失败 n 次 → 间隔×(n+2) 指数推迟 | AIHOT `collect.ts` | A6 调度器 |
| fetch_run 抓取审计(两项目同构) | 毕设 `V10__fetch_run.sql` | fetch_runs 表 |
| cursor 水位线增量(如 since_id) | AIHOT `sources.cursor` | sources 表 |
| 分级告警 + 恢复上报(飞书) | AIHOT `operations/alerts.ts` + `notify/feishu.ts` | A6 通知模块 |
| external ingest 统一推送入口 | AIHOT `POST /api/ingest/items` | douyin-mcp/爆款雷达适配器的统一入库通道,采集与存储解耦 |
| B站搜索 API 字段映射(播放/点赞/弹幕/评论/UP主) | 毕设 `BilibiliFetcher.java` | 爆款雷达 B站适配器备选路径(仍以 yt-dlp 为主) |
| YouTube 频道 RSS 采集(304 条件请求) | AIHOT `rss.ts` | 爆款雷达 YouTube 轻量路径(免 yt-dlp 依赖的备选) |

### 8.2 参考不搬码

- 毕设 `DataSourceFetcher` 四方法策略接口 + 配置驱动分发:Python 侧按此形状设计采集器抽象
- 毕设 DLX 死信重试(x-retry≤3 回投)思想:SQLite 单机场景简化为重试计数列
- AIHOT receipts/budgets 付费请求预算熔断:接入付费数据服务(蝉妈妈类)时再启用

### 8.3 明确不搬

- 两家运行时:Postgres+pg-boss、Nacos+RabbitMQ+Redis+MySQL(与 SQLite 单机原则冲突)
- AI/编辑链路、事件聚簇、RBAC、websocket 推送(与中台业务无关)
- Bing/Sogou 正则解析、Twitter/微信公众号付费 API 适配器

## 9. 风险

| 风险 | 应对 |
|---|---|
| douyin-mcp 停更/接口失效 | 映射层隔离:换 xhs_douyin_content 或手动导出 Excel,库和看板不动 |
| 自动化触发风控 | 频率锁死每日 1 次、只读、不加发布自动化 |
| LLM 成本 | 素材打分用便宜模型,拆解报告按需触发 |
| 素材源被封 | RSSHub 多源冗余,挂了换源,素材引擎降级人工投喂 |

## 10. 待确认项

1. 一期范围(§3.1 六个模块)是否认可?有无要增删?
2. 通知通道:Server酱(微信)还是飞书 webhook?
3. 每日采集时间 09:00 合适吗?(建议选你通常看数据的时间)
4. Streamlit 本地跑(浏览器开 localhost)满足"看数据"需求,还是要局域网手机可访问?
5. douyin-mcp 装好后需要你扫码一次,这步现在就能做吗?
