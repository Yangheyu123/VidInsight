from app.diagnosis import build_diagnoses


BASELINE = {
    "play_p30": 100,
    "play_p70": 1_000,
    "completion_p30": 0.3,
    "completion_p70": 0.7,
    "interaction_p30": 0.05,
    "follow_p30": 0.02,
}


def codes(metric: dict) -> set[str]:
    return {rule.code for rule, _ in build_diagnoses(metric, BASELINE)}


def test_low_completion_recommends_hook_and_pacing() -> None:
    assert "LOW_COMPLETION" in codes({"play_count": 500, "completion_rate": 0.2, "like_count": 20, "comment_count": 2, "share_count": 1, "video_follow_conversion": 0.03})


def test_high_play_low_engagement_is_detected() -> None:
    assert "HIGH_PLAY_LOW_ENGAGEMENT" in codes({"play_count": 1_000, "completion_rate": 0.5, "like_count": 10, "comment_count": 1, "share_count": 0, "video_follow_conversion": 0.03})


def test_low_play_high_completion_is_detected() -> None:
    assert "LOW_PLAY_HIGH_COMPLETION" in codes({"play_count": 99, "completion_rate": 0.7, "like_count": 5, "comment_count": 1, "share_count": 0, "video_follow_conversion": 0.03})


def test_low_play_low_completion_is_detected() -> None:
    assert "LOW_PLAY_LOW_COMPLETION" in codes({"play_count": 99, "completion_rate": 0.2, "like_count": 5, "comment_count": 1, "share_count": 0, "video_follow_conversion": 0.03})


def test_high_play_low_follow_is_detected_only_with_real_conversion() -> None:
    metric = {"play_count": 1_000, "completion_rate": 0.5, "like_count": 80, "comment_count": 5, "share_count": 5, "video_follow_conversion": 0.01}
    assert "HIGH_PLAY_LOW_FOLLOW" in codes(metric)
    metric["video_follow_conversion"] = None
    assert "HIGH_PLAY_LOW_FOLLOW" not in codes(metric)
