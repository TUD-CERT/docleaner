from datetime import datetime, timedelta
from typing import List

import pytest

from docleaner.api.adapters.clock.dummy_clock import DummyClock
from docleaner.api.core.job import JobStatus, JobType
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.jobs import await_job, create_job, get_job, get_job_result
from docleaner.api.services.repository import Repository
from docleaner.api.services.sessions import (
    await_session,
    create_session,
    get_session,
    delete_session,
    purge_sessions,
)
from docleaner.api.utils import generate_token


async def test_process_multiple_jobs_via_session(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[JobType],
) -> None:
    """Creating a session, then associating multiple jobs with
    it and waiting until processing of all jobs is complete."""
    sid = await create_session(repo)
    assert isinstance(sid, str) and len(sid) > 0
    jid1, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
    )
    jid2, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
    )
    # Wait until job completion
    await await_session(sid, repo, queue)
    # Retrieve session and job details
    created, updated, total_jobs, finished_jobs, jobs = await get_session(sid, repo)
    assert isinstance(created, datetime)
    assert isinstance(updated, datetime)
    assert total_jobs == finished_jobs == 2
    assert len(jobs) == 2
    assert {j[0] for j in jobs} == {jid1, jid2}
    assert all({isinstance(j[1], datetime) for j in jobs})
    assert all({isinstance(j[2], datetime) for j in jobs})
    assert {j[3] for j in jobs} == {JobStatus.SUCCESS}
    assert {j[4] for j in jobs} == {job_types[0]}
    # Retrieve one of the results
    result, document_name = await get_job_result(jid2, repo)
    assert document_name == "sample.pdf"
    assert isinstance(result, bytes)
    assert len(result) > 0


async def test_get_unfinished_session_details(
    sample_pdf: bytes, repo: Repository, job_types: List[JobType]
) -> None:
    """Retrieving session details for a session with yet unfinished jobs."""
    sid = await create_session(repo)
    jid1 = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid)
    await repo.update_job(jid1, status=JobStatus.QUEUED)
    jid2 = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid)
    await repo.update_job(jid2, status=JobStatus.SUCCESS)
    jid3 = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid)
    await repo.update_job(jid3, status=JobStatus.ERROR)
    created, updated, total_jobs, finished_jobs, jobs = await get_session(sid, repo)
    assert total_jobs == 3
    assert finished_jobs == 2
    assert len(jobs) == 3


async def test_with_nonexistent_session(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[JobType],
) -> None:
    """Attempting to call various services with a nonexistent session raises exceptions."""
    sid = generate_token()
    with pytest.raises(ValueError):
        await create_job(
            sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
        )
    with pytest.raises(ValueError):
        await await_session(sid, repo, queue)
    with pytest.raises(ValueError, match="Invalid session id"):
        await get_session(sid, repo)
    with pytest.raises(ValueError, match="Invalid session id"):
        await delete_session(sid, repo)


async def test_delete_finished_session(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[JobType],
) -> None:
    """Deleting a session that has only associated jobs in state SUCCESS and ERROR."""
    sid = await create_session(repo)
    jid1, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
    )
    jid2, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
    )
    jid3 = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid)
    await repo.update_job(jid3, status=JobStatus.ERROR)
    # Wait until job completion
    await await_session(sid, repo, queue)
    # Delete session
    await delete_session(sid, repo)
    # Verify session and job deletion
    with pytest.raises(ValueError, match="Invalid session id"):
        await get_session(sid, repo)
    for jid in [jid1, jid2, jid3]:
        with pytest.raises(ValueError, match="does not exist"):
            await get_job(jid, repo)


async def test_delete_running_session(
    sample_pdf: bytes,
    repo: Repository,
    job_types: List[JobType],
) -> None:
    """Attempting to delete a session that has running or queued jobs
    raises an exception until all jobs are finished."""
    sid = await create_session(repo)
    jid1 = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid)
    await repo.update_job(jid1, status=JobStatus.CREATED)
    jid2 = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid)
    await repo.update_job(jid2, status=JobStatus.QUEUED)
    jid3 = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid)
    await repo.update_job(jid3, status=JobStatus.RUNNING)
    with pytest.raises(ValueError, match="has unfinished jobs"):
        await delete_session(sid, repo)
    await repo.update_job(jid1, status=JobStatus.SUCCESS)
    with pytest.raises(ValueError, match="has unfinished jobs"):
        await delete_session(sid, repo)
    await repo.update_job(jid2, status=JobStatus.SUCCESS)
    with pytest.raises(ValueError, match="has unfinished jobs"):
        await delete_session(sid, repo)
    await repo.update_job(jid3, status=JobStatus.ERROR)
    await delete_session(sid, repo)


async def test_purge_sessions(
    sample_pdf: bytes,
    repo: Repository,
    queue: JobQueue,
    file_identifier: FileIdentifier,
    job_types: List[JobType],
) -> None:
    """Purge finished (all associated jobs in SUCCESS or ERROR state) sessions
    after some time of inactivity. Standalone jobs - not associated with a session - are ignored."""
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    sid = await create_session(repo)
    standalone_jid, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types
    )
    await await_job(standalone_jid, repo)
    finished_jid, _ = await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
    )
    await await_job(finished_jid, repo)
    # Job that remains in QUEUED state
    await create_job(
        sample_pdf, "sample.pdf", repo, queue, file_identifier, job_types, sid
    )
    clock.advance(60)
    purged_sids = await purge_sessions(timedelta(seconds=30), repo)
    assert len(purged_sids) == 0  # Session is not stale, there is still a queued job
    await await_session(sid, repo, queue)
    clock.advance(60)
    purged_sids = await purge_sessions(timedelta(seconds=30), repo)
    assert purged_sids == {sid}
    jids = {job.id for job in await repo.find_jobs()}
    assert jids == {standalone_jid}
