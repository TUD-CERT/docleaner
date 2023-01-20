from typing import Any, Dict, List, Tuple

from docleaner.api.core.job import JobStatus, JobType
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


async def create_session(repo: Repository) -> str:
    """Creates a new session and returns the session id."""
    return await repo.add_session()


async def await_session(sid: str, repo: Repository, queue: JobQueue) -> None:
    """Blocks until all jobs of the given session have been processed."""
    for job in await repo.find_jobs(sid):
        await queue.wait_for(job.id)


async def get_session(
    sid: str, repo: Repository
) -> Tuple[
    int,
    int,
    List[
        Tuple[
            str,
            JobStatus,
            JobType,
            List[str],
            Dict[str, Dict[str, Any]],
            Dict[str, Dict[str, Any]],
        ]
    ],
]:
    """Returns session details: The number of total associated jobs,
    the number of finished (success/error) jobs and a list with job details."""
    session = await repo.find_session(sid)
    if session is None:
        raise ValueError("Invalid session id")
    jobs = []
    finished_jobs = 0
    for job in await repo.find_jobs(sid):
        if job.status in [JobStatus.SUCCESS, JobStatus.ERROR]:
            finished_jobs += 1
        jobs.append(
            (
                job.id,
                job.status,
                job.type,
                job.log,
                job.metadata_src,
                job.metadata_result,
            )
        )
    return len(jobs), finished_jobs, jobs
