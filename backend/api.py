"""FastAPI:统一库 → 前端 DataSource 契约

端点与 frontend/src/types.ts DataSource 一一对应:
  GET  /api/videos        → Video[]
  GET  /api/daily?days=30 → DailyStat[](基于 snapshots 逐日聚合)
  GET  /api/templates     → Template[](P2 报告沉淀前为空)
  GET  /api/sync-status   → SyncStatus + 调度/健康信息
  POST /api/sync          → 异步触发 douyin-mcp 全量同步 + ingest
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import db, ingest, llm, materials, radar, report, scripts_ingest
from .config import API_HOST, API_PORT, BJ_TZ

app = FastAPI(title="抖音运营中台 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_sync_lock = threading.Lock()
_sync_state = {"running": False, "last_result": None, "error": None}

# ---- 通用异步任务注册表(报告/素材/雷达,前端轮询 running 状态) ----
_jobs: dict[str, dict] = {
    "report": {"running": False}, "materials": {"running": False},
    "radar": {"running": False}, "scripts": {"running": False},
}
_jobs_lock = threading.Lock()


def _run_job(name: str, fn, *args, **kwargs) -> dict:
    """异步执行长任务(报告/素材抓取/雷达采集),状态写 _jobs"""
    with _jobs_lock:
        if _jobs[name]["running"]:
            return {"started": False, "reason": "任务进行中"}
        _jobs[name]["running"] = True

    def _worker():
        try:
            _jobs[name]["result"] = fn(*args, **kwargs)
            _jobs[name]["error"] = None
        except Exception as e:  # noqa: BLE001 - 状态回传
            _jobs[name]["error"] = str(e)[:300]
        finally:
            _jobs[name]["running"] = False
          # 注:锁释放放在 finally 之外避免与读取竞态(仅 running 标志由锁保护)

    threading.Thread(target=_worker, daemon=True).start()
    return {"started": True}


@app.get("/api/jobs")
def jobs() -> dict:
    with _jobs_lock:
        return {
            k: {
                "running": v["running"],
                "error": v.get("error"),
                "result": v.get("result"),
                "progress": v.get("progress"),
            }
            for k, v in _jobs.items()
        }


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    ingest.ensure_source()


@app.get("/api/videos")
def videos(scope: str = "own") -> list[dict]:
    """scope: own=自有(抖音) / bench=对标(B站/YouTube) / all"""
    where = {"own": "is_own=1", "bench": "is_own=0", "all": "1=1"}.get(scope, "is_own=1")
    rows = db.conn().execute(
        f"SELECT * FROM videos WHERE {where} ORDER BY publish_time DESC"
    ).fetchall()
    # snake_case → 前端 camelCase 契约(frontend/src/types.ts)
    keymap = {
        "video_id": "videoId", "account_id": "accountId", "publish_time": "publishTime",
        "duration_sec": "durationSec", "completion_rate": "completionRate",
        "avg_watch_sec": "avgWatchSec", "completion_5s_rate": "completion5sRate",
        "skip_2s_rate": "skip2sRate", "followers_gained": "followersGained",
        "follower_play_ratio": "followerPlayRatio", "avg_play_ratio": "avgPlayRatio",
        "dislike_rate": "dislikeRate", "like_rate": "likeRate",
        "comment_rate": "commentRate", "share_rate": "shareRate",
        "favorite_rate": "favoriteRate", "cover_url": "coverUrl",
        "collected_at": "collectedAt",
    }
    out = []
    for r in rows:
        d = {keymap.get(k, k): v for k, v in dict(r).items()}
        d["isOwn"] = bool(d.pop("is_own", 1))
        d["templateId"] = d.pop("template_id", None)
        out.append(d)
    return out


@app.get("/api/daily")
def daily(days: int = 30) -> list[dict]:
    """天级粒度聚合(口径优先级):
    1) video_daily 表:douyin-mcp 的 metric_date 日累计 → 相邻日差值(精确)
    2) snapshots 表兜底:相邻抓取的正增量
    完播率取当日快照均值(比率非累计,不能做差)"""
    since = (datetime.now(tz=ZoneInfo(BJ_TZ)) - timedelta(days=days)).strftime("%Y-%m-%d")

    # ---- 播放/涨粉:video_daily 优先 ----
    plays: dict[str, int] = {}
    gained: dict[str, int] = {}
    vd_rows = db.conn().execute(
        "SELECT video_id, date, views, followers_gained FROM video_daily WHERE date>=? "
        "ORDER BY video_id, date",
        (since,),
    ).fetchall()
    prev: dict[str, tuple] = {}
    for r in vd_rows:
        p = prev.get(r["video_id"])
        if p and r["views"] is not None and p[0] is not None:
            plays[r["date"]] = plays.get(r["date"], 0) + max(0, r["views"] - p[0])
            if r["followers_gained"] is not None and p[1] is not None:
                gained[r["date"]] = gained.get(r["date"], 0) + max(0, r["followers_gained"] - p[1])
        prev[r["video_id"]] = (r["views"], r["followers_gained"])

    if not vd_rows:
        # 兜底:快照差值
        rows = db.conn().execute(
            "SELECT video_id, date, captured_at, views, followers_gained FROM snapshots "
            "WHERE date>=? ORDER BY video_id, captured_at",
            (since,),
        ).fetchall()
        prev = {}
        for r in rows:
            p = prev.get(r["video_id"])
            if p and r["views"] is not None and p[0] is not None:
                plays[r["date"]] = plays.get(r["date"], 0) + max(0, r["views"] - p[0])
                if r["followers_gained"] is not None and p[1] is not None:
                    gained[r["date"]] = gained.get(r["date"], 0) + max(0, r["followers_gained"] - p[1])
            prev[r["video_id"]] = (r["views"], r["followers_gained"])

    # ---- 完播率:当日快照均值 ----
    comps: dict[str, list] = {}
    for r in db.conn().execute(
        "SELECT date, completion_rate FROM snapshots WHERE date>=? AND completion_rate IS NOT NULL",
        (since,),
    ):
        comps.setdefault(r["date"], []).append(r["completion_rate"])

    out = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now(tz=ZoneInfo(BJ_TZ)) - timedelta(days=i)).strftime("%Y-%m-%d")
        c = comps.get(d)
        out.append(
            {
                "date": d,
                "plays": plays.get(d, 0),
                "newFollowers": gained.get(d, 0),
                "avgCompletion": (sum(c) / len(c)) if c else None,
            }
        )
    return out


@app.get("/api/videos/{video_id}/daily")
def video_daily(video_id: str) -> list[dict]:
    """单作品天级累计曲线(抽屉趋势图用):video_daily 累计值 + 当日快照的比率"""
    vd = db.conn().execute(
        "SELECT * FROM video_daily WHERE video_id=? ORDER BY date", (video_id,)
    ).fetchall()
    snap: dict[str, sqlite3.Row] = {}
    for r in db.conn().execute(
        "SELECT * FROM snapshots WHERE video_id=? AND skip_2s_rate IS NOT NULL ORDER BY captured_at",
        (video_id,),
    ):
        snap[r["date"]] = r
    out = []
    for r in vd:
        s = snap.get(r["date"])
        out.append(
            {
                "date": r["date"],
                "views": r["views"], "likes": r["likes"], "favorites": r["favorites"],
                "followersGained": r["followers_gained"],
                "completionRate": s["completion_rate"] if s else None,
                "skip2sRate": s["skip_2s_rate"] if s else None,
            }
        )
    return out


@app.get("/api/templates")
def templates() -> list[dict]:
    """模板库:由 LLM 拆解报告沉淀(reports → templates)"""
    rows = db.conn().execute("SELECT * FROM templates ORDER BY id").fetchall()
    out = []
    for r in rows:
        try:
            stats = json.loads(r["stats_json"] or "{}")
        except json.JSONDecodeError:
            stats = {}
        out.append(
            {
                "id": r["id"],
                "name": r["name"],
                "hook": r["hook"] or "",
                "structure": r["structure_md"] or "",
                "accent": r["accent"],
                "stats": {
                    "videos": stats.get("videos", 0),
                    "avgViews": stats.get("avgViews", 0),
                    "avgCompletion": stats.get("avgCompletion", 0),
                    "avg5s": stats.get("avg5s", 0),
                    "avgFavRate": stats.get("avgFavRate", 0),
                },
            }
        )
    return out


# ---------------- P2 报告中心 ----------------

@app.get("/api/reports")
def reports() -> list[dict]:
    rows = db.conn().execute(
        "SELECT id, type, title, engine, created_at FROM reports ORDER BY id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


@app.get("/api/reports/{rid}")
def report_detail(rid: int) -> dict:
    r = db.conn().execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()
    if not r:
        return {"error": "not found"}
    return dict(r)


@app.delete("/api/reports/{rid}")
def report_delete(rid: int) -> dict:
    db.conn().execute("DELETE FROM reports WHERE id=?", (rid,))
    db.conn().commit()
    return {"ok": True}


class ReportBody(BaseModel):
    scope: str = "own"  # own=自有数据 / bench=对标数据


@app.post("/api/report/generate")
def report_generate(body: ReportBody | None = None) -> dict:
    scope = (body.scope if body else "own") or "own"
    return _run_job("report", report.generate, scope=scope)


# ---------------- 手动投喂对标(抖音等外部爆款数据) ----------------

class ManualVideo(BaseModel):
    title: str
    views: int
    likes: int = 0
    favorites: int = 0
    comments: int = 0
    durationSec: int = 0
    url: str = ""
    platform: str = "douyin"  # douyin / bilibili / youtube / other
    accountId: str = ""


@app.post("/api/videos/manual")
def video_manual(body: ManualVideo) -> dict:
    """手动录入对标爆款(别人账号的公开四项数据),进统一库走同一报告引擎"""
    import hashlib

    vid = "manual-" + hashlib.sha1(f"{body.platform}|{body.title}".encode()).hexdigest()[:16]
    v = {
        "platform": body.platform, "video_id": vid, "account_id": body.accountId or None,
        "url": body.url or None, "title": body.title.strip()[:200],
        "publish_time": datetime.now(tz=ZoneInfo(BJ_TZ)).isoformat(timespec="seconds"),
        "duration_sec": body.durationSec, "views": body.views, "likes": body.likes,
        "favorites": body.favorites, "comments": body.comments, "shares": None,
        "completion_rate": None, "completion_5s_rate": None, "skip_2s_rate": None,
        "avg_watch_sec": None, "exposure": None, "followers_gained": None,
        "danmaku": None, "unfollows": None, "follower_play_ratio": None,
        "avg_play_ratio": None, "dislike_rate": None, "like_rate": None,
        "comment_rate": None, "share_rate": None, "favorite_rate": None,
        "cover_url": None, "status": "手动录入", "is_own": 0, "template_id": None,
        "collected_at": datetime.now(tz=ZoneInfo(BJ_TZ)).isoformat(timespec="seconds"),
    }
    is_new = db.upsert_video(v)
    db.conn().commit()
    return {"ok": True, "new": is_new, "video_id": vid}


# ---------------- P3 素材库 ----------------

@app.get("/api/materials")
def materials_list(status: str = "", category: str = "", page: int = 1, page_size: int = 30) -> dict:
    """分页返回:items + total/pages;status/category 可选过滤"""
    where, args = "1=1", []
    if status:
        where += " AND status=?"
        args.append(status)
    if category:
        where += " AND category=?"
        args.append(category)
    total = db.conn().execute(
        f"SELECT COUNT(*) FROM materials WHERE {where}", args
    ).fetchone()[0]
    pages = max(1, -(-total // page_size))
    page = max(1, min(page, pages))
    rows = db.conn().execute(
        f"SELECT * FROM materials WHERE {where} ORDER BY score DESC, id DESC LIMIT ? OFFSET ?",
        [*args, page_size, (page - 1) * page_size],
    ).fetchall()
    return {"items": [dict(r) for r in rows], "total": total, "page": page, "pages": pages, "page_size": page_size}


@app.post("/api/materials/fetch")
def materials_fetch() -> dict:
    return _run_job("materials", materials.fetch_and_score)


@app.post("/api/materials/rescore")
def materials_rescore() -> dict:
    """按最新创作者画像重打「待用」素材分"""
    return _run_job("materials", materials.rescore_pending)


class MaterialPatch(BaseModel):
    status: str  # 待用 / 已用 / 丢弃


@app.patch("/api/materials/{mid}")
def material_patch(mid: int, patch: MaterialPatch) -> dict:
    if patch.status not in ("待用", "已用", "丢弃"):
        return {"error": "非法状态"}
    db.conn().execute("UPDATE materials SET status=? WHERE id=?", (patch.status, mid))
    db.conn().commit()
    return {"ok": True}


# ---------------- P4 爆款雷达 ----------------

class RadarBody(BaseModel):
    mode: str  # channel / search
    platform: str = "bilibili"  # bilibili / youtube(搜索模式必填)
    url: str = ""
    keyword: str = ""
    limit: int = 20


@app.post("/api/radar/collect")
def radar_collect(body: RadarBody) -> dict:
    def _run():
        return radar.collect_radar(
            mode=body.mode, url=body.url, keyword=body.keyword,
            platform=body.platform, limit=body.limit,
            progress=lambda done, total, failed: _jobs["radar"].__setitem__(
                "progress", {"done": done, "total": total, "failed": failed}
            ),
        )

    return _run_job("radar", _run)


# ---------------- 爆款脚本管线(对标逐字稿 → 素材库) ----------------

@app.post("/api/scripts/ingest")
def scripts_ingest_api() -> dict:
    """对标爆款 → 音频(临时)→ 转写 → LLM 提炼钩子/金句 → 素材库「爆款脚本」"""
    return _run_job("scripts", scripts_ingest.ingest_bench_scripts, limit=3)


@app.post("/api/scripts/own")
def scripts_own_api() -> dict:
    """自有脚本:本地产线(D:\\aivideo)script.ts 逐字剧本提取 → video_scripts"""
    from . import own_scripts

    return own_scripts.harvest_own_scripts()


@app.post("/api/brief/export")
def brief_export() -> dict:
    """创作简报:最新报告+模板+选题 → D:\\aivideo\\VIDEINSIGHT_BRIEF.md(产线 agent 必读)"""
    from . import brief

    return brief.build_brief()


@app.get("/api/brief")
def brief_get() -> dict:
    """外接 AI 直喂:返回简报全文 + 可整段粘贴的包装提示词"""
    from . import brief

    return {"content": brief.build_prompt(), "raw": brief.BRIEF_PATH.read_text(encoding="utf-8") if brief.BRIEF_PATH.exists() else ""}


@app.get("/api/sync-status")
def sync_status() -> dict:
    s = db.conn().execute("SELECT * FROM sources WHERE id=?", (ingest.SOURCE_ID,)).fetchone()
    last = db.conn().execute(
        "SELECT * FROM fetch_runs WHERE source_id=? ORDER BY started_at DESC LIMIT 1",
        (ingest.SOURCE_ID,),
    ).fetchone()
    state = "ok"
    if _sync_state["error"]:
        state = "error"
    elif s and s["health"] in ("degraded", "failing"):
        state = "stale"
    return {
        "source": "douyin-mcp",
        "state": state,
        "lastSync": last["finished_at"] if last and last["finished_at"] else (last["started_at"] if last else None),
        "detail": f"健康={s['health'] if s else '?'} · 失败={s['fail_count'] if s else 0} · 下次调度={s['next_fetch_at'] if s else '?'}",
        "running": _sync_state["running"],
        "lastResult": _sync_state["last_result"],
        "error": _sync_state["error"],
    }


@app.post("/api/sync")
def trigger_sync() -> dict:
    if _sync_state["running"] or not _sync_lock.acquire(blocking=False):
        return {"started": False, "reason": "已有同步在跑"}
    _sync_state.update(running=True, error=None)

    def _worker():
        try:
            result = ingest.run_douyin_sync()
            _sync_state["last_result"] = result
        except Exception as e:  # noqa: BLE001 - 状态回传
            _sync_state["error"] = str(e)[:300]
        finally:
            _sync_state["running"] = False
            _sync_lock.release()

    threading.Thread(target=_worker, daemon=True).start()
    return {"started": True}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":
    main()
