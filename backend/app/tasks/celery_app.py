import asyncio
from datetime import datetime, timezone

from celery import Celery
from sqlalchemy import select

from app.config import get_settings
from app.collectors import persist_payload, pull_account_payload
from app.database import SessionLocal
from app.models import Account, JobStatus, SyncJob

settings = get_settings()
celery_app = Celery("vidinsight", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_default_queue="collect",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    beat_schedule={"schedule-enabled-accounts": {"task": "app.tasks.celery_app.schedule_enabled_accounts", "schedule": 300.0}},
)


@celery_app.task(name="app.tasks.celery_app.schedule_enabled_accounts")
def schedule_enabled_accounts() -> int:
    return asyncio.run(_schedule_enabled_accounts())


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
                if payload is None:
                    job.status = JobStatus.PARTIAL.value
                    job.error_message = "No approved data-source adapter is configured."
                else:
                    job.records_written = await persist_payload(session, account, payload)
                    job.status = JobStatus.SUCCEEDED.value
                    job.error_message = None
            except Exception as exc:
                job.status = JobStatus.FAILED.value
                job.error_message = f"Collection failed: {exc.__class__.__name__}"
                account.last_sync_error = job.error_message
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
