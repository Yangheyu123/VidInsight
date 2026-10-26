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


# ---------------- 打分 ----------------

RULE_KEYS = {
    "relevance": ["哲学", "意义", "自由", "思考", "认知", "尼采", "叔本华", "存在", "虚无", "理性",
                   "孤独", "迷茫", "焦虑", "内卷", "人生", "时间", "选择", "真相", "思考", "智慧", "幸福"],
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


def _llm_score(items: list[dict]) -> list[dict] | None:
    """批量打分:返回与入参等长的评分列表;失败返回 None"""
    listing = "\n".join(
        f"{i}. {it['title']} | {(it.get('content') or '')[:60]} | 来源:{it['source']}"
        for i, it in enumerate(items)
    )
    system = (
        "你是短视频选题评估器。创作者赛道:青年思辨哲学短视频,受众18-23岁男性,目标高收藏率。"
        '对每条素材输出JSON:{"i":序号,"relevance":赛道相关性0-10,"conflict":冲突感/反差0-10,'
        '"save_potential":被收藏潜力0-10,"suggestion":"一句话改写建议(怎么变成思辨类选题)","tags":"标签,逗号分隔"}。'
        "只输出JSON数组,不要其他文字。"
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


def fetch_and_score() -> dict:
    """抓取全部信源 → 打分 → 入库(url 去重幂等)"""
    db.init_db()
    items = []
    for fn in (fetch_zhihu_hot, fetch_weibo_hot, fetch_hitokoto):
        try:
            items.extend(fn())
        except Exception as e:  # noqa: BLE001 - 单信源失败不阻断
            print(f"[materials] {fn.__name__} 失败: {e}")
    if not items:
        return {"fetched": 0, "new": 0, "engine": "none"}

    scores = _llm_score(items)
    engine = "llm" if scores else "rule"
    now = datetime.now().isoformat(timespec="seconds")
    c = db.conn()
    new_count = 0
    for it, sc in zip(items, scores or [_rule_score(x) for x in items], strict=True):
        cur = c.execute(
            """INSERT OR IGNORE INTO materials(source, title, content, url,
                 relevance, conflict, save_potential, score, suggestion, tags, status, created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?, '待用', ?)""",
            (
                it["source"], it["title"], it.get("content"), it["url"],
                sc["relevance"], sc["conflict"], sc["save_potential"], sc["score"],
                sc["suggestion"], sc["tags"], now,
            ),
        )
        new_count += cur.rowcount
    c.commit()
    return {"fetched": len(items), "new": new_count, "engine": engine}
