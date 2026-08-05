"""Approved data-source collection contract.

The scheduled worker can pull from an organisation-controlled adapter rather than
inventing platform metrics.  The adapter returns a JSON document containing an
``account_snapshot`` and zero or more ``videos`` in the documented import shape.
The adapter is where official Douyin, approved Computer Use, or a contract data
provider's field mapping belongs; this boundary keeps the core product auditable.
"""

from __future__ import annotations

from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Account, AccountMetricSnapshot, Video, VideoMetricSnapshot
from app.schemas import AccountSnapshotImport, VideoImport


async def pull_account_payload(account: Account) -> dict | None:
    settings = get_settings()
    if not settings.data_source_url:
        return None
    url = f"{settings.data_source_url.rstrip('/')}/accounts/{account.platform_open_id}/metrics"
    headers = {"Authorization": f"Bearer {settings.data_source_token}"} if settings.data_source_token else {}
    async with httpx.AsyncClient(timeout=settings.data_source_timeout_seconds, follow_redirects=False) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Data-source response must be a JSON object")
    return payload


async def persist_payload(session: AsyncSession, account: Account, payload: dict) -> int:
    """Validate and append provider data; existing snapshots are never overwritten."""
    writes = 0
    raw_account = payload.get("account_snapshot")
    if raw_account:
        account_item = AccountSnapshotImport.model_validate(raw_account)
        duplicate = await session.scalar(select(AccountMetricSnapshot.id).where(AccountMetricSnapshot.account_id == account.id, AccountMetricSnapshot.collected_at == account_item.collected_at, AccountMetricSnapshot.source == account_item.source))
        if not duplicate:
            session.add(AccountMetricSnapshot(workspace_id=account.workspace_id, account_id=account.id, follower_count=account_item.follower_count, collected_at=account_item.collected_at, source=account_item.source))
            writes += 1
    newest: datetime | None = None
    for raw_video in payload.get("videos", []):
        item = VideoImport.model_validate(raw_video)
        video = await session.scalar(select(Video).where(Video.account_id == account.id, Video.platform_item_id == item.platform_item_id))
        if not video:
            video = Video(workspace_id=account.workspace_id, account_id=account.id, platform_item_id=item.platform_item_id, title=item.title, published_at=item.published_at, duration_ms=item.duration_ms)
            session.add(video)
            await session.flush()
        duplicate = await session.scalar(select(VideoMetricSnapshot.id).where(VideoMetricSnapshot.video_id == video.id, VideoMetricSnapshot.collected_at == item.collected_at, VideoMetricSnapshot.source == item.source))
        if duplicate:
            continue
        session.add(VideoMetricSnapshot(workspace_id=account.workspace_id, video_id=video.id, play_count=item.play_count, like_count=item.like_count, comment_count=item.comment_count, share_count=item.share_count, forward_count=item.forward_count, completion_rate=item.completion_rate, completion_sample_count=item.completion_sample_count, video_follow_conversion=item.video_follow_conversion, collected_at=item.collected_at, source=item.source))
        newest = max(newest, item.collected_at) if newest else item.collected_at
        writes += 1
    if newest:
        account.last_synced_at = newest
        account.last_sync_error = None
    return writes
