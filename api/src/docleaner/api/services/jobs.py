from typing import Dict, List, Tuple

from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


async def create_job(
    source: bytes, repo: Repository, queue: JobQueue, file_identifier: FileIdentifier
) -> Tuple[str, JobType]:
    """Creates and schedules a job to clean the given source document.
    Returns the job id and (identified) type."""
    # Identify source MIME type
    match file_identifier.identify(source):
        case "application/pdf":
            source_type = JobType.PDF
        case _:
            raise ValueError("Unsupported document")
    # Create and schedule job
    jid = await repo.add_job(Job(src=source, type=source_type))
    job = await repo.find_job(jid)
    if job is None:
        raise RuntimeError(f"Race condition: added job {jid} is now gone")
    await queue.enqueue(job)
    return jid, source_type


async def await_job(
    jid: str, repo: Repository, queue: JobQueue
) -> Tuple[JobStatus, JobType, List[str], Dict[str, str], Dict[str, str]]:
    """Blocks until the job identified by jid has been processed.
    Returns the job's final status, type, log data, source metadata and resulting metadata."""
    await queue.wait_for(jid)
    job = await repo.find_job(jid)
    if job is not None:
        return job.status, job.type, job.log, job.metadata_src, job.metadata_result
    raise RuntimeError(f"Race condition: awaited job {jid} is now gone")


async def get_job_result(jid: str, repo: Repository) -> bytes:
    """Retrieves the result for a successfully completed job identified by jid."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"A job with jid {jid} does not exist")
    if job.status != JobStatus.SUCCESS:
        raise ValueError(
            f"Job with jid {jid} didn't complete (yet), current state is {job.status}"
        )
    return job.result
