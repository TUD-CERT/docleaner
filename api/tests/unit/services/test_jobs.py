from datetime import timedelta
from typing import List

import magic
import pytest

from docleaner.api.adapters.clock.dummy_clock import DummyClock
from docleaner.api.core.job import JobStatus, JobType
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.jobs import (
    await_job,
    create_job,
    get_job,
    get_job_result,
    purge_jobs,
)
from docleaner.api.services.repository import Repository
from docleaner.api.services.sessions import create_session


async def test_process_pdf_job(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[SupportedJobType],
) -> None:
    """Creating a PDF cleaning job, waiting until processing is complete and retrieving the result."""
    jid, job_type = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types
    )
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
    result, document_name = await get_job_result(jid, repo)
    assert document_name == "sample.pdf"
    assert magic.from_buffer(result, mime=True) == "application/pdf"
    assert result != sample_pdf


async def test_process_invalid_job(
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[SupportedJobType],
) -> None:
    """Attempting to create a job from an unsupported document type raises an exception."""
    with pytest.raises(ValueError, match=r".*Unsupported document.*"):
        await create_job(
            b"INVALID_DOCUMENT", "sample.pdf", repo, queue, file_identifier, job_types
        )


async def test_services_with_nonexisting_job(repo: Repository, queue: JobQueue) -> None:
    """Attempting to call various services with a nonexistent job raises exceptions."""
    with pytest.raises(ValueError, match=r".*does not exist.*"):
        await await_job("invalid", repo, queue)
    with pytest.raises(ValueError, match=r".*does not exist.*"):
        await get_job("invalid", repo)
    with pytest.raises(ValueError, match=r".*does not exist.*"):
        await get_job_result("invalid", repo)


async def test_await_again(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[SupportedJobType],
) -> None:
    """Attempting to await a job that has been successfully awaited before
    succeeds and returns identical results."""
    jid, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types
    )
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


async def test_get_unfinished_job_details(sample_pdf: bytes, repo: Repository) -> None:
    """Retrieving details for a job that hasn't been finished yet."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    job_status, job_type, job_log, job_meta_src, job_meta_result = await get_job(
        jid, repo
    )
    assert job_status == JobStatus.CREATED
    assert job_type == JobType.PDF


async def test_get_finished_job_details(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[SupportedJobType],
) -> None:
    """Retrieving details for a job that has been finished."""
    jid, job_type = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types
    )
    await await_job(jid, repo, queue)
    job_status, job_type, job_log, job_meta_src, job_meta_result = await get_job(
        jid, repo
    )
    assert job_status == JobStatus.SUCCESS
    assert job_type == JobType.PDF
    assert len(job_meta_src) > 0


async def test_get_unfinished_job_result(sample_pdf: bytes, repo: Repository) -> None:
    """Attempting to retrieve the result of a yet unfinished job raises an exception."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    with pytest.raises(ValueError, match=r".*didn't complete.*"):
        await get_job_result(jid, repo)


async def test_purge_jobs(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[SupportedJobType],
) -> None:
    """Purge individual finished (in SUCCESS or ERROR state) standalone jobs
    after some time of inactivity. Jobs associated with a session are ignored."""
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    finished_jid, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types
    )
    await await_job(finished_jid, repo, queue)
    running_jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    await repo.update_job(running_jid, status=JobStatus.RUNNING)
    created_jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    queued_jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    await repo.update_job(queued_jid, status=JobStatus.QUEUED)
    sid = await create_session(repo)
    session_jid, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
    )
    await await_job(session_jid, repo, queue)
    clock.advance(60)
    newer_jid, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types
    )
    await await_job(newer_jid, repo, queue)
    purged_ids = await purge_jobs(timedelta(seconds=30), repo)
    assert purged_ids == {finished_jid}
    jids = {job.id for job in await repo.find_jobs()}
    assert jids == {newer_jid, running_jid, created_jid, queued_jid, session_jid}
