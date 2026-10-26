"""douyin-mcp 适配器:只读它的 douyin.sqlite,映射进统一 schema

数据源三张表:
  videos                 作品列表(标题/发布时间/时长/封面/状态)
  video_metric_snapshots 详情页快照(含 raw_metric_json —— 全量字段的宝藏)
  video_metrics          天级粒度行(metric_date)→ video_daily 表

raw_metric_json 解析(平台口径,页面显示什么就存什么):
  "2s跳出率"/"不感兴趣率"/"粉丝播放占比"/"平均播放占比"/"点赞率"/"评论率"/"分享率"/"收藏率" → 0-1 比率
  "弹幕量"/"脱粉量" → 整数(支持 "1.2万" 写法)
"""
import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import BJ_TZ, DOUYIN_MCP_DB

# raw JSON 中文键 → 统一字段
_PCT_KEYS = {
    "2s跳出率": "skip_2s_rate",
    "不感兴趣率": "dislike_rate",
    "粉丝播放占比": "follower_play_ratio",
    "平均播放占比": "avg_play_ratio",
    "点赞率": "like_rate",
    "评论率": "comment_rate",
    "分享率": "share_rate",
    "收藏率": "favorite_rate",
}
_CNT_KEYS = {"弹幕量": "danmaku", "脱粉量": "unfollows"}


def _iso(epoch_sec: int | None) -> str | None:
    if not epoch_sec:
        return None
    return datetime.fromtimestamp(epoch_sec, tz=ZoneInfo(BJ_TZ)).isoformat(timespec="seconds")


def _parse_raw(raw_json: str | None) -> dict:
    """raw_metric_json → 统一字段子集;解析失败静默返回空(缺字段=页面没显示)"""
    out: dict = {v: None for v in (*_PCT_KEYS.values(), *_CNT_KEYS.values())}
    if not raw_json:
        return out
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return out
    if not isinstance(data, dict):
        return out
    for zh, field in _PCT_KEYS.items():
        val = data.get(zh)
        if isinstance(val, str) and val.strip().endswith("%"):
            try:
                out[field] = round(float(val.strip().rstrip("%")) / 100, 6)
            except ValueError:
                pass
    for zh, field in _CNT_KEYS.items():
        val = data.get(zh)
        if isinstance(val, (int, float)):
            out[field] = int(val)
        elif isinstance(val, str):
            v = val.strip().replace(",", "")
            try:
                if v.endswith("万"):
                    out[field] = int(float(v[:-1]) * 10_000)
                elif v.endswith("亿"):
                    out[field] = int(float(v[:-1]) * 100_000_000)
                else:
                    out[field] = int(float(v))
            except ValueError:
                pass
    return out


def pull() -> tuple[list[dict], list[dict], list[dict]]:
    """读取 douyin-mcp 库 → (统一 videos, 快照列表, 天级行)。

    只读打开,不复制不修改源库;本函数即"ingest 统一入口"的拉取端。
    """
    src = sqlite3.connect(f"file:{DOUYIN_MCP_DB}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    try:
        videos_raw = src.execute(
            """SELECT id, account_id, title, publish_time, duration, video_url,
                      cover_url, status FROM videos WHERE is_active=1"""
        ).fetchall()
        snaps_raw = src.execute(
            """SELECT s.*, s.raw_metric_json FROM video_metric_snapshots s
               ORDER BY s.captured_at"""
        ).fetchall()
        daily_raw = src.execute(
            "SELECT * FROM video_metrics ORDER BY metric_date"
        ).fetchall()
    finally:
        src.close()

    # 每条视频:字段级合并(按 captured_at 升序,后到的非空值逐字段覆盖)
    # ——防止"新但稀疏"的列表级快照冲掉"旧但富"的详情级数据
    merged: dict[str, dict] = {}
    for s in snaps_raw:
        m = merged.setdefault(s["video_id"], {})
        raw = _parse_raw(s["raw_metric_json"])
        fields = {
            "views": s["play_count"],
            "likes": s["like_count"],
            "favorites": s["collect_count"],
            "comments": s["comment_count"],
            "shares": s["share_count"],
            "completion_rate": s["completion_rate"],
            "completion_5s_rate": s["five_second_completion_rate"],
            "skip_2s_rate": raw["skip_2s_rate"],
            "avg_watch_sec": s["average_watch_duration_seconds"],
            "exposure": s["exposure_count"],
            "followers_gained": s["follower_gain"],
            "danmaku": raw["danmaku"],
            "unfollows": raw["unfollows"],
            "follower_play_ratio": raw["follower_play_ratio"],
            "avg_play_ratio": raw["avg_play_ratio"],
            "dislike_rate": raw["dislike_rate"],
            "like_rate": raw["like_rate"],
            "comment_rate": raw["comment_rate"],
            "share_rate": raw["share_rate"],
            "favorite_rate": raw["favorite_rate"],
        }
        for k, val in fields.items():
            if val is not None:
                m[k] = val

    now = datetime.now().isoformat(timespec="seconds")
    videos: list[dict] = []
    for r in videos_raw:
        m = merged.get(r["id"], {})
        videos.append(
            {
                "platform": "douyin",
                "video_id": r["id"],
                "account_id": r["account_id"],
                "url": r["video_url"],
                "title": r["title"],
                "publish_time": _iso(r["publish_time"]),
                "duration_sec": r["duration"],
                "views": m.get("views"),
                "likes": m.get("likes"),
                "favorites": m.get("favorites"),
                "comments": m.get("comments"),
                "shares": m.get("shares"),
                "completion_rate": m.get("completion_rate"),
                "completion_5s_rate": m.get("completion_5s_rate"),
                "skip_2s_rate": m.get("skip_2s_rate"),
                "avg_watch_sec": m.get("avg_watch_sec"),
                "exposure": m.get("exposure"),
                "followers_gained": m.get("followers_gained"),
                "danmaku": m.get("danmaku"),
                "unfollows": m.get("unfollows"),
                "follower_play_ratio": m.get("follower_play_ratio"),
                "avg_play_ratio": m.get("avg_play_ratio"),
                "dislike_rate": m.get("dislike_rate"),
                "like_rate": m.get("like_rate"),
                "comment_rate": m.get("comment_rate"),
                "share_rate": m.get("share_rate"),
                "favorite_rate": m.get("favorite_rate"),
                "cover_url": r["cover_url"],
                "status": r["status"],
                "is_own": 1,
                "template_id": None,
                "collected_at": now,
            }
        )

    snapshots: list[dict] = []
    for s in snaps_raw:
        cap = s["captured_at"]
        raw = _parse_raw(s["raw_metric_json"])
        snapshots.append(
            {
                "platform": "douyin",
                "video_id": s["video_id"],
                "captured_at": cap,
                "date": cap[:10],
                "views": s["play_count"],
                "likes": s["like_count"],
                "favorites": s["collect_count"],
                "comments": s["comment_count"],
                "shares": s["share_count"],
                "completion_rate": s["completion_rate"],
                "completion_5s_rate": s["five_second_completion_rate"],
                "skip_2s_rate": raw["skip_2s_rate"],
                "followers_gained": s["follower_gain"],
                **{k: raw[k] for k in ("danmaku", "unfollows", "follower_play_ratio", "avg_play_ratio", "dislike_rate")},
            }
        )

    daily: list[dict] = []
    for d in daily_raw:
        daily.append(
            {
                "platform": "douyin",
                "video_id": d["video_id"],
                "date": d["metric_date"],
                "views": d["play_count"],
                "likes": d["like_count"],
                "favorites": d["collect_count"],
                "comments": d["comment_count"],
                "shares": d["share_count"],
                "completion_rate": d["complete_rate"],
                "avg_watch_sec": d["avg_watch_duration"],
                "followers_gained": d["follower_gain"],
            }
        )
    return videos, snapshots, daily
