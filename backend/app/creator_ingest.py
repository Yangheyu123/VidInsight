"""Parser for user-authorised Creator Center browser-capture events.

The browser bridge submits only JSON responses that the account owner has already
viewed.  API response shapes change over time, so this parser is deliberately
conservative: it records the raw event, extracts recognised metrics, and reports
unrecognised payloads for review instead of manufacturing values.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, AccountMetricSnapshot, SourceEvent, Video, VideoMetricSnapshot


def _number(value: Any) -> int | None:
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return None


def _rate(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed > 1:
        parsed /= 100
    return parsed if 0 <= parsed <= 1 else None


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _first(data: dict, *names: str) -> Any:
    for name in names:
        if data.get(name) is not None:
            return data[name]
    return None


async def infer_account(session: AsyncSession, raw: dict | list, fallback_account_id: str | None) -> Account | None:
    if fallback_account_id:
        return await session.scalar(select(Account).where(Account.id == fallback_account_id))
    candidates: set[str] = set()
    for node in _walk(raw):
        for name in ("open_id", "openId", "douyin_open_id"):
            value = node.get(name)
            if isinstance(value, str) and value:
                candidates.add(value)
    if not candidates:
        return None
    accounts = (await session.scalars(select(Account).where(Account.platform_open_id.in_(candidates)))).all()
    return accounts[0] if len(accounts) == 1 else None


async def parse_creator_event(session: AsyncSession, account: Account, event: SourceEvent) -> int:
    """Append recognised account/video snapshots and return their count."""
    raw = event.payload
    writes = 0
    follower_count: int | None = None
    for node in _walk(raw):
        follower_count = _number(_first(node, "follower_count", "fans_count", "fans", "follower_num"))
        if follower_count is not None:
            break
    if follower_count is not None:
        duplicate = await session.scalar(select(AccountMetricSnapshot.id).where(AccountMetricSnapshot.account_id == account.id, AccountMetricSnapshot.collected_at == event.captured_at, AccountMetricSnapshot.source == "computer_use"))
        if not duplicate:
            session.add(AccountMetricSnapshot(workspace_id=account.workspace_id, account_id=account.id, follower_count=follower_count, collected_at=event.captured_at, source="computer_use"))
            writes += 1

    seen_item_ids: set[str] = set()
    for node in _walk(raw):
        item_id = _first(node, "item_id", "itemId", "aweme_id", "awemeId", "video_id", "videoId")
        if not isinstance(item_id, (str, int)):
            continue
        item_id = str(item_id)
        if item_id in seen_item_ids:
            continue
        statistics = node.get("statistics") if isinstance(node.get("statistics"), dict) else node
        play_count = _number(_first(statistics, "play_count", "play", "play_num", "view_count", "view_num"))
        if play_count is None:
            continue
        seen_item_ids.add(item_id)
        video = await session.scalar(select(Video).where(Video.account_id == account.id, Video.platform_item_id == item_id))
        if not video:
            video = Video(workspace_id=account.workspace_id, account_id=account.id, platform_item_id=item_id, title=str(_first(node, "title", "desc", "caption") or "Untitled Douyin video"), published_at=event.captured_at)
            session.add(video)
            await session.flush()
        duplicate = await session.scalar(select(VideoMetricSnapshot.id).where(VideoMetricSnapshot.video_id == video.id, VideoMetricSnapshot.collected_at == event.captured_at, VideoMetricSnapshot.source == "computer_use"))
        if duplicate:
            continue
        session.add(VideoMetricSnapshot(workspace_id=account.workspace_id, video_id=video.id, play_count=play_count, like_count=_number(_first(statistics, "like_count", "digg_count", "like", "like_num")) or 0, comment_count=_number(_first(statistics, "comment_count", "comment", "comment_num")) or 0, share_count=_number(_first(statistics, "share_count", "share", "share_num")) or 0, forward_count=_number(_first(statistics, "forward_count", "forward", "forward_num")) or 0, completion_rate=_rate(_first(statistics, "completion_rate", "complete_rate", "finish_rate", "finish_percent")), completion_sample_count=_number(_first(statistics, "completion_sample_count", "finish_sample_count")), video_follow_conversion=_rate(_first(statistics, "video_follow_conversion", "follow_conversion", "follow_rate")), collected_at=event.captured_at, source="computer_use", quality="B"))
        writes += 1
    event.parse_status = "parsed" if writes else "unmatched"
    event.parse_details = {"records_written": writes, "recognised_video_count": len(seen_item_ids), "has_follower_snapshot": follower_count is not None}
    if writes:
        account.last_synced_at = event.captured_at
        account.last_sync_error = None
    return writes
