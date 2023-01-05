from dataclasses import dataclass
from typing import Optional

from docleaner.api.adapters.clock.system_clock import SystemClock
from docleaner.api.adapters.file_identifier.magic_file_identifier import (
    MagicFileIdentifier,
)
from docleaner.api.adapters.job_queue.dummy_job_queue import DummyJobQueue
from docleaner.api.adapters.repository.memory_repository import MemoryRepository
from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import Sandbox


@dataclass(eq=False, kw_only=True)
class Adapters:
    """Instantiates an evil god object that holds adapter instances
    the entrypoints need for calling the service layer."""

    clock: Clock
    file_identifier: FileIdentifier
    queue: JobQueue
    repo: Repository
    sandbox: Sandbox


def bootstrap(
    clock: Optional[Clock] = None,
    file_identifier: Optional[FileIdentifier] = None,
    queue: Optional[JobQueue] = None,
    repo: Optional[Repository] = None,
    sandbox: Optional[Sandbox] = None,
) -> Adapters:
    """Initializes adapters and service components.
    Returns a composite object with all adapters attached."""
    if clock is None:
        clock = SystemClock()
    if file_identifier is None:
        file_identifier = MagicFileIdentifier()
    if repo is None:
        repo = MemoryRepository(clock)
    if sandbox is None:
        sandbox = ContainerizedSandbox(
            container_image="localhost/docleaner/pdf_cleaner",
            podman_uri="unix:///run/podman.sock",
        )
    if queue is None:
        queue = DummyJobQueue(repo, sandbox)
    return Adapters(
        clock=clock,
        file_identifier=file_identifier,
        queue=queue,
        repo=repo,
        sandbox=sandbox,
    )
