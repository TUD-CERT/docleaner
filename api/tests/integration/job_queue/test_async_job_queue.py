import asyncio
from typing import List

from docleaner.api.adapters.job_queue.async_job_queue import AsyncJobQueue
from docleaner.api.adapters.sandbox.dummy_sandbox import DummySandbox
from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.jobs import await_job
from docleaner.api.services.repository import Repository


async def test_enforce_concurrent_job_limit(
    repo: Repository, job_types: List[SupportedJobType], sample_pdf: bytes
) -> None:
    """Attempting to enqueue more jobs than the async job queue was configured
    to run concurrently results in excess jobs remaining in QUEUED state."""
    sandbox = DummySandbox()
    job_types[0].sandbox = sandbox
    queue = AsyncJobQueue(repo, job_types, 3)
    jids = [await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF) for i in range(5)]
    # Stop processing and enqueue all five jobs
    await sandbox.halt()
    for jid in jids:
        job = await repo.find_job(jid)
        assert isinstance(job, Job)
        await queue.enqueue(job)
    await asyncio.sleep(0.1)  # Give jobs some time to start
    # Only three jobs should be RUNNING, the remaining QUEUED
    running_jobs = []
    queued_jobs = []
    for job in await repo.find_jobs():
        if job.status == JobStatus.RUNNING:
            running_jobs.append(job)
        elif job.status == JobStatus.QUEUED:
            queued_jobs.append(job)
    assert len(running_jobs) == 3
    assert len(queued_jobs) == 2
    # Release jobs
    await sandbox.resume()
    for jid in jids:
        await await_job(jid, repo)
    await queue.shutdown()
    for job in await repo.find_jobs():
        assert job.status == JobStatus.SUCCESS
