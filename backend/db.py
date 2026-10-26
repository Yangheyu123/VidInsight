"""统一数据库层:platform.db schema 与 upsert(ARCH §5 + §8 移植设计)

表:
  videos      作品主表(全平台统一,自有+对标)
  snapshots   逐次抓取快照(趋势/增量的数据源)
  sources     采集源注册表(健康状态机 + 水位线,AIHOT/毕设合并版)
  fetch_runs  每次抓取审计行(两侦察项目同构表)
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime

from .config import PLATFORM_DB

_local = threading.local()  # FastAPI 多线程下安全连接

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
  platform TEXT NOT NULL,
  video_id TEXT NOT NULL,
  account_id TEXT,
  url TEXT,
  title TEXT,
  publish_time TEXT,
  duration_sec INTEGER,
  views INTEGER, likes INTEGER, favorites INTEGER,
  comments INTEGER, shares INTEGER,
  completion_rate REAL, completion_5s_rate REAL, skip_2s_rate REAL,
  avg_watch_sec REAL, exposure INTEGER, followers_gained INTEGER,
  danmaku INTEGER, unfollows INTEGER,
  follower_play_ratio REAL, avg_play_ratio REAL,
  dislike_rate REAL,
  like_rate REAL, comment_rate REAL, share_rate REAL, favorite_rate REAL,
  cover_url TEXT, status TEXT,
  is_own INTEGER NOT NULL DEFAULT 1,
  template_id TEXT,
  collected_at TEXT,
  PRIMARY KEY (platform, video_id)
);

CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL,
  video_id TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  date TEXT NOT NULL,
  views INTEGER, likes INTEGER, favorites INTEGER,
  comments INTEGER, shares INTEGER,
  completion_rate REAL, completion_5s_rate REAL, skip_2s_rate REAL,
  followers_gained INTEGER,
  danmaku INTEGER, unfollows INTEGER,
  follower_play_ratio REAL, avg_play_ratio REAL, dislike_rate REAL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_v ON snapshots(platform, video_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_d ON snapshots(date);
CREATE UNIQUE INDEX IF NOT EXISTS uq_snapshots_src ON snapshots(platform, video_id, captured_at);

CREATE TABLE IF NOT EXISTS video_daily (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  platform TEXT NOT NULL,
  video_id TEXT NOT NULL,
  date TEXT NOT NULL,
  views INTEGER, likes INTEGER, favorites INTEGER,
  comments INTEGER, shares INTEGER,
  completion_rate REAL, avg_watch_sec REAL, followers_gained INTEGER,
  UNIQUE(platform, video_id, date)
);
CREATE INDEX IF NOT EXISTS idx_vdaily_date ON video_daily(date);

CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  health TEXT NOT NULL DEFAULT 'ok',        -- ok/degraded/failing/paused
  fail_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  cursor_json TEXT,                          -- 水位线(增量游标)
  next_fetch_at TEXT,
  interval_minutes INTEGER NOT NULL DEFAULT 1440,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS fetch_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,                      -- success/partial/failed/running
  found_count INTEGER, new_count INTEGER,
  duration_ms INTEGER, error TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_source ON fetch_runs(source_id, started_at);

CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,                        -- breakdown(拆解)/weekly(周报)
  title TEXT NOT NULL,
  content_md TEXT NOT NULL,
  engine TEXT NOT NULL DEFAULT 'rule',       -- llm / rule(降级)
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS materials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,                      -- zhihu_hot / weibo_hot / hitokoto / classics / bili_hot / v2ex ...
  category TEXT NOT NULL DEFAULT '热点爆款',  -- 热点爆款 / 传统哲学 / 小众潜力
  title TEXT NOT NULL,
  content TEXT,
  url TEXT UNIQUE,
  relevance REAL, conflict REAL, save_potential REAL, score REAL,
  suggestion TEXT, tags TEXT,
  status TEXT NOT NULL DEFAULT '待用',        -- 待用 / 已用 / 丢弃
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status, score DESC);

CREATE TABLE IF NOT EXISTS templates (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  hook TEXT,
  structure_md TEXT,
  accent TEXT NOT NULL DEFAULT 'develop',    -- develop/preview/ship(图表强调色)
  report_id INTEGER,
  stats_json TEXT,                           -- {videos,avgViews,avgCompletion,avg5s,avgFavRate}
  created_at TEXT NOT NULL
);
"""

# 轻量迁移:老库补列(幂等,列已存在则跳过)
_MIGRATIONS = (
    "ALTER TABLE videos ADD COLUMN skip_2s_rate REAL",
    "ALTER TABLE videos ADD COLUMN danmaku INTEGER",
    "ALTER TABLE videos ADD COLUMN unfollows INTEGER",
    "ALTER TABLE videos ADD COLUMN follower_play_ratio REAL",
    "ALTER TABLE videos ADD COLUMN avg_play_ratio REAL",
    "ALTER TABLE videos ADD COLUMN dislike_rate REAL",
    "ALTER TABLE videos ADD COLUMN like_rate REAL",
    "ALTER TABLE videos ADD COLUMN comment_rate REAL",
    "ALTER TABLE videos ADD COLUMN share_rate REAL",
    "ALTER TABLE videos ADD COLUMN favorite_rate REAL",
    "ALTER TABLE videos ADD COLUMN cover_url TEXT",
    "ALTER TABLE videos ADD COLUMN status TEXT",
    "ALTER TABLE snapshots ADD COLUMN skip_2s_rate REAL",
    "ALTER TABLE snapshots ADD COLUMN danmaku INTEGER",
    "ALTER TABLE snapshots ADD COLUMN unfollows INTEGER",
    "ALTER TABLE snapshots ADD COLUMN follower_play_ratio REAL",
    "ALTER TABLE snapshots ADD COLUMN avg_play_ratio REAL",
    "ALTER TABLE snapshots ADD COLUMN dislike_rate REAL",
    "ALTER TABLE materials ADD COLUMN category TEXT NOT NULL DEFAULT '热点爆款'",
)


def conn() -> sqlite3.Connection:
    """线程本地连接;platform.db 由后端独占写,前端只经 API 读"""
    c = getattr(_local, "conn", None)
    if c is None:
        PLATFORM_DB.parent.mkdir(parents=True, exist_ok=True)
        c = sqlite3.connect(PLATFORM_DB, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        _local.conn = c
    return c


def init_db() -> None:
    conn().executescript(SCHEMA)
    for alter in _MIGRATIONS:
        try:
            conn().execute(alter)
        except sqlite3.OperationalError:
            pass  # 列已存在
    conn().commit()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def fetch_run(source_id: str):
    """审计上下文:开始写 running,结束回写结果(AIHOT fetch_runs 模式)"""
    c = conn()
    import time

    t0 = time.monotonic()
    cur = c.execute(
        "INSERT INTO fetch_runs(source_id, started_at, status) VALUES(?,?, 'running')",
        (source_id, now_iso()),
    )
    run_id = cur.lastrowid
    try:
        yield run_id
    except Exception as e:  # noqa: BLE001 - 审计层兜底记录一切异常
        c.execute(
            "UPDATE fetch_runs SET finished_at=?, status='failed', duration_ms=?, error=? WHERE id=?",
            (now_iso(), int((time.monotonic() - t0) * 1000), str(e)[:500], run_id),
        )
        _bump_health(c, source_id, ok=False, error=str(e)[:200])
        c.commit()
        raise
    else:
        c.execute(
            "UPDATE fetch_runs SET finished_at=?, status='success', duration_ms=? WHERE id=?",
            (now_iso(), int((time.monotonic() - t0) * 1000), run_id),
        )
        _bump_health(c, source_id, ok=True)
        c.commit()


def _bump_health(c: sqlite3.Connection, source_id: str, *, ok: bool, error: str | None = None) -> None:
    """健康状态机:连续失败 3 次→degraded,10 次→failing;成功复位 ok(毕设 SourceHealthService 模式)"""
    row = c.execute("SELECT fail_count FROM sources WHERE id=?", (source_id,)).fetchone()
    if row is None:
        return
    fails = 0 if ok else row["fail_count"] + 1
    health = "ok" if ok else ("degraded" if fails < 10 else "failing")
    c.execute(
        "UPDATE sources SET health=?, fail_count=?, last_error=?, updated_at=? WHERE id=?",
        (health, fails, None if ok else error, now_iso(), source_id),
    )


def upsert_video(v: dict) -> bool:
    """upsert 作品主表;返回是否新插入(供 new_count 统计)"""
    c = conn()
    cols = [
        "platform", "video_id", "account_id", "url", "title", "publish_time",
        "duration_sec", "views", "likes", "favorites", "comments", "shares",
        "completion_rate", "completion_5s_rate", "skip_2s_rate",
        "avg_watch_sec", "exposure", "followers_gained",
        "danmaku", "unfollows", "follower_play_ratio", "avg_play_ratio",
        "dislike_rate", "like_rate", "comment_rate", "share_rate", "favorite_rate",
        "cover_url", "status", "is_own", "template_id", "collected_at",
    ]
    exists = c.execute(
        "SELECT 1 FROM videos WHERE platform=? AND video_id=?", (v["platform"], v["video_id"])
    ).fetchone()
    c.execute(
        f"INSERT INTO videos({','.join(cols)}) VALUES({','.join('?' * len(cols))}) "
        "ON CONFLICT(platform, video_id) DO UPDATE SET "
        + ",".join(f"{k}=excluded.{k}" for k in cols if k not in ("platform", "video_id")),
        [v.get(k) for k in cols],
    )
    return exists is None


def insert_snapshot(v: dict, captured_at: str, date: str) -> None:
    """幂等写入(唯一索引 platform+video_id+captured_at,重复采集自动忽略)"""
    c = conn()
    c.execute(
        """INSERT OR IGNORE INTO snapshots(platform, video_id, captured_at, date,
             views, likes, favorites, comments, shares,
             completion_rate, completion_5s_rate, skip_2s_rate, followers_gained,
             danmaku, unfollows, follower_play_ratio, avg_play_ratio, dislike_rate)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            v["platform"], v["video_id"], captured_at, date,
            v.get("views"), v.get("likes"), v.get("favorites"),
            v.get("comments"), v.get("shares"),
            v.get("completion_rate"), v.get("completion_5s_rate"),
            v.get("skip_2s_rate"), v.get("followers_gained"),
            v.get("danmaku"), v.get("unfollows"),
            v.get("follower_play_ratio"), v.get("avg_play_ratio"),
            v.get("dislike_rate"),
        ),
    )


def insert_daily(d: dict) -> None:
    """天级粒度行(douyin-mcp video_metrics / metric_date),幂等"""
    c = conn()
    c.execute(
        """INSERT OR IGNORE INTO video_daily(platform, video_id, date,
             views, likes, favorites, comments, shares,
             completion_rate, avg_watch_sec, followers_gained)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            d["platform"], d["video_id"], d["date"],
            d.get("views"), d.get("likes"), d.get("favorites"),
            d.get("comments"), d.get("shares"),
            d.get("completion_rate"), d.get("avg_watch_sec"),
            d.get("followers_gained"),
        ),
    )
