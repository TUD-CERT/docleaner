from docleaner.api.core.job import Job, JobStatus
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import process_job_in_sandbox, Sandbox


class DummyJobQueue(JobQueue):
    """Dummy job queue that executes jobs in-process and synchronously (so not really a queue).
    Only recommended for unit testing."""

    def __init__(self, repo: Repository, sandbox: Sandbox):
        self._repo = repo
        self._sandbox = sandbox

    async def enqueue(self, job: Job) -> None:
        """Executes the job synchronously."""
        if job.id is None:
            raise ValueError("Only jobs with an ID can be enqueued")
        if job.status != JobStatus.CREATED:
            raise ValueError(
                f"Can't enqueue job {job.id} due to its invalid status {job.status}"
            )
        await self._repo.update_job(job.id, status=JobStatus.QUEUED)
        await process_job_in_sandbox(job.id, self._sandbox, self._repo)

    async def wait_for(self, job: Job) -> None:
        if job.id is None:
            raise ValueError("Only jobs with an ID can be awaited")
        while True:
            j = await self._repo.find_job(job.id)
            if j is None or j.status in [JobStatus.SUCCESS, JobStatus.ERROR]:
                break
