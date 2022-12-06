import pytest

from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token


async def test_add_and_fetch_job(repo: Repository, sample_pdf: bytes) -> None:
    """Adding and retrieving a job."""
    job = Job(src=sample_pdf, type=JobType.PDF)
    jid = await repo.add_job(job)
    assert isinstance(jid, str) and len(jid) > 0
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.id == jid
    assert found_job.src == sample_pdf
    assert found_job.type == JobType.PDF
    assert found_job.status == JobStatus.CREATED


async def test_cant_add_with_specific_jid(repo: Repository, sample_pdf: bytes) -> None:
    """Attempting to add a job with a jid other than None raises an exception."""
    job = Job(id=generate_token(), src=sample_pdf, type=JobType.PDF)
    with pytest.raises(ValueError):
        await repo.add_job(job)


async def test_fetch_all_jobs(repo: Repository, sample_pdf: bytes) -> None:
    """Adding a multiple jobs and fetching all of them at once."""
    jids = set()
    for j in [
        Job(src=sample_pdf, type=JobType.PDF),
        Job(src=sample_pdf, type=JobType.PDF),
    ]:
        jids.add(await repo.add_job(j))
    jobs = await repo.find_jobs()
    assert len(jobs) == 2
    assert set(map(lambda job: job.id, jobs)) == jids


async def test_update_job(repo: Repository, sample_pdf: bytes) -> None:
    """Updating a job's result and status."""
    job = Job(src=sample_pdf, type=JobType.PDF)
    jid = await repo.add_job(job)
    await repo.update_job(jid, status=JobStatus.RUNNING)
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.RUNNING
    await repo.update_job(jid, result=b"TEST", status=JobStatus.SUCCESS)
    assert found_job.status == JobStatus.SUCCESS
    assert found_job.result == b"TEST"


async def test_update_job_log(repo: Repository, sample_pdf: bytes) -> None:
    """Adding an entry to a job's log data."""
    job = Job(src=sample_pdf, type=JobType.PDF)
    jid = await repo.add_job(job)
    await repo.add_to_job_log(jid, "This is")
    await repo.add_to_job_log(jid, "logging data")
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.log == ["This is", "logging data"]


async def test_delete_job(repo: Repository, sample_pdf: bytes) -> None:
    """Deleting a job by its job id."""
    job = Job(src=sample_pdf, type=JobType.PDF)
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
