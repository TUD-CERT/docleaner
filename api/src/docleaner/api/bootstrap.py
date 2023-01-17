from dataclasses import dataclass
import os
from typing import List, Optional

from docleaner.api.adapters.clock.system_clock import SystemClock
from docleaner.api.adapters.file_identifier.magic_file_identifier import (
    MagicFileIdentifier,
)
from docleaner.api.adapters.job_queue.async_job_queue import AsyncJobQueue
from docleaner.api.adapters.repository.mongodb_repository import MongoDBRepository
from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.core.job import JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.metadata import process_pdf_metadata
from docleaner.api.services.repository import Repository


@dataclass(eq=False, kw_only=True)
class Adapters:
    """Instantiates an evil god object that holds adapter instances
    the entrypoints need for calling the service layer."""

    clock: Clock
    file_identifier: FileIdentifier
    job_types: List[SupportedJobType]
    queue: JobQueue
    repo: Repository


def bootstrap(
    clock: Optional[Clock] = None,
    file_identifier: Optional[FileIdentifier] = None,
    job_types: Optional[List[SupportedJobType]] = None,
    queue: Optional[JobQueue] = None,
    repo: Optional[Repository] = None,
) -> Adapters:
    """Initializes adapters and service components.
    Returns a composite object with all adapters attached."""
    if clock is None:
        clock = SystemClock()
    if file_identifier is None:
        file_identifier = MagicFileIdentifier()
    if repo is None:
        repo = MongoDBRepository(clock, "database", 27017)
    if job_types is None:
        job_types = [
            SupportedJobType(
                type=JobType.PDF,
                mimetypes=["application/pdf"],
                sandbox=ContainerizedSandbox(
                    container_image="localhost/docleaner/pdf_cleaner",
                    podman_uri="unix:///run/podman.sock",
                ),
                metadata_processor=process_pdf_metadata,
            )
        ]
    if queue is None:
        available_cpu_cores = len(os.sched_getaffinity(0))
        queue = AsyncJobQueue(repo, job_types, available_cpu_cores)
    return Adapters(
        clock=clock,
        file_identifier=file_identifier,
        job_types=job_types,
        queue=queue,
        repo=repo,
    )
