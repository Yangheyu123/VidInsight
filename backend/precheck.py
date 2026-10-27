"""剧本发布前预检:规则层(本地秒判) + LLM层(数据铁律对照)。

插在用户产线中间:网页AI产出剧本 → 粘贴预检 → 通过再喂 agent。
不依赖产线任何代码,纯文本进出。
"""

from __future__ import annotations

import json
import re

from . import knowledge
from .llm import chat

# ---------------------------------------------------------------- 规则层

SPEED = 4.5  # 字/秒(产线 METHODOLOGY 口径)
DUR_MIN, DUR_MAX, DUR_HARD = 45, 55, 60


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[。!?!?;;\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def rule_check(text: str) -> dict:
    """本地启发式:时长/结尾/开场/碎句。返回 {items, stats}。"""
    sents = _sentences(text)
    n_chars = len(re.sub(r"\s", "", text))
    est_sec = round(n_chars / SPEED, 1)
    items: list[dict] = []

    # 时长
    if n_chars < 120:
        items.append({"severity": "high", "location": "全文",
                      "problem": f"全文仅 {n_chars} 字(≈{est_sec}s),低于 45s 下限,内容撑不满 Hook-展开-结尾 结构",
                      "fix": "补足到 200~250 字(45~55s):钩子后加反向冲击段,或思辨段加一层"})
    elif n_chars > int(DUR_HARD * SPEED):
        items.append({"severity": "high", "location": "全文",
                      "problem": f"全文 {n_chars} 字(≈{est_sec}s)超过 60s 硬上限,完播会被时长拖死",
                      "fix": f"砍到 {int(DUR_MIN*SPEED)}~{int(DUR_MAX*SPEED)} 字:删纯说理句,保留具象案例"})
    elif not (int(DUR_MIN * SPEED) <= n_chars <= int(DUR_MAX * SPEED)):
        items.append({"severity": "low", "location": "全文",
                      "problem": f"{n_chars} 字(≈{est_sec}s)略偏离 45~55s 甜区",
                      "fix": "微调即可,不强制"})

    # 开场(首句):数据铁律——提问式开场=5s完播全账号倒数
    if sents:
        first = sents[0]
        is_question = bool(re.search(r"[??]$", first)) or ("吗" in first[-6:])
        concrete = bool(re.search(r"\d|[一九二三四五六七八九十百千]|\d{4}年|岁|个|位", first))
        if is_question and not concrete:
            items.append({"severity": "high", "location": "开场·第1句",
                          "problem": "首句是纯提问开场——本账号数据:提问式开场 5s 完播全账号倒数,纯提问开场从未跑出过池",
                          "fix": "改成具象开场:人物+年份+动作/具体物(如「1990年,一个31岁的天文台员工…」),问题挪到第2-3句"})
        elif not concrete:
            items.append({"severity": "mid", "location": "开场·第1句",
                          "problem": "首句没检出数字/年份/量词等具象信号,疑似抽象对仗开场(对照失败案例:0个具体名词)",
                          "fix": "往首句塞一个具体锚点:年份、岁数、地点或物件"})

    # 结尾:评论钩子(问句+二元选择)
    tail = " ".join(sents[-3:]) if sents else ""
    has_q = bool(re.search(r"[??]", tail))
    has_choice = any(k in tail for k in ("还是", "你会", "选", "如果是你"))
    if not has_q:
        items.append({"severity": "mid", "location": "结尾·末3句",
                      "problem": "结尾没有问句,缺评论钩子(互动三率里评论率直接受此驱动)",
                      "fix": "结尾上屏一个二元选择题问句(如「你选清醒的痛苦,还是麻木的快乐?」)"})
    elif has_q and not has_choice:
        items.append({"severity": "low", "location": "结尾·末3句",
                      "problem": "结尾有问句但不是二元选择题,评论门槛略高",
                      "fix": "改成 A 还是 B 的二选一,让观众站队即可评论"})

    # 碎句(平均句长过低 = 断句怪/TTS断死风险)
    if sents:
        avg = n_chars / max(len(sents), 1)
        if avg < 9 and len(sents) >= 5:
            items.append({"severity": "mid", "location": "全文断句",
                          "problem": f"平均句长 {avg:.1f} 字,碎句过多——TTS 逐句断死/断句怪的根源",
                          "fix": "按完整自然句合并(产线规则:卡文本必须完整自然句)"})

    return {
        "items": items,
        "stats": {"chars": n_chars, "sentences": len(sents), "est_seconds": est_sec},
    }


# ---------------------------------------------------------------- LLM层

# L3 兜底铁律:仅在检索不到足够证据时作为 prior 使用(账号日更,知识库才是主判据)
IRON_LAWS = """通用铁律(兜底 prior,若与下方真实证据冲突,以证据为准):
1. 开场具象:人物/年份/动作/具体物;纯提问开场 5s 完播历来垫底。
2. 钩子 0-3s,5-10s 反向冲击;每 12-15s 一次小冲突;禁平铺说理。
3. 片长 45-55s(上限 60s),约 4.5 字/秒;钩子段快,思辨/结尾段慢。
4. 结尾二元选择题问句(评论钩子)。
受众:18-23岁 45%,男:女 8:2,程序员/思辨爱好者。"""

LLM_INSTRUCTION = """你是短视频剧本质检官。基于「真实数据证据」评审剧本——证据是本账号真实发生过的事实(带时效),
引用证据时注意新旧:越新的数据权重越高,老证据只做背景。
只输出一个 JSON 对象,不要 markdown 代码块,格式:
{"score": 0-100整数, "verdict": "可发|小改|重写",
 "issues": [{"severity":"high|mid|low","location":"开场第1句/钩子/中段/结尾/全文","problem":"一句话问题(可引用证据数据)","fix":"可直接照抄的改法(给出具体例句)"}],
 "strengths": ["保留的亮点,最多3条"],
 "rewrite_hook": "若开场有问题,给一个可用的具象开场句;无问题给空串",
 "rewrite": "完整修正稿全文(直接应用所有fix后的可发布版本,保持原意与45-55s时长;verdict=可发时返回原稿)"}
问题定位到具体句子,fix 必须给可直接替换的例句。rewrite 必须是完整剧本,不许只写改动说明。"""


def _evidence_block(evidence: list[dict]) -> str:
    if not evidence:
        return "(知识库暂无证据,按兜底铁律评审)"
    lines = ["真实数据证据(按新旧排序,越新权重越高):"]
    for i, e in enumerate(evidence, 1):
        kind = {"own_video": "自有视频", "bench": "对标爆款", "report": "报告结论"}.get(e["kind"], e["kind"])
        age = f"{e['age_days']}天前" if e["age_days"] else "近期"
        lines.append(f"[{i}]({kind}·{age}) {e['title']}: {e['text']}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def llm_check(text: str, evidence: list[dict]) -> dict | None:
    """GLM 基于检索证据深检。失败返回 None(规则层结果仍可用)。"""
    try:
        raw = chat(
            LLM_INSTRUCTION,
            f"{_evidence_block(evidence)}\n\n{IRON_LAWS}\n\n待检剧本:\n{text}",
            temperature=0.3,
            max_tokens=16384,
        )
    except Exception:
        return None
    data = _extract_json(raw or "")
    if not isinstance(data, dict):
        return None
    data.setdefault("issues", [])
    data.setdefault("strengths", [])
    data.setdefault("rewrite_hook", "")
    data.setdefault("rewrite", "")
    return data


# ---------------------------------------------------------------- 汇总

SEV_ORDER = {"high": 0, "mid": 1, "low": 2}


def precheck(text: str) -> dict:
    """入口:规则层 + LLM层合并,输出体检单。"""
    text = (text or "").strip()
    if len(text) < 20:
        return {"error": "剧本太短(至少 20 字)"}

    rules = rule_check(text)

    # 聚合账号证据(GLM直读模式:近30天自有战绩+爆款脚本+最新报告结论)
    try:
        evidence = knowledge.gather_evidence()
    except Exception:
        evidence = []

    llm = llm_check(text, evidence)

    items = list(rules["items"])
    if llm:
        items.extend(llm.get("issues") or [])
        # 同 severity 排序;规则层问题保留在前(LLM 会重复点名的合并展示无妨)
    items.sort(key=lambda x: SEV_ORDER.get(x.get("severity"), 3))

    highs = sum(1 for i in items if i.get("severity") == "high")
    if llm and llm.get("score") is not None:
        score = llm["score"]
        verdict = llm.get("verdict") or ("重写" if highs >= 2 else "小改" if items else "可发")
    else:
        score = max(30, 100 - highs * 25 - sum(1 for i in items if i.get("severity") == "mid") * 10)
        verdict = "重写" if highs >= 2 else ("小改" if items else "可发")

    return {
        "score": score,
        "verdict": verdict,
        "items": items,
        "strengths": (llm or {}).get("strengths") or [],
        "rewrite_hook": (llm or {}).get("rewrite_hook") or "",
        "rewrite": (llm or {}).get("rewrite") or "",
        "evidence": evidence,
        "stats": rules["stats"],
        "llm_ok": llm is not None,
    }
