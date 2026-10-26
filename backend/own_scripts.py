"""自有脚本采集:从本地产线(D:\\aivideo\\remotion-vibe\\src\\<项目>\\script*.ts)提取逐字剧本

产线结构:每个视频一个项目目录,script.ts(手写基座)/script_vo.ts(配音生成版)
内含 CARDS 数组,注释声明"字幕卡真理源 = 目标剧本全文(逐字保留)"。
提取:正则抽取所有 {t: '...'} 文本段拼接 = 完整脚本;kw 段为关键词高亮。
纯本地文件解析:无网络、无 ASR、幂等(按项目目录去重)。
"""
import re
from datetime import datetime
from pathlib import Path

from . import db

LINE_ROOT = Path(r"D:\aivideo\remotion-vibe\src")

# 项目目录 → 可读标题(按需补充;未映射的用目录名)
TITLE_MAP = {
    "tomorrow": "明日复明日,可明日若是无穷无尽?",
    "stable": "稳定的生活,是另一种牢笼?",
    "finite": "有限,就等于没有意义吗?",
    "success": "成功,才是成功之母?",
    "coder": "我和女朋友为AI吵了一架",
    "calc": "越会算账的人,越容易体验不到人生吗",
    "milk": "便利贴为什么是黄色的",
    "runback": "短期没回报的事,还值得做吗",
    "sticky": "燕子,才是最狡诈的动物?",
    "harvest": "为什么记住一切的人,反而可能不会思考?",
}


def _extract_text(content: str) -> str:
    """抽取 CARDS 中所有 {t: '...'} / {t: "..."} 文本段,按序拼接(跳过注释行)"""
    content = re.sub(r"^\s*//.*$", "", content, flags=re.M)  # 去行注释
    parts = re.findall(r"\{\s*t:\s*'([^']*)'", content) + re.findall(r'\{\s*t:\s*"([^"]*)"', content)
    # 两类引号混用时保序:改为统一扫描
    parts = [p for p in re.findall(r"\{\s*t:\s*('([^']*)'|\"([^\"]*)\")", content)]
    text = "".join(m[1] or m[2] for m in parts)
    return text.strip()


def _norm(s: str) -> str:
    """标题归一:只留汉字/字母/数字(白名单),小写——用于产线脚本 ↔ 抖音作品配对"""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", s or "").lower()


def _match_video_id(title: str) -> str | None:
    """在抖音自有作品里找配对:归一后互相包含,或最长公共前缀 ≥8 字"""
    key = _norm(title)
    if len(key) < 4:
        return None
    best: tuple[int, str] | None = None  # (公共前缀长, video_id)
    for r in db.conn().execute("SELECT video_id, title FROM videos WHERE is_own=1"):
        t = _norm(r["title"])
        if len(t) < 4:
            continue
        if key in t or t in key:
            return r["video_id"]
        # 前缀匹配:抖音标题常为 "vibe知识大赏｜<脚本标题>后续文案"
        n = 0
        for a, b in zip(t, key):
            if a != b:
                break
            n += 1
        if n >= 8 and (best is None or n > best[0]):
            best = (n, r["video_id"])
    return best[1] if best else None


def harvest_own_scripts() -> dict:
    """扫描产线项目目录 → 提取脚本 → 配对抖音作品 → video_scripts 表(幂等)
    持久闭环:产线每新增/更新一个项目,下一次 tick 自动同步进中台。"""
    db.init_db()
    if not LINE_ROOT.exists():
        return {"error": f"产线目录不存在: {LINE_ROOT}"}
    now = datetime.now().isoformat(timespec="seconds")
    found = saved = matched = 0
    for proj_dir in sorted(LINE_ROOT.iterdir()):
        if not proj_dir.is_dir():
            continue
        script_file = next(
            (f for f in (proj_dir / "script.ts", proj_dir / "script_vo.ts") if f.exists()),
            None,
        )
        if not script_file:
            continue
        found += 1
        try:
            text = _extract_text(script_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if len(text) < 40:
            continue
        mtime = datetime.fromtimestamp(script_file.stat().st_mtime).isoformat(timespec="seconds")
        title = TITLE_MAP.get(proj_dir.name, proj_dir.name)
        vid = _match_video_id(title)
        if vid:
            matched += 1
        c = db.conn()
        c.execute(
            """INSERT INTO video_scripts(project, title, text, chars, source, file_mtime, video_id, created_at)
               VALUES(?,?,?,?, 'aivideo_line', ?, ?, ?)
               ON CONFLICT(project) DO UPDATE SET
                 title=excluded.title, text=excluded.text, chars=excluded.chars,
                 file_mtime=excluded.file_mtime, video_id=excluded.video_id""",
            (proj_dir.name, title, text, len(text), mtime, vid, now),
        )
        saved += 1
    db.conn().commit()
    return {"projects_found": found, "scripts_saved": saved, "matched_videos": matched}


def latest_own_scripts(n: int = 2) -> list[dict]:
    """最近更新的 N 条自有脚本(带配对作品的真实战绩,报告对比用)"""
    rows = db.conn().execute(
        """SELECT s.project, s.title, s.text, s.chars, s.file_mtime, s.video_id,
              v.views, v.completion_rate, v.completion_5s_rate, v.skip_2s_rate, v.favorites
           FROM video_scripts s
           LEFT JOIN videos v ON v.video_id = s.video_id AND v.platform = 'douyin'
           ORDER BY s.file_mtime DESC LIMIT ?""",
        (n,),
    ).fetchall()
    return [dict(r) for r in rows]
