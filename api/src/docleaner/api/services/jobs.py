from datetime import timedelta
from typing import Any, Dict, List, Set, Tuple

from docleaner.api.core.job import JobStatus, JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.repository import Repository


async def create_job(
    source: bytes,
    source_name: str,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[SupportedJobType],
) -> Tuple[str, JobType]:
    """Creates and schedules a job to clean the given source document.
    Returns the job id and (identified) type."""
    # Identify source MIME type
    source_mimetype = file_identifier.identify(source)
    source_type = None
    for jt in job_types:
        if source_mimetype in jt.mimetypes:
            source_type = jt.type
            break
    if source_type is None:
        raise ValueError("Unsupported document type")
    # Create and schedule job
    jid = await repo.add_job(source, source_name, source_type)
    job = await repo.find_job(jid)
    if job is None:
        raise RuntimeError(f"Race condition: added job {jid} is now gone")
    await queue.enqueue(job)
    return jid, source_type


async def await_job(
    jid: str, repo: Repository, queue: JobQueue
) -> Tuple[
    JobStatus, JobType, List[str], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]
]:
    """Blocks until the job identified by jid has been processed.
    Returns the job's final status, type, log data, source metadata and resulting metadata."""
    await queue.wait_for(jid)
    job = await repo.find_job(jid)
    if job is not None:
        return job.status, job.type, job.log, job.metadata_src, job.metadata_result
    raise RuntimeError(f"Race condition: awaited job {jid} is now gone")


async def get_job(
    jid: str, repo: Repository
) -> Tuple[
    JobStatus, JobType, List[str], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]
]:
    """Returns details for the job identified by jid."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"A job with jid {jid} does not exist")
    return job.status, job.type, job.log, job.metadata_src, job.metadata_result


async def get_job_result(jid: str, repo: Repository) -> Tuple[bytes, str]:
    """Retrieves the result and document name for a successfully completed job identified by jid."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"A job with jid {jid} does not exist")
    if job.status != JobStatus.SUCCESS:
        raise ValueError(
            f"Job with jid {jid} didn't complete (yet), current state is {job.status}"
        )
    return job.result, job.name


async def purge_jobs(delta: timedelta, repo: Repository, clock: Clock) -> Set[str]:
    """Deletes all jobs that haven't been updated within the timeframe specified by delta.
    Returns the identifiers of all deleted jobs."""
    now = clock.now()
    purged_jobs = set()
    for job in await repo.find_jobs():
        if (
            job.status in [JobStatus.SUCCESS, JobStatus.ERROR]
            and now - job.updated > delta
        ):
            purged_jobs.add(job.id)
            await repo.delete_job(job.id)
    return purged_jobs
