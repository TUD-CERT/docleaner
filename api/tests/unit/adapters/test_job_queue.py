import pytest

from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


async def test_enqueue_job(
    queue: JobQueue, repo: Repository, sample_pdf: bytes
) -> None:
    """Adding a job to the processing queue and waiting until job completion."""
    jid = await repo.add_job(sample_pdf, JobType.PDF)
    job = await repo.find_job(jid)
    assert isinstance(job, Job)
    await queue.enqueue(job)
    await queue.wait_for(jid)


async def test_enqueue_job_with_invalid_state(
    queue: JobQueue, repo: Repository, sample_pdf: bytes
) -> None:
    """Attempting to enqueue a job in invalid state."""
    jid = await repo.add_job(sample_pdf, JobType.PDF)
    await repo.update_job(jid, status=JobStatus.SUCCESS)
    job = await repo.find_job(jid)
    assert isinstance(job, Job)
    with pytest.raises(ValueError):
        await queue.enqueue(job)
