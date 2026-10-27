"""发布登记:agent 发布回调 → 终稿+发布时间入档 → 与预检初稿配对。

流程:预检存初稿(precheck_archive) → agent 发布后回调 /api/publish(带终稿)
→ 按内容相似度自动配对初稿 → 数据回流时即可画"发布后N小时"曲线。

零手动操作:用户唯一动作是平时照常预检;回调由 agent 一行 HTTP 完成。
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from . import db
from .config import BJ_TZ


def _now() -> str:
    return datetime.now(ZoneInfo(BJ_TZ)).isoformat(timespec="seconds")


def init_table() -> None:
    c = db.conn()
    c.execute(
        """CREATE TABLE IF NOT EXISTS publish_logs(
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             title TEXT NOT NULL,
             final_script TEXT,
             published_at TEXT,
             draft TEXT,                -- 配对到的预检初稿
             draft_score INTEGER,       -- 初稿预检得分
             final_chars INTEGER,
             deliver_path TEXT,         -- 产线成片路径
             video_id TEXT,             -- 数据回流后回填
             created_at TEXT NOT NULL)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS precheck_archive(
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             draft TEXT NOT NULL,
             score INTEGER,
             verdict TEXT,
             items_json TEXT,
             rewrite TEXT,
             created_at TEXT NOT NULL)"""
    )
    c.commit()


def _similarity(a: str, b: str) -> float:
    """字符 bigram 相似度(轻量,无依赖,中文友好)。"""
    if not a or not b:
        return 0.0
    a2, b2 = a[:600], b[:600]
    ga = {a2[i : i + 2] for i in range(len(a2) - 1)}
    gb = {b2[i : i + 2] for i in range(len(b2) - 1)}
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def archive_precheck(draft: str, result: dict) -> int:
    """预检时自动存档初稿+体检单。返回 archive_id。"""
    init_table()
    c = db.conn()
    cur = c.execute(
        "INSERT INTO precheck_archive(draft, score, verdict, items_json, rewrite, created_at) VALUES(?,?,?,?,?,?)",
        (
            draft,
            result.get("score"),
            result.get("verdict"),
            json.dumps(result.get("items", []), ensure_ascii=False),
            result.get("rewrite", ""),
            _now(),
        ),
    )
    c.commit()
    return cur.lastrowid


def log_publish(title: str, final_script: str, published_at: str | None = None) -> dict:
    """agent 回调:登记发布。自动配对最近一条相似度≥0.35的初稿。"""
    init_table()
    published_at = published_at or _now()
    c = db.conn()

    draft = draft_score = None
    try:
        rows = c.execute(
            "SELECT id, draft, score FROM precheck_archive ORDER BY id DESC LIMIT 30"
        ).fetchall()
        best, best_sim = None, 0.0
        for r in rows:
            sim = _similarity(r["draft"], final_script or title)
            if sim > best_sim:
                best, best_sim = r, sim
        if best and best_sim >= 0.35:
            draft, draft_score = best["draft"], best["score"]
    except Exception:
        pass

    cur = c.execute(
        "INSERT INTO publish_logs(title, final_script, published_at, draft, draft_score, final_chars, created_at)"
        " VALUES(?,?,?,?,?,?,?)",
        (title, final_script, published_at, draft, draft_score, len(final_script or ""), _now()),
    )
    c.commit()
    return {
        "ok": True,
        "id": cur.lastrowid,
        "paired_draft": bool(draft),
        "draft_score": draft_score,
    }


def attach_video(publish_id: int, video_id: str) -> dict:
    """数据回流时回填抖音 video_id(按标题匹配后调用)。"""
    init_table()
    db.conn().execute("UPDATE publish_logs SET video_id=? WHERE id=?", (video_id, publish_id))
    db.conn().commit()
    return {"ok": True}


def recent(limit: int = 20) -> list[dict]:
    init_table()
    rows = db.conn().execute(
        "SELECT id, title, published_at, draft_score, final_chars, draft,"
        " video_id, final_script, deliver_path FROM publish_logs ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "published_at": r["published_at"],
            "draft_score": r["draft_score"],
            "final_chars": r["final_chars"],
            "paired": bool(r["draft"]),
            "video_id": r["video_id"],
            "has_final": bool(r["final_script"]),
            "has_draft": bool(r["draft"]),
            "deliver_path": r["deliver_path"],
        }
        for r in rows
    ]
