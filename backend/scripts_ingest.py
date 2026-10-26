"""爆款脚本管线(dycopy 模式移植):对标爆款视频 → 音频(临时)→ 转写 → LLM 提炼 → 素材库

铁律:
  · 文字是资产:逐字稿与提炼结果进素材库(分类=爆款脚本)
  · 资源即删:音频落在 TemporaryDirectory,转写完成自动销毁,不落库不残留
  · 串行限速:一次最多 N 条,条间延时,风控友好
候选:对标库(is_own=0)按播放降序,且尚未入库过(url 去重)。
"""
import tempfile
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from . import asr, db, llm
from .persona import PERSONA

REFINE_SYSTEM = (
    f"你是短视频脚本分析师。{PERSONA}"
    "输入是一条对标爆款的标题与完整逐字稿。输出紧凑中文分析(150字内,分号分隔):"
    "钩子=前3秒原句引用并说明为何有效;节奏=开场/中段/结尾各在干什么;"
    "金句=逐字稿中最值得收藏的1-2句原文;改编=用创作者身份翻这个选题的一句方案。"
    "格式:钩子「…」;节奏:…;金句「…」;改编:…。只引用原文,不编造。"
)


def _download_audio(url: str, platform: str, tmp_dir: str) -> str | None:
    """yt-dlp 仅拉音频流(bilibili 带 buvid3),返回本地文件路径"""
    from yt_dlp import YoutubeDL

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}
    if platform == "bilibili":
        headers.update({"Referer": "https://www.bilibili.com/", "Cookie": f"buvid3={uuid4().hex}-infoc;"})
    opts = {
        "quiet": True, "no_warnings": True, "skip_download": False,
        "format": "bestaudio/best",
        "outtmpl": str(Path(tmp_dir) / "%(id)s.%(ext)s"),
        "http_headers": headers,
        "socket_timeout": 30, "retries": 2,
        "max_filesize": 80 * 1024 * 1024,  # 超大文件跳过
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if not info:
        return None
    vid = info.get("id")
    for f in Path(tmp_dir).iterdir():
        if f.stem == vid or f.name.startswith(str(vid)):
            return str(f)
    return None


def _ingest_one(video: dict, now: str) -> bool:
    """单条:拉音频 → 转写 → 提炼 → 入库;音频随临时目录销毁"""
    url = video["url"]
    with tempfile.TemporaryDirectory(prefix="vidinsight-asr-") as tmp:
        audio = _download_audio(url, video["platform"], tmp)
        if not audio:
            print(f"[scripts] 未取到音频:{url[:60]}")
            return False
        text = asr.transcribe(audio)
    if not text or len(text) < 30:
        print(f"[scripts] 转写过短,跳过:{url[:60]}")
        return False

    refine = llm.chat(REFINE_SYSTEM, f"标题:{video['title']}\n播放:{video['views']}\n逐字稿:\n{text[:4000]}", temperature=0.3)
    suggestion = (refine or "LLM 提炼降级:请人工阅读逐字稿").strip()[:400]

    c = db.conn()
    c.execute(
        """INSERT OR IGNORE INTO materials(source, category, title, content, url,
             relevance, conflict, save_potential, score, suggestion, tags, status, created_at)
           VALUES('bench_video', '爆款脚本', ?, ?, ?, 10, 10, 10, 10, ?, '对标逐字稿', '待用', ?)""",
        (video["title"][:120], text[:1500], url, suggestion, now),
    )
    c.commit()
    return True


def ingest_bench_scripts(limit: int = 3) -> dict:
    """入口:对标爆款 → 脚本语料。limit 控制单轮时长(每条约 1-3 分钟)。"""
    db.init_db()
    rows = db.conn().execute(
        """SELECT v.platform, v.url, v.title, v.views FROM videos v
           WHERE v.is_own=0 AND v.url IS NOT NULL AND v.views > 0
             AND NOT EXISTS (SELECT 1 FROM materials m WHERE m.url = v.url)
           ORDER BY v.views DESC LIMIT ?""",
        (limit * 3,),
    ).fetchall()
    now = datetime.now().isoformat(timespec="seconds")
    done = skipped = 0
    for v in rows:
        if done >= limit:
            break
        try:
            if _ingest_one(dict(v), now):
                done += 1
                print(f"[scripts] ✅ {v['title'][:30]}")
            else:
                skipped += 1
        except Exception as e:  # noqa: BLE001 - 单条失败不阻断
            skipped += 1
            print(f"[scripts] 失败 {v['title'][:24]}: {e}")
        if done < limit:
            time.sleep(3)
    return {"candidates": len(rows), "transcribed": done, "skipped": skipped}
