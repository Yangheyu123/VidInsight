"""P4 爆款雷达:yt-dlp 两阶段采集 B站/YouTube 对标元数据 → 统一库(is_own=0)

两阶段:
  1) flat 列目录(一次请求拿全视频 ID,不逐条访问)
  2) 逐条全量元数据(随机延时限流:B站 2-4s,YouTube 3-6s,上限 30 条防超时)
B站收藏数补抓:api.bilibili.com/x/web-interface/view?bvid=(yt-dlp 不返回)
支持:频道/B站空间 URL 模式 + bilisearch/ytsearch 关键词模式。
"""
import json
import random
import re
import time
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from . import db
from .config import BJ_TZ

DELAY = {"bilibili": (2.0, 4.0), "youtube": (3.0, 6.0)}


def _detect_platform(url: str) -> str:
    if "bilibili.com" in url or url.startswith("bilisearch"):
        return "bilibili"
    if "youtube.com" in url or "youtu.be" in url or url.startswith("ytsearch"):
        return "youtube"
    raise ValueError(f"无法识别平台: {url}")


def _ydl_opts(platform: str, flat: bool) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "retries": 2,
        "socket_timeout": 20,
    }
    if platform == "bilibili":
        # B站风控(412):伪造 buvid3 cookie + UA + Referer(毕设 BilibiliFetcher 验证过的方案)
        from uuid import uuid4

        opts["http_headers"] = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Cookie": f"buvid3={uuid4().hex}-infoc;",
        }
    if flat:
        opts["extract_flat"] = "in_playlist"
    return opts


def _list_entries(target: str, platform: str, limit: int) -> list[dict]:
    """阶段一:flat 列目录 → [{id, url}]"""
    from yt_dlp import YoutubeDL

    opts = _ydl_opts(platform, flat=True)
    opts["playlistend"] = limit
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(target, download=False)
    entries = (info or {}).get("entries") or []
    out = []
    for e in entries:
        vid = e.get("id")
        if not vid:
            continue
        url = e.get("url") or (
            f"https://www.bilibili.com/video/{vid}" if vid.startswith("BV") else f"https://www.youtube.com/watch?v={vid}"
        )
        out.append({"id": vid, "url": url})
    return out[:limit]


def _bili_favorites(bvid: str) -> int | None:
    """B站收藏数补抓(公开接口)"""
    try:
        req = urllib.request.Request(
            f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        return (d.get("data") or {}).get("stat", {}).get("favorite")
    except Exception:  # noqa: BLE001 - 补抓失败仅留空
        return None


def _fetch_one(entry: dict, platform: str) -> dict | None:
    """阶段二:单条全量元数据"""
    from yt_dlp import YoutubeDL

    with YoutubeDL(_ydl_opts(platform, flat=False)) as ydl:
        info = ydl.extract_info(entry["url"], download=False)
    if not info or info.get("_type") == "playlist":
        return None
    ts = info.get("timestamp")
    pub = (
        datetime.fromtimestamp(ts, tz=ZoneInfo(BJ_TZ)).isoformat(timespec="seconds")
        if ts
        else (info.get("upload_date") or None)
    )
    vid = info.get("id") or entry["id"]
    favorites = None
    if platform == "bilibili":
        favorites = _bili_favorites(vid) if vid.startswith("BV") else None
    return {
        "platform": platform,
        "video_id": vid,
        "account_id": info.get("uploader") or info.get("channel"),
        "url": info.get("webpage_url") or entry["url"],
        "title": info.get("title"),
        "publish_time": pub,
        "duration_sec": int(info.get("duration") or 0),
        "views": info.get("view_count"),
        "likes": info.get("like_count"),
        "favorites": favorites,
        "comments": info.get("comment_count"),
        "shares": None,
        "completion_rate": None,  # 公开数据无完播口径
        "completion_5s_rate": None,
        "skip_2s_rate": None,
        "avg_watch_sec": None,
        "exposure": None,
        "followers_gained": None,
        "danmaku": None, "unfollows": None,
        "follower_play_ratio": None, "avg_play_ratio": None, "dislike_rate": None,
        "like_rate": None, "comment_rate": None, "share_rate": None, "favorite_rate": None,
        "cover_url": info.get("thumbnail"),
        "status": None,
        "is_own": 0,
        "template_id": None,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }


def _build_target(mode: str, platform: str, url: str = "", keyword: str = "", limit: int = 30) -> str:
    if mode == "channel":
        return url
    if mode == "search":
        prefix = "bilisearch" if platform == "bilibili" else "ytsearch"
        return f"{prefix}{min(limit, 50)}:{keyword}"
    raise ValueError("mode 必须是 channel 或 search")


RADAR_SOURCE = "radar_bench"  # 对标源统一注册(周级调度)


def collect_radar(mode: str, url: str = "", keyword: str = "", platform: str = "", limit: int = 30, progress=None) -> dict:
    """入口:频道/搜索采集 → 统一库 + 审计。带限流,分钟级,供 API 异步/tick 调用。
    progress(done, total, failed):可选进度回调(前端持久进度条)。"""
    db.init_db()
    db.conn().execute(
        """INSERT INTO sources(id, name, kind, interval_minutes, updated_at)
           VALUES(?, '对标雷达(yt-dlp)', 'radar', 10080, ?)
           ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at""",
        (RADAR_SOURCE, db.now_iso()),
    )
    db.conn().commit()

    plat = platform or _detect_platform(url or (f"bilisearch:{keyword}" if not url else url))
    if mode == "search" and not platform:
        raise ValueError("搜索模式必须指定 platform=bilibili|youtube")
    target = _build_target(mode, plat, url, keyword, limit)

    with db.fetch_run(RADAR_SOURCE):
        entries = _list_entries(target, plat, limit)
        cap = min(len(entries), 30)  # 全量阶段上限,防长跑
        lo, hi = DELAY.get(plat, (2.0, 4.0))
        saved = new_count = failed = 0
        for i, e in enumerate(entries[:cap]):
            try:
                v = _fetch_one(e, plat)
                if v and v.get("title"):
                    if db.upsert_video(v):
                        new_count += 1
                    saved += 1
            except Exception:  # noqa: BLE001 - 单条失败跳过
                failed += 1
            if progress:
                try:
                    progress(i + 1, cap, failed)
                except Exception:  # noqa: BLE001
                    pass
            if i < cap - 1:
                time.sleep(random.uniform(lo, hi))
        return {"listed": len(entries), "saved": saved, "new": new_count, "failed": failed}
