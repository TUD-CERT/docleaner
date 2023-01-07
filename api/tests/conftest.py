import pytest

from docleaner.api.adapters.clock.dummy_clock import DummyClock
from docleaner.api.adapters.file_identifier.magic_file_identifier import (
    MagicFileIdentifier,
)
from docleaner.api.adapters.job_queue.async_job_queue import AsyncJobQueue
from docleaner.api.adapters.repository.memory_repository import MemoryRepository
from docleaner.api.adapters.sandbox.dummy_sandbox import DummySandbox
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
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
def repo(clock: Clock) -> Repository:
    return MemoryRepository(clock)


@pytest.fixture
def sandbox() -> Sandbox:
    return DummySandbox()


@pytest.fixture
def queue(repo: Repository, sandbox: DummySandbox) -> JobQueue:
    return AsyncJobQueue(repo=repo, sandbox=sandbox)


@pytest.fixture
def file_identifier() -> FileIdentifier:
    return MagicFileIdentifier()
