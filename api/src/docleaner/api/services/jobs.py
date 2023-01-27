from datetime import timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from docleaner.api.core.job import JobStatus, JobType
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
    sid: Optional[str] = None,
) -> Tuple[str, JobType]:
    """Creates and schedules a job to clean the given source document.
    Can optionally be added to a session by providing a session id (sid).
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
    jid = await repo.add_job(source, source_name, source_type, sid)
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
    JobStatus,
    JobType,
    List[str],
    Dict[str, Dict[str, Any]],
    Dict[str, Dict[str, Any]],
    Optional[str],
]:
    """Returns details for the job identified by jid."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"A job with jid {jid} does not exist")
    return (
        job.status,
        job.type,
        job.log,
        job.metadata_src,
        job.metadata_result,
        job.session_id,
    )


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


async def get_job_stats(repo: Repository) -> Tuple[int, int, int, int, int, int]:
    """Returns the number of overall total and currently registered jobs differentiated by their status:
    # total jobs ever seen, # created, # queued, # running, # successful, # error."""
    result: Dict[JobStatus, int] = {
        JobStatus.CREATED: 0,
        JobStatus.QUEUED: 0,
        JobStatus.RUNNING: 0,
        JobStatus.SUCCESS: 0,
        JobStatus.ERROR: 0,
    }
    for job in await repo.find_jobs():
        result[job.status] += 1
    return (
        await repo.get_total_job_count(),
        result[JobStatus.CREATED],
        result[JobStatus.QUEUED],
        result[JobStatus.RUNNING],
        result[JobStatus.SUCCESS],
        result[JobStatus.ERROR],
    )


async def purge_jobs(purge_after: timedelta, repo: Repository) -> Set[str]:
    """Deletes all finished standalone (not associated with a session) jobs that haven't been
    updated within the timeframe specified by purge_after. Returns the identifiers of all deleted jobs."""
    purged_jobs = set()
    for job in await repo.find_jobs(
        status=[JobStatus.SUCCESS, JobStatus.ERROR], not_updated_for=purge_after
    ):
        if job.session_id is None:
            purged_jobs.add(job.id)
            await repo.delete_job(job.id)
    return purged_jobs
