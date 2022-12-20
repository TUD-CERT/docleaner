import pytest

from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


async def test_enqueue_job(
    queue: JobQueue, repo: Repository, sample_pdf: bytes
) -> None:
    """Adding a job to the processing queue and waiting until job completion."""
    job = Job(src=sample_pdf, type=JobType.PDF)
    jid = await repo.add_job(job)
    await queue.enqueue(job)
    await queue.wait_for(jid)


async def test_enqueue_job_without_id(
    queue: JobQueue, repo: Repository, sample_pdf: bytes
) -> None:
    """Attempting to enqueue a job without an ID raises an exception."""
    job = Job(src=sample_pdf, type=JobType.PDF)
    with pytest.raises(ValueError):
        await queue.enqueue(job)


async def test_enqueue_job_with_invalid_state(
    queue: JobQueue, repo: Repository, sample_pdf: bytes
) -> None:
    """Attempting to enqueue a job in invalid state."""
    job = Job(src=sample_pdf, type=JobType.PDF, status=JobStatus.SUCCESS)
    await repo.add_job(job)
    with pytest.raises(ValueError):
        await queue.enqueue(job)
