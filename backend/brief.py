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
        f"# VidInsight 创作简报(自动生成 {datetime.now().strftime('%Y-%m-%d %H:%f')[:16]})",
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
        "执行规则:新脚本必须满足——开场具象(人物/年份/动作,拒绝纯抽象对仗);"
        "每 30 秒一个钩子回拉;结尾给收藏理由;标题从上方模板取结构,用自己的词填。",
        "",
    ]

    content = "\n".join(lines)
    try:
        BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
        BRIEF_PATH.write_text(content, encoding="utf-8")
    except OSError as e:
        return {"error": f"写入失败: {e}", "path": str(BRIEF_PATH)}
    return {"ok": True, "path": str(BRIEF_PATH), "chars": len(content)}


if __name__ == "__main__":
    print(build_brief())
