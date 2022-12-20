from datetime import timedelta

import magic
import pytest

from docleaner.api.adapters.clock.dummy_clock import DummyClock
from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.jobs import (
    await_job,
    create_job,
    get_job_result,
    purge_jobs,
)
from docleaner.api.services.repository import Repository


async def test_process_pdf_job(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    clock: Clock,
) -> None:
    """Creating a PDF cleaning job, waiting until processing is complete and retrieving the result."""
    jid, job_type = await create_job(sample_pdf, repo, queue, file_identifier, clock)
    assert isinstance(jid, str) and len(jid) > 0
    assert job_type == JobType.PDF
    # Wait until job completion
    result_status, result_type, log, metadata_src, metadata_result = await await_job(
        jid, repo, queue
    )
    assert result_status == JobStatus.SUCCESS
    assert result_type == JobType.PDF
    assert isinstance(log, list)
    assert isinstance(metadata_src, dict) and len(metadata_src) > 0
    assert isinstance(metadata_result, dict)
    # Retrieve resulting PDF
    result = await get_job_result(jid, repo)
    assert magic.from_buffer(result, mime=True) == "application/pdf"
    assert result != sample_pdf


async def test_process_invalid_job(
    repo: Repository, queue: JobQueue, file_identifier: FileIdentifier, clock: Clock
) -> None:
    """Attempting to create a job from an unsupported document type raises an exception."""
    with pytest.raises(ValueError, match=r".*Unsupported document.*"):
        await create_job(b"INVALID_DOCUMENT", repo, queue, file_identifier, clock)


async def test_await_nonexisting_job(repo: Repository, queue: JobQueue) -> None:
    """Attempting to await an invalid job raises an exception."""
    with pytest.raises(ValueError, match=r".*does not exist.*"):
        await await_job("invalid", repo, queue)


async def test_await_again(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    clock: Clock,
) -> None:
    """Attempting to await a job that has been successfully awaited before
    succeeds and returns identical results."""
    jid, _ = await create_job(sample_pdf, repo, queue, file_identifier, clock)
    r1_status, r1_type, r1_log, r1_meta_src, r1_meta_result = await await_job(
        jid, repo, queue
    )
    r2_status, r2_type, r2_log, r2_meta_src, r2_meta_result = await await_job(
        jid, repo, queue
    )
    for x, y in [
        (r1_status, r2_status),
        (r1_type, r2_type),
        (r1_log, r2_log),
        (r1_meta_src, r2_meta_src),
        (r1_meta_result, r2_meta_result),
    ]:
        assert x == y


async def test_get_unfinished_job_result(
    sample_pdf: bytes, repo: Repository, clock: Clock
) -> None:
    """Attempting to retrieve the result of a yet unfinished job raises an exception."""
    job = Job(
        src=sample_pdf, type=JobType.PDF, status=JobStatus.QUEUED, created=clock.now()
    )
    jid = await repo.add_job(job)
    with pytest.raises(ValueError, match=r".*didn't complete.*"):
        await get_job_result(jid, repo)


async def test_get_nonexisting_job_result(repo: Repository) -> None:
    """Attempting to retrieve the result of an invalid job raises an exception."""
    with pytest.raises(ValueError, match=r".*does not exist.*"):
        await get_job_result("invalid", repo)


async def test_purge_jobs(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
) -> None:
    """Purge jobs after some time of inactivity as long as they are not in a RUNNING state."""
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    jid1, _ = await create_job(sample_pdf, repo, queue, file_identifier, clock)
    jid2, _ = await create_job(sample_pdf, repo, queue, file_identifier, clock)
    running_job = Job(
        src=sample_pdf, type=JobType.PDF, status=JobStatus.RUNNING, created=clock.now()
    )
    running_jid = await repo.add_job(running_job)
    clock.advance(60)
    newer_jid, _ = await create_job(sample_pdf, repo, queue, file_identifier, clock)
    purged_ids = await purge_jobs(timedelta(seconds=30), repo, clock)
    assert purged_ids == {jid1, jid2}
    jids = {job.id for job in await repo.find_jobs()}
    assert jids == {newer_jid, running_jid}
