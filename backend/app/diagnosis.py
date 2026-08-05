from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosisRule:
    code: str
    title: str
    suggestion: str


RULES = {
    "LOW_COMPLETION": DiagnosisRule("LOW_COMPLETION", "完播偏低", "开头钩子或视频节奏可能需要优化；检查前 3 秒承诺、信息密度和冗余段落。"),
    "HIGH_PLAY_LOW_ENGAGEMENT": DiagnosisRule("HIGH_PLAY_LOW_ENGAGEMENT", "曝光较好，互动承接偏弱", "可增加明确提问、评论引导或可讨论观点，提升互动设计。"),
    "LOW_PLAY_HIGH_COMPLETION": DiagnosisRule("LOW_PLAY_HIGH_COMPLETION", "内容承接较好，曝光不足", "优先检查封面标题、选题受众和首屏信息。"),
    "LOW_PLAY_LOW_COMPLETION": DiagnosisRule("LOW_PLAY_LOW_COMPLETION", "选题与内容承接都待优化", "建议同时复核选题、开场和内容结构是否匹配目标受众。"),
    "HIGH_PLAY_LOW_FOLLOW": DiagnosisRule("HIGH_PLAY_LOW_FOLLOW", "流量未充分转化为关注", "可强化人设识别、系列价值和关注理由。"),
}


def build_diagnoses(metric: dict[str, float], baseline: dict[str, float]) -> list[tuple[DiagnosisRule, dict]]:
    play = metric["play_count"]
    completion = metric["completion_rate"]
    interaction_rate = (metric["like_count"] + metric["comment_count"] + metric["share_count"]) / play if play else 0
    results: list[tuple[DiagnosisRule, dict]] = []
    high_play = play >= baseline["play_p70"]
    low_play = play < baseline["play_p30"]
    high_completion = completion >= baseline["completion_p70"]
    low_completion = completion < baseline["completion_p30"]
    if low_completion:
        results.append((RULES["LOW_COMPLETION"], {"completion_rate": completion, "threshold": baseline["completion_p30"]}))
    if high_play and interaction_rate < baseline["interaction_p30"]:
        results.append((RULES["HIGH_PLAY_LOW_ENGAGEMENT"], {"play_count": play, "interaction_rate": interaction_rate, "threshold": baseline["interaction_p30"]}))
    if low_play and high_completion:
        results.append((RULES["LOW_PLAY_HIGH_COMPLETION"], {"play_count": play, "completion_rate": completion}))
    if low_play and low_completion:
        results.append((RULES["LOW_PLAY_LOW_COMPLETION"], {"play_count": play, "completion_rate": completion}))
    follow_conversion = metric.get("video_follow_conversion")
    if high_play and follow_conversion is not None and follow_conversion < baseline["follow_p30"]:
        results.append((RULES["HIGH_PLAY_LOW_FOLLOW"], {"play_count": play, "video_follow_conversion": follow_conversion, "threshold": baseline["follow_p30"]}))
    return results
