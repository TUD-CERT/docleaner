from typing import Any, Dict, List, Union

import pytest

from docleaner.api.adapters.sandbox.dummy_sandbox import DummySandbox
from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.core.metadata import DocumentMetadata
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.metadata import process_pdf_metadata
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import process_job_in_sandbox
from docleaner.api.utils import generate_token


async def test_process_successful_job_in_sandbox(
    repo: Repository, sample_pdf: bytes
) -> None:
    """Successfully processing a job in a dummy sandbox
    and storing the result in the repository."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    await repo.update_job(jid, status=JobStatus.QUEUED)
    sandbox = DummySandbox()
    job_types = [
        SupportedJobType(
            type=JobType.PDF,
            mimetypes=["application/pdf"],
            sandbox=sandbox,
            metadata_processor=process_pdf_metadata,
        )
    ]
    await process_job_in_sandbox(jid, job_types, repo)
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.SUCCESS
    assert len(found_job.result) > 0  # Result is present
    assert len(found_job.log) > 0  # Something was logged
    # Presence and attached document metadata
    assert isinstance(found_job.metadata_result, DocumentMetadata)
    assert isinstance(found_job.metadata_src, DocumentMetadata)
    assert len(found_job.metadata_result.primary) > 0
    assert len(found_job.metadata_src.primary) > 0


async def test_process_unsuccessful_job_in_sandbox(
    repo: Repository, sample_pdf: bytes
) -> None:
    """Processing a job that fails during execution in a dummy
    sandbox and storing the result in the repository."""
    jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    await repo.update_job(jid, status=JobStatus.QUEUED)
    sandbox = DummySandbox(simulate_errors=True)
    job_types = [
        SupportedJobType(
            type=JobType.PDF,
            mimetypes=["application/pdf"],
            sandbox=sandbox,
            metadata_processor=process_pdf_metadata,
        )
    ]
    await process_job_in_sandbox(jid, job_types, repo)
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.ERROR
    assert len(found_job.result) == 0
    assert len(found_job.log) > 0  # Something was logged


async def test_process_invalid_job_in_sandbox(
    repo: Repository, sample_pdf: bytes
) -> None:
    """Attempting to process an invalid job id in the sandbox raises an exception."""
    # Invalid jid
    sandbox = DummySandbox()
    job_types = [
        SupportedJobType(
            type=JobType.PDF,
            mimetypes=["application/pdf"],
            sandbox=sandbox,
            metadata_processor=process_pdf_metadata,
        )
    ]
    with pytest.raises(ValueError):
        await process_job_in_sandbox(generate_token(), job_types, repo)
    # Invalid job status
    jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    await repo.update_job(jid, status=JobStatus.ERROR)
    with pytest.raises(ValueError):
        await process_job_in_sandbox(jid, job_types, repo)


async def test_exception_during_metadata_processing(
    repo: Repository, sample_pdf: bytes, job_types: List[SupportedJobType]
) -> None:
    """An exception thrown during metadata post-processing isn't re-raised,
    but instead the job finishes with an ERROR status."""

    def failing_postprocessor(
        src: Dict[str, Union[bool, Dict[str, Any]]]
    ) -> DocumentMetadata:
        raise ValueError()

    job_types[0].metadata_processor = failing_postprocessor
    jid = await repo.add_job(sample_pdf, "sample.pdf", JobType.PDF)
    await repo.update_job(jid, status=JobStatus.QUEUED)
    await process_job_in_sandbox(jid, job_types, repo)
    found_job = await repo.find_job(jid)
    assert isinstance(found_job, Job)
    assert found_job.status == JobStatus.ERROR
    assert found_job.log[-1] == "Error during metadata post-processing"
