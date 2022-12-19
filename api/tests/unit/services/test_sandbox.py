import pytest

from docleaner.api.adapters.sandbox.dummy_sandbox import DummySandbox
from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import process_job_in_sandbox
from docleaner.api.utils import generate_token


async def test_process_successful_job_in_sandbox(
    repo: Repository, sample_pdf: bytes
) -> None:
    """Successfully processing a job in a dummy sandbox
    and storing the result in the repository."""
    job = Job(src=sample_pdf, type=JobType.PDF, status=JobStatus.QUEUED)
    jid = await repo.add_job(job)
    sandbox = DummySandbox()
    await process_job_in_sandbox(jid, sandbox, repo)
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.SUCCESS
    assert len(found_job.result) > 0  # Result is present
    assert len(found_job.log) > 0  # Something was logged
    # Presence of attached document metadata
    assert len(found_job.metadata_src) > 0


async def test_process_unsuccessful_job_in_sandbox(
    repo: Repository, sample_pdf: bytes
) -> None:
    """Processing a job that fails during execution in a dummy
    sandbox and storing the result in the repository."""
    job = Job(src=sample_pdf, type=JobType.PDF, status=JobStatus.QUEUED)
    jid = await repo.add_job(job)
    sandbox = DummySandbox(simulate_errors=True)
    await process_job_in_sandbox(jid, sandbox, repo)
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.ERROR
    assert len(found_job.result) == 0
    assert len(found_job.log) > 0  # Something was logged


async def test_process_invalid_job_in_sandbox(
    repo: Repository, sample_pdf: bytes
) -> None:
    """Attempting to process an invalid job in the sandbox raises an exception."""
    # Invalid jid
    sandbox = DummySandbox()
    with pytest.raises(ValueError):
        await process_job_in_sandbox(generate_token(), sandbox, repo)
    # Invalid job status
    job = Job(src=sample_pdf, type=JobType.PDF, status=JobStatus.ERROR)
    jid = await repo.add_job(job)
    with pytest.raises(ValueError):
        await process_job_in_sandbox(jid, sandbox, repo)
