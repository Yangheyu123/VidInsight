"""创作简报桥:中台 → 产线(D:\\aivideo\\VIDEINSIGHT_BRIEF.md)

把最新拆解报告(第2/3/7/8章)+ 模板库 + 已采用选题,蒸馏成产线 agent 可直接执行的创作简报。
产线用法(AGENTS.md 加一行):写新脚本前必读 VIDEINSIGHT_BRIEF.md。
触发:报告生成后自动刷新(tick)+ POST /api/brief/export 手动。
"""
import re
from datetime import datetime
from pathlib import Path

from . import db

BRIEF_PATH = Path(r"D:\aivideo\VIDEINSIGHT_BRIEF.md")


def _sections(md: str) -> dict[str, str]:
    """按 ## 标题切章节"""
    parts = re.split(r"\n(?=## )", md)
    out: dict[str, str] = {}
    for p in parts[1:]:
        title = p.split("\n", 1)[0].lstrip("# ").strip()
        out[title] = p
    return out


def _pick(sections: dict[str, str], keyword: str, limit: int = 2600) -> str:
    for k, v in sections.items():
        if keyword in k:
            return v[:limit].rstrip()
    return ""


def build_brief() -> dict:
    """生成创作简报 → 写入产线根目录"""
    c = db.conn()
    report_row = c.execute(
        "SELECT id, title, content_md, engine, created_at FROM reports "
        "WHERE type='breakdown' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not report_row:
        return {"error": "还没有拆解报告,先生成一份"}

    secs = _sections(report_row["content_md"])

    # 数据态势:作品均值/爆款线/互动三率
    own = c.execute(
        "SELECT COUNT(*) n, AVG(views) mv, AVG(completion_rate) mc, AVG(likes + comments + favorites) * 1.0 / NULLIF(AVG(NULLIF(views, 0)), 0) mi FROM videos WHERE is_own=1"
    ).fetchone()
    bench = c.execute(
        "SELECT COUNT(*) n, AVG(views) mv FROM videos WHERE is_own=0"
    ).fetchone()
    viral = c.execute(
        "SELECT COUNT(*) n FROM videos v WHERE v.is_own=1 AND v.views >= 3 * (SELECT AVG(views) FROM videos WHERE is_own=1)"
    ).fetchone()

    templates = c.execute("SELECT id, name, hook FROM templates ORDER BY id").fetchall()
    adopted = c.execute(
        "SELECT title, substr(suggestion,1,80) s FROM materials WHERE status='已用' ORDER BY score DESC LIMIT 8"
    ).fetchall()
    ready = c.execute(
        "SELECT title, score FROM materials WHERE status='待用' AND category != '爆款脚本' "
        "ORDER BY score DESC LIMIT 6"
    ).fetchall()

    lines = [
        f"# VidInsight 创作简报(自动生成 {datetime.now().strftime('%Y-%m-%d %H:%M')})",
        f"> 基于报告 #{report_row['id']}《{report_row['title']}》({report_row['engine']})。"
        "产线 agent 写新脚本前必读本文件;简报由中台每日自动刷新,勿手改。",
        "",
        "## 0. 数据态势(真实数字)",
        f"- 自有 {own['n']} 条:均播放 {own['mv'] or 0:,.0f} · 均完播 {(own['mc'] or 0) * 100:.1f}% · 互动率 {(own['mi'] or 0) * 100:.2f}%(赞+评+藏/播)",
        f"- 对标 {bench['n'] or 0} 条:均播放 {(bench['mv'] or 0):,.0f} · 自有爆款 {viral['n']} 条",
    ]
    if templates:
        lines += ["", "## 1. 优先模板(胜率排序)"]
        lines += [f"- **{t['name']}**: {t['hook']}" for t in templates]
    for label, kw in [
        ("## 2. 标题模板(直接套用)", "标题模板"),
        ("## 3. 钩子模板(前 3 秒开口)", "钩子模板"),
        ("## 4. 脚本节奏", "脚本节奏"),
        ("## 5. 避坑清单", "避坑"),
    ]:
        body = _pick(secs, kw)
        if body:
            lines += ["", body]
    vs = _pick(secs, "我的脚本", limit=3200)
    if vs:
        lines += ["", vs]
    if adopted:
        lines += ["", "## 已采用选题(优先做)"]
        lines += [f"- 《{a['title']}》 → {a['s']}" for a in adopted]
    if ready:
        lines += ["", "## 待用高分选题(素材库备选)"]
        lines += [f"- {r['score']:.1f} 分 《{r['title']}》" for r in ready]
    lines += [
        "",
        "---",
        "执行对齐(与产线 METHODOLOGY 一致,冲突以产线为准):",
        "- 开场具象(人物/年份/动作/具体物+反直觉结论),拒绝纯提问/纯抽象对仗(高置信线索:提问式开场 5s 完播居账号尾部)",
        "- 承接 5-10s 反向冲击,每 12-15s 一次小冲突;钩子段快思辨段慢",
        "- 片长 45-55s(上限 60);字数密度 ≤4.5 字/s",
        "- 结尾:金句(可整条反色高亮,给收藏)+ 评论钩子(具体可答)停到片尾",
        "- 标题从上方模板取结构,用自己的词填;选题优先「已采用」",
        "- 数据结论均为高置信线索,非固定归因(诊断协议:回看具体内容分辨)",
        "",
    ]

    content = "\n".join(lines)
    try:
        BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
        BRIEF_PATH.write_text(content, encoding="utf-8")
    except OSError as e:
        return {"error": f"写入失败: {e}", "path": str(BRIEF_PATH)}
    return {"ok": True, "path": str(BRIEF_PATH), "chars": len(content)}


PROMPT_WRAPPER = """你是我的短视频编剧(赛道:思辨哲学,受众18-23岁男性为主)。
下面是「创作简报」——由我的数据中台基于真实账号数据+对标爆款自动生成。
其中数据结论是**高置信线索而非铁律**(同样指标可能源于题材/钩子/限流,需回看内容分辨);
但开场具象、节奏、密度三条硬约束必须服从。

{content}

—— 执行硬约束(与产线 METHODOLOGY 对齐,冲突时以产线为准) ——
1. 片长 45-55 秒(上限 60 秒),不是 60-90
2. 密度红线:全片字数 ≤ 4.5 字/秒,单卡 ≤ 4.5 × 可见秒数;超线=精简文案
3. 节奏:前 3 秒具象开场(具体名字/数字/动作+反直觉结论);承接 5-10s 反向冲击(禁引用与说理);每 12-15s 一次小冲突;钩子段快(~5字/s)、思辨段慢(~3.5字/s)
4. 结尾:金句给收藏(写成可整条高亮的反色金句)+ 评论钩子(具体、可答、有吐槽空间的提问)停到片尾

现在请基于以上简报,为我写一条新视频的完整脚本(开场钩子→承接→中段冲突→思辨→结尾金句+评论钩子)。"""


def build_prompt() -> str:
    """包装成可直接整段粘贴给任意 AI(ChatGPT/Kimi/豆包/其它 agent)的完整提示词"""
    if not BRIEF_PATH.exists():
        build_brief()
    try:
        content = BRIEF_PATH.read_text(encoding="utf-8")
    except OSError:
        content = ""
    return PROMPT_WRAPPER.replace("{content}", content)
