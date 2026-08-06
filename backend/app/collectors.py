"""Approved data-source collection contract.

The scheduled worker can pull from an organisation-controlled adapter rather than
inventing platform metrics.  The adapter returns a JSON document containing an
``account_snapshot`` and zero or more ``videos`` in the documented import shape.
The adapter is where official Douyin, approved Computer Use, or a contract data
provider's field mapping belongs; this boundary keeps the core product auditable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.douyin import decrypt
from app.models import Account, AccountMetricSnapshot, Video, VideoMetricSnapshot
from app.schemas import AccountSnapshotImport, VideoImport


def _validated_base_url(base_url: str, settings: Settings, *, require_crawler_allowlist: bool = False) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Approved data sources must use an HTTPS URL")
    if require_crawler_allowlist and parsed.hostname.lower() not in settings.crawler_domain_list:
        raise ValueError("Crawler source host is not in CRAWLER_ALLOWED_DOMAINS")
    return base_url.rstrip("/")


async def pull_account_payload(account: Account, base_url: str | None = None, token: str | None = None, *, source: str = "contract_api", require_crawler_allowlist: bool = False) -> dict | None:
    """Pull one validated contract payload from an organisation-approved worker.

    Computer Use and crawler workers are deliberately external bridges: this API
    never receives a platform password, cookie, CAPTCHA response, or proxy pool.
    They must return the same append-only import contract as a licensed provider.
    """
    settings = get_settings()
    base_url = base_url or settings.data_source_url
    token = token if token is not None else settings.data_source_token
    if not base_url:
        return None
    url = f"{_validated_base_url(base_url, settings, require_crawler_allowlist=require_crawler_allowlist)}/accounts/{account.platform_open_id}/metrics"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(timeout=settings.data_source_timeout_seconds, follow_redirects=False) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Data-source response must be a JSON object")
    _force_payload_source(payload, source)
    return payload


def _force_payload_source(payload: dict, source: str) -> None:
    """Make provenance server-controlled rather than trusting a worker payload."""
    account_snapshot = payload.get("account_snapshot")
    if isinstance(account_snapshot, dict):
        account_snapshot["source"] = source
    for video in payload.get("videos", []):
        if isinstance(video, dict):
            video["source"] = source


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


BUSINESS_VIDEO_QUERY_URL = "https://open.douyin.com/api/apps/v1/video_bc/query/"
DOUYIN_VIDEO_LIST_URL = "https://open.douyin.com/video/list/"


async def collect_douyin_authorized_video_metrics(session: AsyncSession, account: Account) -> int | None:
    """Collect real-time public video metrics using the account's OAuth token.

    This is the standard path after the application has been granted
    ``video.list``.  Douyin does not expose completion rate or video-level follow
    conversion from this endpoint; those remain null rather than fabricated.
    """
    if not account.access_token_encrypted or account.authorization_status != "active":
        return None
    now = datetime.now(timezone.utc)
    written = 0
    try:
        token = decrypt(account.access_token_encrypted)
    except ValueError as exc:
        raise ValueError("Stored Douyin token cannot be decrypted") from exc
    async with httpx.AsyncClient(timeout=get_settings().data_source_timeout_seconds, follow_redirects=False) as client:
        response = await client.get(DOUYIN_VIDEO_LIST_URL, headers={"access-token": token, "content-type": "application/json"})
        response.raise_for_status()
        payload = response.json()
    data = payload.get("data") or {}
    if data.get("error_code", 0) != 0 or payload.get("extra", {}).get("error_code", 0) != 0:
        raise ValueError(f"Douyin video list failed: {data.get('error_code') or payload.get('extra', {}).get('error_code')}")
    for item in data.get("list", []):
        item_id = item.get("item_id")
        statistics = item.get("statistics") or {}
        if not item_id or not statistics:
            continue
        published_at = datetime.fromtimestamp(int(item.get("create_time") or now.timestamp()), tz=timezone.utc)
        video = await session.scalar(select(Video).where(Video.account_id == account.id, Video.platform_item_id == item_id))
        if not video:
            video = Video(workspace_id=account.workspace_id, account_id=account.id, platform_item_id=item_id, title=item.get("title") or "Untitled Douyin video", published_at=published_at, cover_url=item.get("cover"))
            session.add(video)
            await session.flush()
        duplicate = await session.scalar(select(VideoMetricSnapshot.id).where(VideoMetricSnapshot.video_id == video.id, VideoMetricSnapshot.collected_at == now, VideoMetricSnapshot.source == "douyin_api"))
        if duplicate:
            continue
        session.add(VideoMetricSnapshot(workspace_id=account.workspace_id, video_id=video.id, play_count=int(statistics.get("play_count", 0)), like_count=int(statistics.get("digg_count", 0)), comment_count=int(statistics.get("comment_count", 0)), share_count=int(statistics.get("share_count", 0)), forward_count=int(statistics.get("forward_count", 0)), completion_rate=None, completion_sample_count=None, video_follow_conversion=None, collected_at=now, source="douyin_api", quality="A"))
        written += 1
    if written:
        account.last_synced_at = now
        account.last_sync_error = None
    return written


async def collect_douyin_business_video_metrics(session: AsyncSession, account: Account) -> int | None:
    """Append fields returned by the documented经营授权 video-query API.

    The endpoint does not provide completion or follow conversion, so those remain
    null.  Returning ``None`` signals that this adapter is not configured.
    """
    settings = get_settings()
    if not settings.douyin_business_access_token:
        return None
    videos = (await session.scalars(select(Video).where(Video.account_id == account.id))).all()
    if not videos:
        return 0
    token = settings.douyin_business_access_token
    now = datetime.now(timezone.utc)
    written = 0
    async with httpx.AsyncClient(timeout=settings.data_source_timeout_seconds, follow_redirects=False) as client:
        for offset in range(0, len(videos), 20):
            batch = videos[offset:offset + 20]
            response = await client.post(BUSINESS_VIDEO_QUERY_URL, params={"open_id": account.platform_open_id}, headers={"access-token": token, "content-type": "application/json"}, json={"item_ids": [video.platform_item_id for video in batch]})
            response.raise_for_status()
            payload = response.json()
            if payload.get("err_no", 0) != 0:
                raise ValueError(f"Douyin business video query failed: {payload.get('err_no')}")
            result = payload.get("data", {}).get("data", {}).get("list", [])
            video_by_item = {video.platform_item_id: video for video in batch}
            for item in result:
                video = video_by_item.get(item.get("item_id"))
                statistics = item.get("statistics") or {}
                if not video or not statistics:
                    continue
                duplicate = await session.scalar(select(VideoMetricSnapshot.id).where(VideoMetricSnapshot.video_id == video.id, VideoMetricSnapshot.collected_at == now, VideoMetricSnapshot.source == "douyin_api"))
                if duplicate:
                    continue
                session.add(VideoMetricSnapshot(workspace_id=account.workspace_id, video_id=video.id, play_count=int(statistics.get("play_count", 0)), like_count=int(statistics.get("digg_count", 0)), comment_count=int(statistics.get("comment_count", 0)), share_count=int(statistics.get("share_count", 0)), forward_count=int(statistics.get("forward_count", 0)), completion_rate=None, completion_sample_count=None, video_follow_conversion=None, collected_at=now, source="douyin_api", quality="B"))
                written += 1
    if written:
        account.last_synced_at = now
        account.last_sync_error = None
    return written
