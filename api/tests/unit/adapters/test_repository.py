from datetime import datetime, timedelta
from typing import List

import pytest

from docleaner.api.adapters.clock.dummy_clock import DummyClock
from docleaner.api.core.job import Job, JobParams, JobStatus, JobType
from docleaner.api.core.metadata import DocumentMetadata, MetadataField
from docleaner.api.core.session import Session
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token


async def test_add_and_fetch_job(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Adding and retrieving a job."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    assert isinstance(jid, str) and len(jid) > 0
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.id == jid
    assert found_job.src == sample_pdf
    assert found_job.type == job_types[0]
    assert found_job.status == JobStatus.CREATED
    assert found_job.metadata_result is found_job.metadata_src is None
    assert isinstance(found_job.created, datetime)
    assert found_job.created == found_job.updated
    assert found_job.session_id is None


async def test_add_and_fetch_job_with_params(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Adding and retrieving a job with some custom parameters."""
    params = JobParams(metadata=[MetadataField(id="Title", value="invoice")])
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], params)
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.params == JobParams(
        metadata=[MetadataField(id="Title", value="invoice")]
    )


async def test_fetch_all_jobs(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Adding multiple jobs and fetching all of them at once,
    expecting a list ordered descending by job creation date.
    For performance reasons, the returned job objects do not contain
    any metadata, no job log and no source or resulting documents."""
    jids = []
    for i in range(5):
        jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
        await repo.add_to_job_log(jid, "debug log entry")
        jids.append(jid)
    jobs = await repo.find_jobs()
    assert len(jobs) == 5
    assert list(map(lambda job: job.id, jobs)) == jids
    for job in jobs:
        assert job.metadata_result is job.metadata_src is None
        assert job.result == b""
        assert job.src == b""
        assert job.log == []


async def test_filter_jobs(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Fetching jobs using various filter criteria."""
    # session (sid) filtering is covered by session-specific tests
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    queued_jids = set()
    for i in range(2):
        jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
        await repo.update_job(jid, status=JobStatus.QUEUED)
        queued_jids.add(jid)
    running_jids = set()
    for i in range(2):
        jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
        await repo.update_job(jid, status=JobStatus.RUNNING)
        running_jids.add(jid)
    clock.advance(30)
    successful_jids = set()
    for i in range(2):
        jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
        await repo.update_job(jid, status=JobStatus.SUCCESS)
        successful_jids.add(jid)
    # Filter by status flags
    assert running_jids == {
        job.id for job in await repo.find_jobs(status=[JobStatus.RUNNING])
    }
    assert queued_jids | successful_jids == {
        job.id
        for job in await repo.find_jobs(status=[JobStatus.QUEUED, JobStatus.SUCCESS])
    }
    # Filter by not_updated_for
    assert queued_jids | running_jids == {
        job.id for job in await repo.find_jobs(not_updated_for=timedelta(seconds=10))
    }
    # Filter by multiple criteria
    assert queued_jids == {
        job.id
        for job in await repo.find_jobs(
            status=[JobStatus.QUEUED], not_updated_for=timedelta(seconds=10)
        )
    }


async def test_update_job(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Updating a job's result, status and metadata."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    metadata_src = DocumentMetadata(
        primary={
            "author": MetadataField(id="author", value="Alice"),
            "year": MetadataField(id="year", value=2000),
        },
        signed=True,
    )
    metadata_result = DocumentMetadata(
        primary={"author": MetadataField(id="author", value="Alice")}, signed=True
    )
    await repo.update_job(
        jid,
        status=JobStatus.RUNNING,
        metadata_src=metadata_src,
        metadata_result=metadata_result,
    )
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.RUNNING
    await repo.update_job(jid, result=b"TEST", status=JobStatus.SUCCESS)
    updated_job = await repo.find_job(jid)
    assert isinstance(updated_job, Job)
    assert updated_job.status == JobStatus.SUCCESS
    assert updated_job.result == b"TEST"
    assert isinstance(updated_job.metadata_result, DocumentMetadata)
    assert isinstance(updated_job.metadata_src, DocumentMetadata)
    assert len(updated_job.metadata_result.primary) == 1
    assert updated_job.metadata_result.primary["author"].value == "Alice"
    assert updated_job.metadata_result.embeds == {}
    assert len(updated_job.metadata_src.primary) == 2
    assert updated_job.metadata_src.primary["author"].value == "Alice"
    assert updated_job.metadata_src.primary["year"].value == 2000
    assert updated_job.metadata_src.embeds == {}
    assert updated_job.metadata_src.signed is updated_job.metadata_result.signed is True


async def test_update_job_log(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Adding an entry to a job's log data."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    await repo.add_to_job_log(jid, "This is")
    await repo.add_to_job_log(jid, "logging data")
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.log == ["This is", "logging data"]


async def test_delete_job(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Deleting a job via its job id."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    await repo.delete_job(jid)
    assert await repo.find_job(jid) is None
    assert await repo.find_jobs() == []


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
    sample_pdf: bytes, repo: Repository, job_types: List[JobType]
) -> None:
    """Updating a job also updates its 'updated' timestamp."""
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    advanced_time = clock.advance(10)
    await repo.update_job(jid, status=JobStatus.QUEUED)
    result = await repo.find_job(jid)
    assert isinstance(result, Job)
    # Account for repository implementations with different time resolutions
    assert advanced_time - result.updated <= timedelta(seconds=1)


async def test_get_total_job_count(
    sample_pdf: bytes, repo: Repository, job_types: List[JobType]
) -> None:
    """Retrieving the total number of jobs after some jobs have been deleted."""
    assert await repo.get_total_job_count() == 0
    for i in range(3):
        jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
        await repo.delete_job(jid)
    for i in range(5):
        await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    assert await repo.get_total_job_count() == 8


async def test_add_and_fetch_session(repo: Repository) -> None:
    """Adding and retrieving a session."""
    sid = await repo.add_session()
    assert isinstance(sid, str) and len(sid) > 0
    found_session = await repo.find_session(sid)
    assert isinstance(found_session, Session)
    assert found_session.id == sid
    assert found_session.created == found_session.updated


async def test_fetch_all_sessions(repo: Repository) -> None:
    """Adding multiple sessions and fetching all of them at once."""
    sids = set()
    for i in range(2):
        sids.add(await repo.add_session())
    sessions = await repo.find_sessions()
    assert len(sessions) == 2
    assert set(map(lambda session: session.id, sessions)) == sids


async def test_filter_sessions(repo: Repository) -> None:
    """Fetching sessions by their last updated timestamp."""
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    old_sid1 = await repo.add_session()
    old_sid2 = await repo.add_session()
    clock.advance(30)
    await repo.add_session()
    await repo.add_session()
    assert {old_sid1, old_sid2} == {
        session.id
        for session in await repo.find_sessions(not_updated_for=timedelta(seconds=10))
    }


async def test_delete_session(repo: Repository) -> None:
    """Deleting a session via its session id."""
    sid = await repo.add_session()
    await repo.delete_session(sid)
    assert await repo.find_session(sid) is None
    assert await repo.find_sessions() == set()


async def test_with_nonexisting_session(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Attempting to CRUD a nonexisting session."""
    sid = generate_token()
    assert await repo.find_session(sid) is None
    with pytest.raises(ValueError):
        await repo.delete_session(sid)
    with pytest.raises(ValueError):
        await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid=sid)
    with pytest.raises(ValueError):
        await repo.find_jobs(sid)


async def test_add_jobs_to_session_then_fetch_and_delete_them(
    repo: Repository, sample_pdf: bytes, job_types: List[JobType]
) -> None:
    """Adding a session, then adding jobs to that session and fetch then again.
    Afterwards, deleting the session and verifying that both jobs are gone as well."""
    # Create session and jobs
    sid = await repo.add_session()
    jids = set()
    for i in range(2):
        jids.add(await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid=sid))
    sessionless_jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0])
    # Fetch session's jobs
    found_jobs = await repo.find_jobs(sid)
    assert len(found_jobs) == 2
    assert set(map(lambda job: job.id, found_jobs)) == jids
    for j in found_jobs:
        assert j.session_id == sid
    # Delete session and associated jobs
    await repo.delete_session(sid)
    assert await repo.find_sessions() == set()
    remaining_jobs = await repo.find_jobs()
    assert set(map(lambda job: job.id, remaining_jobs)) == {sessionless_jid}


async def test_session_timestamp_is_updated_after_job_updates(
    sample_pdf: bytes, repo: Repository, job_types: List[JobType]
) -> None:
    """Adding, updating or deleting a job that is associated with a session also
    updates that session's 'updated' timestamp."""
    clock = DummyClock()
    repo._clock = clock  # type: ignore
    sid = await repo.add_session()
    # Session is updated when adding jobs
    advanced_time = clock.advance(10)
    jid = await repo.add_job(sample_pdf, "sample.pdf", job_types[0], sid=sid)
    session = await repo.find_session(sid)
    assert isinstance(session, Session)
    # Account for repository implementations with different time resolutions
    assert advanced_time - session.updated <= timedelta(seconds=1)
    # Session is updated when updating jobs
    advanced_time = clock.advance(10)
    await repo.update_job(jid, status=JobStatus.QUEUED)
    session = await repo.find_session(sid)
    assert isinstance(session, Session)
    assert advanced_time - session.updated <= timedelta(seconds=1)
    # Session is updated when deleting jobs
    advanced_time = clock.advance(10)
    await repo.delete_job(jid)
    session = await repo.find_session(sid)
    assert isinstance(session, Session)
    assert advanced_time - session.updated <= timedelta(seconds=1)
