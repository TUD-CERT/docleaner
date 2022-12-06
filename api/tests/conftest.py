import pytest

from docleaner.api.adapters.repository.memory_repository import MemoryRepository
from docleaner.api.services.repository import Repository


@pytest.fixture
def repo() -> Repository:
    return MemoryRepository()


@pytest.fixture
def sample_pdf() -> bytes:
    with open("tests/resources/sample.pdf", "rb") as f:
        result = f.read()
    return result
