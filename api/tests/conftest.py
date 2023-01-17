from typing import AsyncGenerator, List

import pytest

from docleaner.api.adapters.clock.dummy_clock import DummyClock
from docleaner.api.adapters.file_identifier.magic_file_identifier import (
    MagicFileIdentifier,
)
from docleaner.api.adapters.job_queue.async_job_queue import AsyncJobQueue
from docleaner.api.adapters.repository.memory_repository import MemoryRepository
from docleaner.api.adapters.sandbox.dummy_sandbox import DummySandbox
from docleaner.api.core.job import JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.metadata import process_pdf_metadata
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import Sandbox


@pytest.fixture
def clock() -> Clock:
    return DummyClock()


@pytest.fixture
def sample_pdf() -> bytes:
    with open("tests/resources/sample.pdf", "rb") as f:
        result = f.read()
    return result


@pytest.fixture
async def repo(clock: Clock) -> AsyncGenerator[Repository, None]:
    repo = MemoryRepository(clock)
    yield repo
    await repo.disconnect()


@pytest.fixture
def sandbox() -> Sandbox:
    return DummySandbox()


@pytest.fixture
def file_identifier() -> FileIdentifier:
    return MagicFileIdentifier()


@pytest.fixture
def job_types(sandbox: Sandbox) -> List[SupportedJobType]:
    return [
        SupportedJobType(
            type=JobType.PDF,
            mimetypes=["application/pdf"],
            sandbox=sandbox,
            metadata_processor=process_pdf_metadata,
        )
    ]


@pytest.fixture
async def queue(
    repo: Repository, job_types: List[SupportedJobType]
) -> AsyncGenerator[JobQueue, None]:
    q = AsyncJobQueue(repo=repo, job_types=job_types, max_concurrent_jobs=3)
    yield q
    await q.shutdown()
