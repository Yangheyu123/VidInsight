from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import AccountDataImport, VideoImport


def video(index: int) -> dict:
    return {"platform_item_id": str(index), "title": "sample", "published_at": datetime.now(timezone.utc), "play_count": 1, "like_count": 1, "comment_count": 0, "forward_count": 0, "completion_rate": 0.5, "collected_at": datetime.now(timezone.utc)}


def test_batch_import_accepts_up_to_500_video_snapshots() -> None:
    payload = AccountDataImport(videos=[VideoImport(**video(index)) for index in range(500)])
    assert len(payload.videos) == 500


def test_batch_import_rejects_more_than_500_video_snapshots() -> None:
    with pytest.raises(ValidationError):
        AccountDataImport(videos=[VideoImport(**video(index)) for index in range(501)])
