from datetime import datetime, timedelta
from typing import Any, Dict, List, Set, Tuple

from docleaner.api.core.job import JobStatus, JobType
from docleaner.api.services.clock import Clock
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
    datetime,
    datetime,
    int,
    int,
    List[Tuple[str, datetime, datetime, JobStatus, JobType]],
]:
    """Returns session details: The number of total associated jobs,
    the number of finished (success/error) jobs and a list with
    abbreviated job details (jid, created, updated, status, type)."""
    session = await repo.find_session(sid)
    if session is None:
        raise ValueError("Invalid session id")
    jobs = []
    finished_jobs = 0
    for job in await repo.find_jobs(sid):
        if job.status in [JobStatus.SUCCESS, JobStatus.ERROR]:
            finished_jobs += 1
        jobs.append((job.id, job.created, job.updated, job.status, job.type))
    return session.created, session.updated, len(jobs), finished_jobs, jobs


async def purge_sessions(purge_after: timedelta, repo: Repository) -> Set[str]:
    """Purges sessions after all jobs associated with a session are
    finished (in state SUCCESS or ERROR) and the session hasn't been updated
    within the specified timeframe (purge_after). Returns the identifiers of all deleted sessions."""
    purged_sessions = set()
    for session in await repo.find_sessions(not_updated_for=purge_after):
        # Do not purge sessions with unfinished jobs
        if await repo.find_jobs(
            sid=session.id,
            status=[JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CREATED],
        ):
            continue
        for job in await repo.find_jobs(
            sid=session.id, status=[JobStatus.SUCCESS, JobStatus.ERROR]
        ):
            await repo.delete_job(job.id)
        purged_sessions.add(session.id)
        await repo.delete_session(session.id)
    return purged_sessions
