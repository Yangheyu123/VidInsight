# VidInsight · 短视频运营数据中台

> 抖音自数据全自动采集 → 统一数据库 → Geist 风格看板 → AI 爆款拆解 → 素材引擎 → 多平台对标雷达。
> 单人创作者的全自动内容作战室:每天 09:05,数据自己更新,报告自己生成。

## 功能总览

| 模块 | 能力 | 引擎 |
|---|---|---|
| **数据看板** | 播放/完播率/5s完播/2秒跳出/收藏率(KPI)/涨粉 六卡 + 天级趋势 | React + Tailwind + Recharts |
| **作品明细** | 全字段表格 + 排序筛选 + 详情抽屉(15 项指标,含弹幕/脱粉/不感兴趣率/粉丝播放占比) | FastAPI + SQLite |
| **报告中心** | LLM 爆款拆解报告,固定 7 章节(时段/标题模板/钩子/脚本节奏/标签/选题/避坑),自动沉淀创作模板 | GLM-5.3-Flash |
| **模板对比** | 模板卡 + A/B 对照图 + 下一优先模板结论 | 报告引擎自动沉淀 |
| **素材引擎** | 知乎热榜 + 微博热搜 + 一言,LLM 按相关性×冲突感×收藏潜力打分,状态流转待用/已用/丢弃 | 公开接口 + LLM |
| **对标雷达** | B站/YouTube 关键词与频道采集,两阶段限流,爆款 3×均值自动判定 | yt-dlp |
| **调度** | 表驱动调度:到期即抓、失败退避、健康状态机、审计留痕 | Windows 任务计划 + tick |

## 架构

```
┌────────────────────── 看板(DESIGN.md · Geist 设计系统) ──────────────────────┐
│   总览      作品明细      模板对比      报告中心      素材库                  │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               ▼ FastAPI(:8787)
┌────────────────────── 统一库 platform.db(SQLite) ───────────────────────────┐
│  videos / snapshots / video_daily / reports / materials / templates         │
│  sources(健康状态机+水位线) / fetch_runs(抓取审计)                          │
└───────┬─────────────────┬──────────────────┬────────────────────────────────┘
        ▼                 ▼                  ▼
  douyin-mcp         爆款雷达(yt-dlp)     素材引擎(公开接口)
  自有账号全指标       B站/YouTube 对标     知乎/微博/一言 + LLM 打分
  (Playwright 无头)   (buvid3 反风控)      (GLM-5.3-Flash)
        └─────────────────┴──────────────────┘
                     每日 09:00 tick(任务计划)
```

## 快速开始(Windows)

**日常一键启动**:双击 `scripts\start.bat` → 自动构建前端 → 单进程全栈服务 → 打开 http://127.0.0.1:8787

开发模式(热更新)才需要双终端:

```bash
git clone https://github.com/Yangheyu123/VidInsight.git && cd VidInsight

# 1. 外部采集器(独立 venv)
git clone https://github.com/Kuhakucai/douyin-mcp vendors/douyin-mcp
cd vendors/douyin-mcp && py -m venv .venv && .venv/Scripts/pip install -e .
.venv/Scripts/douyin-mcp acknowledge-platform-risk --yes
.venv/Scripts/douyin-mcp login          # 扫码一次,登录态存本地
cd ../..

# 2. 后端
py -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt

# 3. 前端
cd frontend && pnpm install && pnpm dev # http://localhost:5173
cd .. && .venv/Scripts/python -m uvicorn backend.api:app --port 8787

# 4. 每日自动化
schtasks /Create /TN VidInsightTick /SC DAILY /ST 09:05 /TR "项目路径\scripts\tick.bat" /F
```

## 数据口径(诚实原则)

- 界面上的每个数字:要么是真的,要么明确标注演示——没有第三种状态
- 页面未显示的指标如实存 `null`,不推导不编造
- 爆款判定:播放 ≥ 3 × 账号均值(自有与对标同公式)
- 天级趋势 = 相邻快照正增量,自接入日起逐日累积

## 路线图

- [x] P1 抖音自数据全链路(采集/统一库/看板/无头调度)
- [x] P2 报告中心(LLM 拆解 + 模板沉淀)
- [x] P3 素材引擎(三源抓取 + LLM 打分)
- [x] P4 对标雷达(B站/YouTube)
- [ ] P5 频道级对标监控(定时增量)+ 新爆款自动报告
- [ ] P6 半自动生产:模板 → LLM 脚本 → 人工终审

## 致谢

- [douyin-mcp](https://github.com/Kuhakucai/douyin-mcp) · 创作者中心采集(AGPL)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) · 多平台元数据引擎
- [DESIGN.md](https://getdesign.md) · Vercel Geist 设计系统
- 一言 Hitokoto / 知乎 / 微博 公开接口

## License

MIT
