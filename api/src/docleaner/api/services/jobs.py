import asyncio
from datetime import timedelta
import logging
from typing import Dict, List, Optional, Set, Tuple

from docleaner.api.core.job import JobParams, JobStatus, JobType
from docleaner.api.core.metadata import DocumentMetadata
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository

logger = logging.getLogger(__name__)


async def create_job(
    source: bytes,
    source_name: str,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[JobType],
    params: Optional[JobParams] = None,
    sid: Optional[str] = None,
) -> Tuple[str, JobType]:
    """Creates and schedules a job to transform the given source document.
    Can optionally be added to a session by providing a session id (sid).
    Returns the job id and (identified) type."""
    # Identify source MIME type
    source_mimetype = file_identifier.identify(source)
    try:
        source_type = next(
            filter(lambda jt: source_mimetype in jt.mimetypes, job_types)
        )
    except StopIteration:
        raise ValueError("Unsupported document type")
    # Create and schedule job
    logger.debug(
        "Creating job for %s of type %s (%s)", source_name, source_type.id, sid
    )
    jid = await repo.add_job(source, source_name, source_type, params, sid)
    job = await repo.find_job(jid)
    if job is None:
        raise RuntimeError(f"Race condition: added job {jid} is now gone")
    await queue.enqueue(job)
    return jid, source_type


async def await_job(jid: str, repo: Repository) -> Tuple[
    JobStatus,
    JobType,
    List[str],
    Optional[DocumentMetadata],
    Optional[DocumentMetadata],
]:
    """Blocks until the job identified by jid has been processed.
    Returns the job's final status, type, log data, source metadata and resulting metadata.
    """
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"A job with jid {jid} does not exist")
    while True:
        if job is None or job.status in [JobStatus.SUCCESS, JobStatus.ERROR]:
            break
        job = await repo.find_job(jid)
        await asyncio.sleep(0.1)
    if job is not None:
        return job.status, job.type, job.log, job.metadata_src, job.metadata_result
    raise RuntimeError(f"Race condition: awaited job {jid} is now gone")


async def get_job(jid: str, repo: Repository) -> Tuple[
    JobStatus,
    JobType,
    List[str],
    Optional[DocumentMetadata],
    Optional[DocumentMetadata],
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


async def get_jobs(
    status: JobStatus, repo: Repository
) -> List[Tuple[str, JobType, List[str]]]:
    """Returns all jobs with a specific status as tuples (jid, type, log)."""
    jobs = await repo.find_jobs(status=[status])
    return [(j.id, j.type, j.log) for j in jobs]


async def get_job_src(jid: str, repo: Repository) -> Tuple[bytes, str]:
    """Retrieves the source document and its name for a job identified by jid."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"A job with jid {jid} does not exist")
    return job.src, job.name


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


async def delete_job(jid: str, repo: Repository) -> None:
    """Deletes a single job if it is in a finished state (SUCCESS or ERROR)."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"A job with jid {jid} does not exist")
    if job.status in [JobStatus.CREATED, JobStatus.QUEUED, JobStatus.RUNNING]:
        raise ValueError(f"Job {jid} is not in a finished state (SUCCESS or ERROR)")
    logger.debug("Deleting job %s with status %s", jid, job.status)
    await repo.delete_job(jid)


async def purge_jobs(purge_after: timedelta, repo: Repository) -> Set[str]:
    """Deletes all finished standalone (not associated with a session) jobs that haven't been
    updated within the timeframe specified by purge_after. Returns the identifiers of all deleted jobs.
    """
    purged_jobs = set()
    for job in await repo.find_jobs(
        status=[JobStatus.SUCCESS, JobStatus.ERROR], not_updated_for=purge_after
    ):
        if job.session_id is None:
            purged_jobs.add(job.id)
            await repo.delete_job(job.id)
    if len(purged_jobs) > 0:
        logger.debug("Purged %d jobs", len(purged_jobs))
    return purged_jobs
