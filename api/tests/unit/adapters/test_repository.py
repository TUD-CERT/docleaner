from datetime import datetime

import pytest

from docleaner.api.adapters.clock.dummy_clock import DummyClock
from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token


async def test_add_and_fetch_job(
    repo: Repository, sample_pdf: bytes, clock: Clock
) -> None:
    """Adding and retrieving a job."""
    job = Job(src=sample_pdf, type=JobType.PDF, created=clock.now())
    jid = await repo.add_job(job)
    assert isinstance(jid, str) and len(jid) > 0
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.id == jid
    assert found_job.src == sample_pdf
    assert found_job.type == JobType.PDF
    assert found_job.status == JobStatus.CREATED
    assert found_job.metadata_result == found_job.metadata_src == {}
    assert isinstance(found_job.created, datetime)
    assert found_job.created == found_job.updated


async def test_cant_add_with_specific_jid(
    repo: Repository, sample_pdf: bytes, clock: Clock
) -> None:
    """Attempting to add a job with a jid other than None raises an exception."""
    job = Job(
        id=generate_token(), src=sample_pdf, type=JobType.PDF, created=clock.now()
    )
    with pytest.raises(ValueError):
        await repo.add_job(job)


async def test_fetch_all_jobs(
    repo: Repository, sample_pdf: bytes, clock: Clock
) -> None:
    """Adding multiple jobs and fetching all of them at once."""
    jids = set()
    for j in [
        Job(src=sample_pdf, type=JobType.PDF, created=clock.now()),
        Job(src=sample_pdf, type=JobType.PDF, created=clock.now()),
    ]:
        jids.add(await repo.add_job(j))
    jobs = await repo.find_jobs()
    assert len(jobs) == 2
    assert set(map(lambda job: job.id, jobs)) == jids


async def test_update_job(repo: Repository, sample_pdf: bytes, clock: Clock) -> None:
    """Updating a job's result, status and metadata."""
    job = Job(src=sample_pdf, type=JobType.PDF, created=clock.now())
    jid = await repo.add_job(job)
    await repo.update_job(
        jid,
        status=JobStatus.RUNNING,
        metadata_src={"author": "Alice", "year": "2000"},
        metadata_result={"year": "2000"},
    )
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.RUNNING
    await repo.update_job(jid, result=b"TEST", status=JobStatus.SUCCESS)
    assert found_job.status == JobStatus.SUCCESS
    assert found_job.result == b"TEST"
    assert found_job.metadata_result == {"year": "2000"}
    assert found_job.metadata_src == {"author": "Alice", "year": "2000"}


async def test_update_job_log(
    repo: Repository, sample_pdf: bytes, clock: Clock
) -> None:
    """Adding an entry to a job's log data."""
    job = Job(src=sample_pdf, type=JobType.PDF, created=clock.now())
    jid = await repo.add_job(job)
    await repo.add_to_job_log(jid, "This is")
    await repo.add_to_job_log(jid, "logging data")
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.log == ["This is", "logging data"]


async def test_delete_job(repo: Repository, sample_pdf: bytes, clock: Clock) -> None:
    """Deleting a job by its job id."""
    job = Job(src=sample_pdf, type=JobType.PDF, created=clock.now())
    jid = await repo.add_job(job)
    await repo.delete_job(jid)
    assert await repo.find_job(jid) is None
    assert await repo.find_jobs() == set()


async def test_with_nonexisting_job(repo: Repository) -> None:
    """Attempting to CRUD a nonexisting job."""
    jid = generate_token()
    assert await repo.find_job(jid) is None
    with pytest.raises(ValueError):
        await repo.update_job(jid)
    with pytest.raises(ValueError):
        await repo.add_to_job_log(jid, "test")
    with pytest.raises(ValueError):
        await repo.delete_job(jid)


async def test_job_timestamp_is_updated_after_updates(
    sample_pdf: bytes, repo: Repository, clock: Clock
) -> None:
    """Updating a job also updates its 'updated' timestamp."""
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    job = Job(src=sample_pdf, type=JobType.PDF, created=clock.now())
    jid = await repo.add_job(job)
    advanced_time = clock.advance(10)
    await repo.update_job(jid, status=JobStatus.QUEUED)
    result = await repo.find_job(jid)
    assert isinstance(result, Job)
    assert result.updated == advanced_time
