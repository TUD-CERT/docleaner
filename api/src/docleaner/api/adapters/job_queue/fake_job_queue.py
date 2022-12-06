from docleaner.api.core.job import Job, JobStatus
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


class FakeJobQueue(JobQueue):
    """Fake job queue that pseudo-executes jobs in-process and synchronously.
    Only usable for fast unit testing."""

    def __init__(self, repo: Repository):
        self._repo = repo

    async def enqueue(self, job: Job) -> None:
        """Doesn't perform any real work, but updates the job status and simulates a result."""
        if job.id is None:
            raise ValueError("Only jobs with an ID can be enqueued")
        if job.status != JobStatus.CREATED:
            raise ValueError(
                f"Can't enqueue job {job.id} due to its invalid status {job.status}"
            )
        await self._repo.update_job(job.id, status=JobStatus.SUCCESS, result=b"RESULT")

    async def wait_for(self, job: Job) -> None:
        if job.id is None:
            raise ValueError("Only jobs with an ID can be awaited")
        while True:
            j = await self._repo.find_job(job.id)
            if j is None or j.status in [JobStatus.SUCCESS, JobStatus.ERROR]:
                break
