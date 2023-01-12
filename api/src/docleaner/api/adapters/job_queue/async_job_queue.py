import asyncio
from typing import List

from docleaner.api.core.job import Job, JobStatus
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import process_job_in_sandbox


class AsyncJobQueue(JobQueue):
    """In-process job queue using Python's native asyncio library.
    Executes each job in its own coroutine."""

    def __init__(self, repo: Repository, job_types: List[SupportedJobType]):
        self._repo = repo
        self._job_types = job_types

    async def enqueue(self, job: Job) -> None:
        """Creates a new coroutine for job execution."""
        if job.id is None:
            raise ValueError("Only jobs with an ID can be enqueued")
        if job.status != JobStatus.CREATED:
            raise ValueError(
                f"Can't enqueue job {job.id} due to its invalid status {job.status}"
            )
        await self._repo.update_job(job.id, status=JobStatus.QUEUED)
        asyncio.create_task(process_job_in_sandbox(job.id, self._job_types, self._repo))

    async def wait_for(self, jid: str) -> None:
        job = await self._repo.find_job(jid)
        if job is None:
            raise ValueError(f"A job with jid {jid} does not exist")
        while True:
            if job is None or job.status in [JobStatus.SUCCESS, JobStatus.ERROR]:
                break
            job = await self._repo.find_job(jid)
            await asyncio.sleep(0.1)
