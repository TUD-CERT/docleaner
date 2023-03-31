import os
from typing import List, Optional, Tuple

from docleaner.api.adapters.clock.system_clock import SystemClock
from docleaner.api.adapters.file_identifier.magic_file_identifier import (
    MagicFileIdentifier,
)
from docleaner.api.adapters.job_queue.async_job_queue import AsyncJobQueue
from docleaner.api.adapters.repository.mongodb_repository import MongoDBRepository
from docleaner.api.core.job import JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository


def bootstrap(
    job_types: List[JobType],
    clock: Optional[Clock] = None,
    file_identifier: Optional[FileIdentifier] = None,
    queue: Optional[JobQueue] = None,
    repo: Optional[Repository] = None,
) -> Tuple[Clock, FileIdentifier, List[JobType], JobQueue, Repository]:
    """Initializes and returns adapters and service components."""
    if clock is None:
        clock = SystemClock()
    if file_identifier is None:
        file_identifier = MagicFileIdentifier()
    if repo is None:
        repo = MongoDBRepository(clock, job_types, "database", 27017)
    if queue is None:
        available_cpu_cores = len(os.sched_getaffinity(0))
        queue = AsyncJobQueue(repo, available_cpu_cores)
    return clock, file_identifier, job_types, queue, repo
