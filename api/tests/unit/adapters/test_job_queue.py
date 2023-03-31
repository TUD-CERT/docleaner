import pytest
from typing import List

from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.jobs import await_job
from docleaner.api.services.repository import Repository


async def test_enqueue_job(
    queue: JobQueue, repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Adding a job to the processing queue and waiting until job completion."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    job = await repo.find_job(jid)
    assert isinstance(job, Job)
    await queue.enqueue(job)
    await await_job(jid, repo)


async def test_enqueue_job_with_invalid_state(
    queue: JobQueue, repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Attempting to enqueue a job in invalid state."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    await repo.update_job(jid, status=JobStatus.SUCCESS)
    job = await repo.find_job(jid)
    assert isinstance(job, Job)
    with pytest.raises(ValueError):
        await queue.enqueue(job)
