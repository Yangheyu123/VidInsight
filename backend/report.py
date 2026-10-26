"""P2 报告引擎:平台真数据 → LLM(GLM-5.3-Flash)拆解 → reports/templates 表

输出固定 7 章节(PRD 需求 3 原样落地):
  发布时间推荐 / 标题模板 / 钩子模板 / 脚本节奏 / 标签策略 / 选题方向 / 避坑清单
LLM 不可用时降级为统计版报告(全真数字,无 AI 解读),不报错。
报告末尾的 JSON 块自动解析 → templates 表(模板对比页数据源)。
"""
import json
import re
from datetime import datetime

from . import db, llm

SYSTEM = (
    "你是一名资深短视频策略分析师,专注抖音知识类内容。"
    "创作者赛道:青年思辨哲学短视频,受众 18-23 岁男性,核心目标:高收藏率。"
    "规则:只引用给定数据中的真实数字,禁止编造;输出简体中文 Markdown;"
    "结论果断、可执行,少解释多给模板。"
)

SECTIONS = [
    "1. 发布时间推荐",
    "2. 标题模板(8-10 个可直接套用)",
    "3. 钩子模板(前 3 秒开口,6-8 个)",
    "4. 脚本节奏(开头/中段/结尾结构)",
    "5. 标签策略",
    "6. 选题方向(10 个具体选题)",
    "7. 避坑清单(5-8 条)",
]

JSON_INSTRUCTION = """最后另起一段输出模板沉淀(供系统解析,格式严格如下):
```json
{"templates": [{"id": "T1", "name": "模板名", "hook": "钩子一句话", "structure": "结构一句话", "accent": "develop", "stats": {"videos": 4, "avgViews": 10000, "avgCompletion": 0.35, "avg5s": 0.6, "avgFavRate": 0.05}}]}
```
要求:最多 3 个模板;stats 必须按你归类的作品真实数据计算均值;accent 三选一:develop/preview/ship。"""


def _video_lines() -> tuple[str, dict]:
    rows = db.conn().execute(
        "SELECT title, publish_time, duration_sec, views, likes, favorites, comments, shares,"
        " completion_rate, completion_5s_rate, skip_2s_rate, followers_gained, danmaku, unfollows,"
        " dislike_rate, follower_play_ratio, favorite_rate, status"
        " FROM videos WHERE is_own=1 ORDER BY views DESC"
    ).fetchall()
    lines = []
    for r in rows:
        fr = (r["favorites"] / r["views"]) if r["views"] else None
        lines.append(
            f"- 《{r['title']}》[{r['status']}] 时长{r['duration_sec']}s 播放{r['views']} "
            f"赞{r['likes']} 藏{r['favorites']} 评{r['comments']} 转{r['shares']} "
            f"完播{_p(r['completion_rate'])} 5s完播{_p(r['completion_5s_rate'])} "
            f"2s跳出{_p(r['skip_2s_rate'])} 收藏率{_p(fr)} 涨粉{r['followers_gained'] or 0} "
            f"弹幕{r['danmaku'] if r['danmaku'] is not None else '—'} 脱粉{r['unfollows'] if r['unfollows'] is not None else '—'} "
            f"不感兴趣{_p(r['dislike_rate'])} 粉丝播放占比{_p(r['follower_play_ratio'])} "
            f"发布{str(r['publish_time'] or '')[:16]}"
        )
    vids = [dict(r) for r in rows]
    views = [v["views"] or 0 for v in vids]
    mean = sum(views) / len(views) if views else 0
    stats = {
        "count": len(vids),
        "mean_views": round(mean),
        "viral_line": round(mean * 3),
        "total_favs": sum(v["favorites"] or 0 for v in vids),
        "total_followers": sum(v["followers_gained"] or 0 for v in vids),
    }
    return "\n".join(lines), stats


def _p(x) -> str:
    return f"{x * 100:.1f}%" if isinstance(x, (int, float)) else "—"


def _fallback_report(stats: dict, lines: str) -> str:
    """降级版:全真数据 + 骨架,无 AI 解读"""
    return f"""# 爆款拆解报告(统计版·LLM 未接入)

> 当前为规则降级版:以下数字全部真实;AI 解读章节在配置 LLM_API_KEY 后自动启用。

## 0. 数据底座
- 作品 {stats['count']} 条 · 均值播放 {stats['mean_views']:,} · 爆款线(3×均值){stats['viral_line']:,}
- 累计收藏 {stats['total_favs']:,} · 累计涨粉 {stats['total_followers']:,}

## 作品清单(按播放降序)
{lines}

{chr(10).join('## ' + s for s in SECTIONS)}

> 以上章节待 LLM 版填充。
"""


def _parse_templates(md: str) -> list[dict]:
    """解析报告末尾 ```json {...}``` 模板块"""
    m = re.search(r"```json\s*(\{.*?\})\s*```", md, re.S) or re.search(
        r"```\s*(\{.*?" r'"templates".*?\})\s*' + "```", md, re.S
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
        out = []
        for t in data.get("templates", [])[:3]:
            if not isinstance(t, dict) or not t.get("name"):
                continue
            stats = t.get("stats") or {}
            out.append(
                {
                    "id": str(t.get("id") or f"T{len(out) + 1}")[:8],
                    "name": str(t["name"])[:24],
                    "hook": str(t.get("hook") or "")[:120],
                    "structure_md": str(t.get("structure") or "")[:300],
                    "accent": t.get("accent") if t.get("accent") in ("develop", "preview", "ship") else "develop",
                    "stats": {
                        "videos": int(stats.get("videos") or 0),
                        "avgViews": int(stats.get("avgViews") or 0),
                        "avgCompletion": float(stats.get("avgCompletion") or 0),
                        "avg5s": float(stats.get("avg5s") or 0),
                        "avgFavRate": float(stats.get("avgFavRate") or 0),
                    },
                }
            )
        return out
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


def generate() -> dict:
    """生成拆解报告并存库;返回 {report_id, engine, templates}"""
    db.init_db()
    lines, stats = _video_lines()
    now = datetime.now().isoformat(timespec="seconds")

    user_prompt = (
        f"创作者抖音账号数据({now[:10]} 快照):\n"
        f"均值播放 {stats['mean_views']:,},爆款线 3×均值 = {stats['viral_line']:,}\n"
        f"{lines}\n\n请基于以上真实数据输出爆款拆解报告,Markdown 固定章节:\n"
        + "\n".join(f"## {s}" for s in SECTIONS)
        + "\n\n每章节必须结合上面数据的真实规律给结论;数字只引用给定数据。\n"
        + JSON_INSTRUCTION
    )

    md = llm.chat(SYSTEM, user_prompt, temperature=0.4)
    if md and "##" in md:
        engine = "llm"
    else:
        engine = "rule"
        md = _fallback_report(stats, lines)

    c = db.conn()
    cur = c.execute(
        "INSERT INTO reports(type, title, content_md, engine, created_at) VALUES(?,?,?,?,?)",
        ("breakdown", f"爆款拆解 · {now[:16].replace('T', ' ')}", md, engine, now),
    )
    report_id = cur.lastrowid

    # 模板沉淀:LLM 版替换式重建(报告是模板的唯一来源);规则版不动旧模板
    saved = []
    if engine == "llm":
        saved = _parse_templates(md)
        if saved:
            c.execute("DELETE FROM templates")
            for t in saved:
                c.execute(
                    "INSERT OR REPLACE INTO templates(id,name,hook,structure_md,accent,report_id,stats_json,created_at)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (
                        t["id"], t["name"], t["hook"], t["structure_md"], t["accent"],
                        report_id, json.dumps(t["stats"], ensure_ascii=False), now,
                    ),
                )
    c.commit()
    return {"report_id": report_id, "engine": engine, "templates": len(saved)}
