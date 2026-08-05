import asyncio
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import select

from app.config import get_settings
from app.collectors import collect_douyin_business_video_metrics, persist_payload, pull_account_payload
from app.database import SessionLocal
from app.douyin import decrypt, encrypt, expiration, refresh_access_token
from app.models import Account, JobStatus, SyncJob

settings = get_settings()
celery_app = Celery("vidinsight", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_default_queue="collect",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    beat_schedule={
        "schedule-enabled-accounts": {"task": "app.tasks.celery_app.schedule_enabled_accounts", "schedule": 300.0},
        "refresh-douyin-tokens": {"task": "app.tasks.celery_app.refresh_due_douyin_tokens", "schedule": 3600.0},
    },
)


@celery_app.task(name="app.tasks.celery_app.schedule_enabled_accounts")
def schedule_enabled_accounts() -> int:
    return asyncio.run(_schedule_enabled_accounts())


@celery_app.task(name="app.tasks.celery_app.refresh_due_douyin_tokens")
def refresh_due_douyin_tokens() -> int:
    return asyncio.run(_refresh_due_douyin_tokens())


async def _refresh_due_douyin_tokens() -> int:
    now = datetime.now(timezone.utc)
    refreshed = 0
    async with SessionLocal() as session:
        accounts = (await session.scalars(select(Account).where(Account.refresh_token_encrypted.is_not(None), Account.token_expires_at.is_not(None), Account.token_expires_at <= now))).all()
        for account in accounts:
            try:
                payload = await refresh_access_token(decrypt(account.refresh_token_encrypted))
                account.access_token_encrypted = encrypt(payload["access_token"])
                account.token_expires_at = expiration(payload.get("expires_in"))
                if payload.get("refresh_token"):
                    account.refresh_token_encrypted = encrypt(payload["refresh_token"])
                    account.refresh_token_expires_at = expiration(payload.get("refresh_expires_in"))
                account.authorization_status = "active"
                account.last_sync_error = None
                refreshed += 1
            except Exception as exc:
                account.authorization_status = "expired"
                account.last_sync_error = f"Token refresh failed: {exc.__class__.__name__}"
        await session.commit()
    return refreshed


async def _schedule_enabled_accounts() -> int:
    async with SessionLocal() as session:
        accounts = (await session.scalars(select(Account).where(Account.collection_enabled.is_(True)))).all()
        job_ids: list[str] = []
        for account in accounts:
            job = SyncJob(workspace_id=account.workspace_id, account_id=account.id, trigger="scheduled", status=JobStatus.QUEUED.value)
            session.add(job)
            await session.flush()
            job_ids.append(job.id)
        await session.commit()
        for job_id in job_ids:
            collect_account.delay(job_id)
        return len(accounts)


@celery_app.task(name="app.tasks.celery_app.collect_account")
def collect_account(job_id: str) -> None:
    asyncio.run(_collect_account(job_id))


async def _collect_account(job_id: str) -> None:
    """Dispatch point for the approved Douyin/Computer Use/crawler adapters.

    External credentials and scopes are environment-owned; the task intentionally
    never fabricates mandatory metrics when no approved source adapter is available.
    """
    async with SessionLocal() as session:
        job = await session.scalar(select(SyncJob).where(SyncJob.id == job_id))
        if not job:
            return
        job.status = JobStatus.RUNNING.value
        await session.commit()
        account = await session.scalar(select(Account).where(Account.id == job.account_id))
        if not account or not account.collection_enabled:
            job.status = JobStatus.FAILED.value
            job.error_message = "Account is unavailable or collection is disabled."
        else:
            try:
                payload = await pull_account_payload(account)
                if payload is not None:
                    job.records_written = await persist_payload(session, account, payload)
                    job.status = JobStatus.SUCCEEDED.value
                    job.error_message = None
                else:
                    official_written = await collect_douyin_business_video_metrics(session, account)
                    if official_written is None:
                        job.status = JobStatus.PARTIAL.value
                        job.error_message = "No approved data-source adapter is configured."
                    else:
                        job.records_written = official_written
                        job.status = JobStatus.PARTIAL.value
                        job.error_message = "Official video metrics synced; completion and follow-conversion fields require an additional approved source."
            except Exception as exc:
                job.status = JobStatus.FAILED.value
                job.error_message = f"Collection failed: {exc.__class__.__name__}"
                account.last_sync_error = job.error_message
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
