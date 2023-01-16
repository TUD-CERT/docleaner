import asyncio
from typing import List, Literal, Set, Union

from docleaner.api.core.job import Job, JobStatus
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import process_job_in_sandbox


class AsyncJobQueue(JobQueue):
    """In-process job queue using Python's native asyncio library.
    Executes each job in its own coroutine."""

    def __init__(
        self,
        repo: Repository,
        job_types: List[SupportedJobType],
        max_concurrent_jobs: int,
    ):
        self._ev_shutdown = asyncio.Event()
        self._repo = repo
        self._job_types = job_types
        self._max_concurrent_jobs = max_concurrent_jobs
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._worker_task = asyncio.create_task(self._worker())

    async def enqueue(self, job: Job) -> None:
        """Creates a new coroutine for job execution."""
        if job.id is None:
            raise ValueError("Only jobs with an ID can be enqueued")
        if job.status != JobStatus.CREATED:
            raise ValueError(
                f"Can't enqueue job {job.id} due to its invalid status {job.status}"
            )
        await self._repo.update_job(job.id, status=JobStatus.QUEUED)
        await self._queue.put(job)

    async def wait_for(self, jid: str) -> None:
        job = await self._repo.find_job(jid)
        if job is None:
            raise ValueError(f"A job with jid {jid} does not exist")
        while True:
            if job is None or job.status in [JobStatus.SUCCESS, JobStatus.ERROR]:
                break
            job = await self._repo.find_job(jid)
            await asyncio.sleep(0.1)

    async def shutdown(self) -> None:
        self._ev_shutdown.set()
        await self._worker_task

    async def _worker(self) -> None:
        running_tasks: Set[asyncio.Task[None]] = set()
        await_shutdown: asyncio.Task[Union[Literal[True], Job]] = asyncio.create_task(
            self._ev_shutdown.wait()
        )
        while True:
            # Garbage-collect finished tasks
            running_tasks = set(filter(lambda t: not t.done(), running_tasks))
            if len(running_tasks) >= self._max_concurrent_jobs:
                # Concurrent job limit reached, wait for a job to finish
                completed_tasks, _ = await asyncio.wait(
                    running_tasks, return_when=asyncio.FIRST_COMPLETED
                )
                for t in completed_tasks:
                    running_tasks.remove(t)
            else:
                await_job: asyncio.Task[
                    Union[Literal[True], Job]
                ] = asyncio.create_task(self._queue.get())
                done, pending = await asyncio.wait(
                    [await_job, await_shutdown], return_when=asyncio.FIRST_COMPLETED
                )
                if await_job in done:
                    job = await_job.result()
                    assert isinstance(job, Job)
                    running_tasks.add(
                        asyncio.create_task(
                            process_job_in_sandbox(job.id, self._job_types, self._repo)
                        )
                    )
                    self._queue.task_done()
                else:
                    await_job.cancel()
                if await_shutdown in done:
                    # Graceful wait for running tasks to finish
                    for t in running_tasks:
                        await t
                    break
