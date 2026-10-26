"""ingest 编排:外部采集源 → 统一库 + 审计 + 健康状态机

两类动作:
  ingest_douyin()      只读复制 douyin-mcp 库 → platform.db(秒级)
  run_douyin_sync()    先驱动 douyin-mcp sync+details(浏览器自动化,分钟级),再 ingest
                       details 按 next_action 游标自动续跑(≤4 轮),尽量补全详情字段
"""
import json
import re
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from . import db
from .adapters import douyin_mcp
from .config import BJ_TZ, DOUYIN_MCP_DIR, DOUYIN_MCP_PY, SOURCE_INTERVALS

SOURCE_ID = "douyin_self"


def _cli(args: list[str], timeout_sec: int = 900, bg: bool = False) -> str:
    """调用 douyin-mcp CLI,返回 stdout。
    bg=True 追加 background_first:无头后台抓取,不弹浏览器;
    仅当触发验证/需重新扫码时,工具才会要求可见浏览器(人工兜底)。"""
    if bg:
        args = [*args, "--mode", "background_first"]
    p = subprocess.run(
        [str(DOUYIN_MCP_PY), "-m", "douyin_creator_mcp.cli", *args],
        cwd=str(DOUYIN_MCP_DIR),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=True,
    )
    return p.stdout or ""


def _next_cursor(out: str) -> int | None:
    """从 details 输出解析 next_action.continue 游标(容忍非纯 JSON 输出)"""
    if '"continue"' not in out:
        return None
    try:
        na = json.loads(out).get("next_action") or {}
        if na.get("type") == "continue" and na.get("cursor") is not None:
            return int(na["cursor"])
    except json.JSONDecodeError:
        pass
    m = re.search(r'"cursor"\s*:\s*(\d+)', out)
    return int(m.group(1)) if m else None


def ensure_source() -> None:
    db.conn().execute(
        """INSERT INTO sources(id, name, kind, interval_minutes, updated_at)
           VALUES(?, '抖音自数据(douyin-mcp)', 'douyin_self', ?, ?)
           ON CONFLICT(id) DO NOTHING""",
        (SOURCE_ID, SOURCE_INTERVALS["douyin_self"], db.now_iso()),
    )
    db.conn().commit()


def ingest_douyin() -> dict:
    """拉取映射 + 落库 + 审计。返回 {found, new}"""
    ensure_source()
    with db.fetch_run(SOURCE_ID) as run_id:
        videos, snapshots, daily = douyin_mcp.pull()
        new_count = 0
        for v in videos:
            if db.upsert_video(v):
                new_count += 1
        for s in snapshots:
            db.insert_snapshot(s, s["captured_at"], s["date"])
        for d in daily:
            db.insert_daily(d)
        # 推进 next_fetch_at(表驱动调度)
        nxt = datetime.now(tz=ZoneInfo(BJ_TZ)) + timedelta(minutes=SOURCE_INTERVALS["douyin_self"])
        db.conn().execute(
            "UPDATE sources SET next_fetch_at=?, cursor_json=? WHERE id=?",
            (nxt.isoformat(timespec="seconds"), f'{{"last_run": {run_id}}}', SOURCE_ID),
        )
        db.conn().commit()
        return {"found": len(videos), "new": new_count}


def run_douyin_sync(timeout_sec: int = 900) -> dict:
    """驱动 douyin-mcp 全量同步(subprocess)后执行 ingest。
    浏览器自动化较慢(约 2-5 分钟),供 API 异步线程 / 调度 tick 调用。
    details 按 next_action 游标自动续跑,直到完成或 4 轮上限。"""
    _cli(["sync"], timeout_sec, bg=True)
    cursor: int | None = None
    for _ in range(4):
        args = ["details"] + ([] if cursor is None else ["--cursor", str(cursor)])
        cursor = _next_cursor(_cli(args, timeout_sec, bg=True))
        if cursor is None:
            break
    return ingest_douyin()
