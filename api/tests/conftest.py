import pytest

from docleaner.api.adapters.file_identifier.magic_file_identifier import (
    MagicFileIdentifier,
)
from docleaner.api.adapters.job_queue.dummy_job_queue import DummyJobQueue
from docleaner.api.adapters.repository.memory_repository import MemoryRepository
from docleaner.api.adapters.sandbox.dummy_sandbox import DummySandbox
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import Sandbox


@pytest.fixture
def sample_pdf() -> bytes:
    with open("tests/resources/sample.pdf", "rb") as f:
        result = f.read()
    return result


@pytest.fixture
def repo() -> Repository:
    return MemoryRepository()


@pytest.fixture
def sandbox() -> Sandbox:
    return DummySandbox()


@pytest.fixture
def queue(repo: Repository, sandbox: DummySandbox) -> JobQueue:
    return DummyJobQueue(repo=repo, sandbox=sandbox)


@pytest.fixture
def file_identifier() -> FileIdentifier:
    return MagicFileIdentifier()
