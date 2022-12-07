import pytest

from docleaner.api.adapters.job_queue.dummy_job_queue import DummyJobQueue
from docleaner.api.adapters.repository.memory_repository import MemoryRepository
from docleaner.api.adapters.sandbox.dummy_sandbox import DummySandbox
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


@pytest.fixture
def repo() -> Repository:
    return MemoryRepository()


@pytest.fixture
def sample_pdf() -> bytes:
    with open("tests/resources/sample.pdf", "rb") as f:
        result = f.read()
    return result


@pytest.fixture
def queue(repo: Repository) -> JobQueue:
    return DummyJobQueue(repo=repo, sandbox=DummySandbox())
