"""P3 素材引擎:公开源抓取 → LLM 打分(相关性×冲突感×收藏潜力)→ materials 表

信源(公开接口,不引 RSSHub 服务):
  zhihu_hot   知乎热榜(选题雷达)
  hitokoto    一言 API(文学/哲学句子,金句素材)
打分:LLM 批量评估 0-10 三维 + 改写建议;LLM 不可用 → 规则关键词降级打分。
"""
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime

from . import db, llm
from .persona import PERSONA

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def _get_json(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_zhihu_hot(limit: int = 30) -> list[dict]:
    """知乎热榜(移动端公开接口):标题 + 摘要 + 问题链接"""
    data = _get_json("https://api.zhihu.com/topstory/hot-list?limit=50")
    out = []
    for it in data.get("data", [])[:limit]:
        t = it.get("target") or {}
        title = (t.get("title") or "").strip()
        if not title:
            continue
        card = it.get("card_id") or ""
        qid = card.split("_")[-1] if card.startswith("Q_") else (t.get("id") or "")
        out.append(
            {
                "source": "zhihu_hot",
                "title": title,
                "content": (it.get("detail_text") or t.get("excerpt") or "")[:200],
                "url": f"https://www.zhihu.com/question/{qid}" if qid else "https://www.zhihu.com/hot",
            }
        )
    return out


def fetch_hitokoto(n: int = 8) -> list[dict]:
    """一言 API(文学 d / 哲学 k 分类):金句素材"""
    out, seen = [], set()
    for _ in range(n * 2):
        if len(out) >= n:
            break
        try:
            d = _get_json("https://v1.hitokoto.cn/?c=d&c=k&encode=json")
        except Exception:  # noqa: BLE001 - 单源失败不阻断
            continue
        uuid = d.get("uuid") or d.get("hitokoto", "")[:24]
        if uuid in seen:
            continue
        seen.add(uuid)
        out.append(
            {
                "source": "hitokoto",
                "title": (d.get("hitokoto") or "")[:80],
                "content": f"—— {d.get('from', '佚名')}",
                "url": f"https://hitokoto.cn/uuid/{uuid}" if d.get("uuid") else "https://hitokoto.cn",
            }
        )
        time.sleep(0.3)
    return out


def fetch_weibo_hot(limit: int = 20) -> list[dict]:
    """微博热搜(公开接口;关键:必须带 Referer,否则 403 —— 移植自毕设 WeiboFetcher)"""
    req = urllib.request.Request(
        "https://weibo.com/ajax/side/hotSearch",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Referer": "https://weibo.com/",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for it in (d.get("data") or {}).get("realtime") or []:
        word = (it.get("word") or "").strip()
        if not word:
            continue
        out.append(
            {
                "source": "weibo_hot",
                "title": word,
                "content": f"热度 {it.get('num', 0)} · {it.get('label_name', '')}".strip(" ·"),
                "url": f"https://s.weibo.com/weibo?q=%23{urllib.parse.quote(word)}%23",
            }
        )
    return out[:limit]


# ---------------- 语料库:全抓取源(无本地语料) ----------------
# 三类:热点爆款 / 传统哲学 / 小众潜力 —— 全部来自线上真实信号

SCORE_THRESHOLD = 7.0  # 入库门槛:严选,低于此分不存(需求方 2026-10 定为 7 分)


def fetch_bili_hot(limit: int = 15) -> list[dict]:
    """B站综合热门榜(公开接口+buvid3):高爆火款语料"""
    from uuid import uuid4

    req = urllib.request.Request(
        "https://api.bilibili.com/x/web-interface/popular?ps=20&pn=1",
        headers={
            "User-Agent": _UA,
            "Referer": "https://www.bilibili.com/",
            "Cookie": f"buvid3={uuid4().hex}-infoc;",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for it in (d.get("data") or {}).get("list") or []:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        stat = it.get("stat") or {}
        out.append(
            {
                "source": "bili_hot",
                "category": "热点爆款",
                "title": title,
                "content": f"UP:{(it.get('owner') or {}).get('name', '?')} 播放{stat.get('view', '?')} 藏{stat.get('favorite', '?')}",
                "url": f"https://www.bilibili.com/video/{it.get('bvid')}",
            }
        )
    return out[:limit]


def fetch_bili_philosophy(limit: int = 15, keyword: str = "哲学") -> list[dict]:
    """B站哲学区搜索(按播放排序):传统哲学/思辨语料,经过市场验证的选题池"""
    from uuid import uuid4

    req = urllib.request.Request(
        "https://api.bilibili.com/x/web-interface/search/type"
        f"?search_type=video&keyword={urllib.parse.quote(keyword)}&order=click&page=1",
        headers={
            "User-Agent": _UA,
            "Referer": "https://search.bilibili.com/",
            "Cookie": f"buvid3={uuid4().hex}-infoc;",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        d = json.loads(r.read().decode("utf-8"))
    out = []
    for it in (d.get("data") or {}).get("result") or []:
        title = re.sub(r"<[^>]+>", "", it.get("title") or "").strip()
        if not title:
            continue
        out.append(
            {
                "source": "bili_philosophy",
                "category": "传统哲学",
                "title": title,
                "content": f"UP:{it.get('author', '?')} 播放{it.get('play', '?')}",
                "url": it.get("arcurl") or "https://search.bilibili.com",
            }
        )
    return out[:limit]


def fetch_v2ex(limit: int = 15) -> list[dict]:
    """V2EX 热帖(程序员社区):小众潜力语料,贴创作者应届程序员身份"""
    d = _get_json("https://www.v2ex.com/api/topics/hot.json")
    out = []
    for it in d or []:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        out.append(
            {
                "source": "v2ex",
                "category": "小众潜力",
                "title": title,
                "content": f"{it.get('replies', 0)} 回复 · 节点:{(it.get('node') or {}).get('title', '?')}",
                "url": it.get("url") or "https://v2ex.com",
            }
        )
    return out[:limit]


def fetch_baidu_hot(limit: int = 20) -> list[dict]:
    """百度实时热搜(公开接口):热点爆款语料"""
    d = _get_json("https://top.baidu.com/api/board?platform=wise&tab=realtime")
    out = []
    for it in (d.get("data") or {}).get("cards") or []:
        for c in it.get("content") or []:
            word = (c.get("word") or c.get("query") or "").strip()
            if not word:
                continue
            out.append(
                {
                    "source": "baidu_hot",
                    "category": "热点爆款",
                    "title": word,
                    "content": f"热度 {c.get('hotScore', '?')}",
                    "url": c.get("url") or f"https://www.baidu.com/s?wd={urllib.parse.quote(word)}",
                }
            )
    return out[:limit]


def fetch_hackernews(limit: int = 15) -> list[dict]:
    """HackerNews 首页(Algolia 公开接口):英文科技小众潜力语料"""
    d = _get_json("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30")
    out = []
    for it in d.get("hits") or []:
        title = (it.get("title") or "").strip()
        if not title:
            continue
        out.append(
            {
                "source": "hackernews",
                "category": "小众潜力",
                "title": title,
                "content": f"{it.get('points', 0)} 赞 · {it.get('num_comments', 0)} 评论",
                "url": it.get("url") or f"https://news.ycombinator.com/item?id={it.get('objectID')}",
            }
        )
    return out[:limit]


# 分类归属:老源固定映射(入库与回填共用)
CATEGORY_OF_SOURCE = {
    "zhihu_hot": "热点爆款",
    "weibo_hot": "热点爆款",
    "baidu_hot": "热点爆款",
    "bili_hot": "热点爆款",
    "bili_philosophy": "传统哲学",
    "hitokoto": "传统哲学",
    "v2ex": "小众潜力",
    "hackernews": "小众潜力",
}

RULE_KEYS = {
    "relevance": ["哲学", "意义", "自由", "思考", "认知", "尼采", "叔本华", "存在", "虚无", "理性",
                   "孤独", "迷茫", "焦虑", "内卷", "人生", "时间", "选择", "真相", "智慧", "幸福",
                   "程序员", "应届", "秋招", "实习", "毕业", "考研", "offer", "工科", "代码"],
    "conflict": ["反而", "其实", "真相", "骗局", "谎言", "陷阱", "错觉", "才是", "并非", "敢不敢", "为什么"],
    "save_potential": ["收藏", "建议", "清单", "方法", "一句话", "记住", "金句", "值得", "改变"],
}


def _rule_score(item: dict) -> dict:
    text = f"{item['title']} {item.get('content') or ''}"

    def hit(keys: list[str]) -> float:
        n = sum(1 for k in keys if k in text)
        return min(10.0, n * 2.5)

    rel, con, sav = hit(RULE_KEYS["relevance"]), hit(RULE_KEYS["conflict"]), hit(RULE_KEYS["save_potential"])
    if "?" in text or "?" in text:
        con = min(10.0, con + 1.5)
    return {
        "relevance": rel, "conflict": con, "save_potential": sav,
        "score": round(rel * 0.4 + con * 0.3 + sav * 0.3, 2),
        "suggestion": "规则评分(配置 LLM 后自动升级为 AI 评估)",
        "tags": "规则",
    }


def _llm_score_batch(items: list[dict]) -> list[dict] | None:
    """单批打分(≤30 条,控制输出 token 上限);失败返回 None"""
    listing = "\n".join(
        f"{i}. {it['title']} | {(it.get('content') or '')[:60]} | 来源:{it['source']}"
        for i, it in enumerate(items)
    )
    system = (
        f"你是短视频选题评估器。{PERSONA}"
        '对每条素材输出JSON:{"i":序号,"relevance":0-10(=该创作者能否用应届生/程序员第一人称把它转成思辨选题),'
        '"conflict":冲突感/反差0-10,'
        '"save_potential":互动潜力0-10(点赞冲动+评论话头+收藏理由,三合一综合),'
        '"suggestion":"一句话:怎么用他的身份(程序员/应届生/秋招)把这个素材做成思辨短视频,并点出观众为什么会点赞/评论/收藏",'
        '"tags":"标签,逗号分隔"}。只输出JSON数组,不要其他文字。'
    )
    raw = llm.chat(system, listing, temperature=0.2)
    if not raw:
        return None
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return None
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    out = []
    for i, it in enumerate(items):
        e = next((x for x in arr if isinstance(x, dict) and int(x.get("i", -1)) == i), {})
        rel = max(0.0, min(10.0, float(e.get("relevance", 0))))
        con = max(0.0, min(10.0, float(e.get("conflict", 0))))
        sav = max(0.0, min(10.0, float(e.get("save_potential", 0))))
        out.append(
            {
                "relevance": rel, "conflict": con, "save_potential": sav,
                "score": round(rel * 0.4 + con * 0.3 + sav * 0.3, 2),
                "suggestion": str(e.get("suggestion") or "")[:120],
                "tags": str(e.get("tags") or "")[:40],
            }
        )
    return out


def _llm_score(items: list[dict]) -> list[dict] | None:
    """分批打分(每批 30 条防输出超限);任一批失败 → 整体降级规则"""
    out: list[dict] = []
    for i in range(0, len(items), 30):
        batch = _llm_score_batch(items[i : i + 30])
        if batch is None:
            return None
        out.extend(batch)
    return out


def rescore_pending(limit: int = 60) -> dict:
    """用最新画像重新给「待用」素材打分(建议文案会按新身份改写)"""
    rows = db.conn().execute(
        "SELECT id, title, content, source FROM materials WHERE status='待用' "
        "ORDER BY score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    if not rows:
        return {"rescored": 0, "engine": "none"}
    items = [{"source": r["source"], "title": r["title"], "content": r["content"] or ""} for r in rows]
    scores = _llm_score(items)
    engine = "llm" if scores else "rule"
    c = db.conn()
    dropped = 0
    for r, sc in zip(rows, scores or [_rule_score(x) for x in items], strict=True):
        if (sc["score"] or 0) < SCORE_THRESHOLD:
            c.execute("UPDATE materials SET status='丢弃' WHERE id=?", (r["id"],))  # 重评后掉出严选线
            dropped += 1
            continue
        c.execute(
            "UPDATE materials SET relevance=?, conflict=?, save_potential=?, score=?, suggestion=?, tags=? WHERE id=?",
            (sc["relevance"], sc["conflict"], sc["save_potential"], sc["score"], sc["suggestion"], sc["tags"], r["id"]),
        )
    c.commit()
    return {"rescored": len(rows), "dropped": dropped, "engine": engine, "threshold": SCORE_THRESHOLD}


def fetch_and_score() -> dict:
    """抓取全部信源 → 打分 → 严选入库(≥7.5 分;url 去重幂等)"""
    db.init_db()
    # 分类自愈回填(强制覆盖,幂等)
    for src, cat in CATEGORY_OF_SOURCE.items():
        db.conn().execute("UPDATE materials SET category=? WHERE source=?", (cat, src))
    db.conn().commit()

    items = []
    for fn in (
        fetch_zhihu_hot, fetch_weibo_hot, fetch_baidu_hot, fetch_bili_hot,
        fetch_bili_philosophy, fetch_v2ex, fetch_hackernews, fetch_hitokoto,
    ):
        try:
            got = fn()
            for it in got:
                it.setdefault("category", CATEGORY_OF_SOURCE.get(it["source"], "热点爆款"))
            items.extend(got)
        except Exception as e:  # noqa: BLE001 - 单信源失败不阻断
            print(f"[materials] {fn.__name__} 失败: {e}")
    if not items:
        return {"fetched": 0, "new": 0, "engine": "none"}

    scores = _llm_score(items)
    engine = "llm" if scores else "rule"
    now = datetime.now().isoformat(timespec="seconds")
    c = db.conn()
    new_count = kept = 0
    for it, sc in zip(items, scores or [_rule_score(x) for x in items], strict=True):
        if (sc["score"] or 0) < SCORE_THRESHOLD:
            continue  # 严选:低于门槛不入库
        kept += 1
        cur = c.execute(
            """INSERT OR IGNORE INTO materials(source, category, title, content, url,
                 relevance, conflict, save_potential, score, suggestion, tags, status, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?, '待用', ?)""",
            (
                it["source"], it["category"], it["title"], it.get("content"), it["url"],
                sc["relevance"], sc["conflict"], sc["save_potential"], sc["score"],
                sc["suggestion"], sc["tags"], now,
            ),
        )
        new_count += cur.rowcount
    c.commit()
    return {"fetched": len(items), "kept": kept, "new": new_count, "engine": engine, "threshold": SCORE_THRESHOLD}
