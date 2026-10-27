"""账号证据知识库:GLM 直读模式(无向量/无 agent)。

日更账号证据价值在「新」不在「似」——选材规则确定,SQL 聚合,单次喂给 GLM 全读:
  L1 近30天自有作品(脚本节选+真实战绩,发布时间锚定,自动覆盖更新)
  L1' 对标爆款脚本(全部,数量有限)
  L2 最新报告结论(只取最近2份,旧结论天然被新报告替代)

升级路径:脚本积累到数百条时,把 gather_evidence() 换成向量检索或
agent 浏览即可,调用方(precheck)接口不变。
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from . import db
from .config import BJ_TZ

_TZ = ZoneInfo(BJ_TZ)
OWN_WINDOW_DAYS = 30
REPORT_KEEP = 2
BENCH_LIMIT = 8
SCRIPT_EXCERPT = 320


def _now() -> datetime:
    return datetime.now(_TZ)


def _fmt(v, suffix: str = "") -> str:
    if v is None:
        return "?"
    if isinstance(v, float):
        return f"{v:.3g}{suffix}"
    return f"{v}{suffix}"


def _age_days(ts: str) -> int:
    try:
        return max((_now() - datetime.fromisoformat(ts)).days, 0)
    except Exception:
        return 0


def gather_evidence() -> list[dict]:
    """聚合证据文档。返回 [{kind,title,text,age_days}],按新→旧。"""
    c = db.conn()
    docs: list[dict] = []

    # L1 自有:近30天有脚本配对的作品(真实战绩是核心反馈)
    try:
        rows = c.execute(
            """SELECT vs.project, vs.title AS stitle, vs.text, vs.video_id,
                      v.title, v.publish_time, v.views, v.likes, v.comments,
                      v.completion_5s_rate, v.skip_2s_rate, v.completion_rate
               FROM video_scripts vs LEFT JOIN videos v ON vs.video_id = v.video_id
               ORDER BY v.publish_time DESC"""
        ).fetchall()
        for r in rows:
            paired = bool(r["video_id"])
            pub = (r["publish_time"] or "")[:19] if paired else ""
            if pub and _age_days(pub) > OWN_WINDOW_DAYS:
                continue
            title = r["title"] or r["stitle"] or r["project"] or "自有作品"
            if paired and r["views"] is not None:
                metrics = (
                    f"播放{_fmt(r['views'])} 赞{_fmt(r['likes'])} 评论{_fmt(r['comments'])} "
                    f"5s完播{_fmt(r['completion_5s_rate'], '%')} 2s跳出{_fmt(r['skip_2s_rate'], '%')} "
                    f"完播{_fmt(r['completion_rate'], '%')}"
                )
                text = f"《{title}》发布{pub[:10]} 战绩:{metrics} 脚本:{(r['text'] or '')[:SCRIPT_EXCERPT]}"
            else:
                text = f"《{title}》(尚未配对抖音作品数据,只有脚本) 脚本:{(r['text'] or '')[:SCRIPT_EXCERPT]}"
            docs.append({
                "kind": "own_video",
                "title": title if paired else f"{title}·未配对",
                "text": text,
                "age_days": _age_days(pub) if pub else 7,
            })
    except Exception:
        pass

    # L1' 对标爆款脚本:仅非产线来源(产线脚本一律是自有,不得混入)
    try:
        rows = c.execute(
            "SELECT project, title, text, created_at FROM video_scripts "
            "WHERE (video_id IS NULL OR video_id = '') AND source != 'aivideo_line' "
            "ORDER BY created_at DESC LIMIT ?",
            (BENCH_LIMIT,),
        ).fetchall()
        for r in rows:
            docs.append({
                "kind": "bench",
                "title": r["title"] or r["project"] or "爆款脚本",
                "text": f"对标爆款《{r['title'] or r['project']}》脚本:{(r['text'] or '')[:SCRIPT_EXCERPT]}",
                "age_days": _age_days((r["created_at"] or "")[:19]),
            })
    except Exception:
        pass

    # L2 最新报告结论(旧报告不进——新结论天然替代旧结论)
    try:
        reports = c.execute(
            "SELECT id, title, content_md, created_at FROM reports ORDER BY id DESC LIMIT ?",
            (REPORT_KEEP,),
        ).fetchall()
        for rep in reports:
            md = rep["content_md"] or ""
            # 取核心结论段:含「结论/建议/模板/铁律」关键词的段落,或前1200字
            paras = [p.strip() for p in md.split("\n\n") if len(p.strip()) > 80]
            picked = [p for p in paras if any(k in p for k in ("结论", "建议", "模板", "铁律", "应该", "策略"))]
            body = "\n".join(picked[:6]) if picked else md[:1200]
            docs.append({
                "kind": "report",
                "title": f"报告《{rep['title']}》核心结论",
                "text": body[:1600],
                "age_days": _age_days((rep["created_at"] or "")[:19]),
            })
    except Exception:
        pass

    docs.sort(key=lambda d: d["age_days"])
    return docs


def stats() -> dict:
    """知识库规模一览(前端/调试用)。"""
    try:
        ev = gather_evidence()
        return {
            "own": sum(1 for e in ev if e["kind"] == "own_video"),
            "bench": sum(1 for e in ev if e["kind"] == "bench"),
            "reports": sum(1 for e in ev if e["kind"] == "report"),
            "total": len(ev),
        }
    except Exception as e:
        return {"error": str(e)[:120]}
