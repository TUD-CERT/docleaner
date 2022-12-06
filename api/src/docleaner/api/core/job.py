from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


class JobStatus(IntEnum):
    QUEUED = 0  # Job is waiting to be picked by a worker
    RUNNING = 1  # Job is currently being executed
    SUCCESS = 2  # Job execution was successful, the result is available
    ERROR = 3  # Job execution threw an error, a log is available


class JobType(IntEnum):
    PDF = 0


@dataclass(eq=False, kw_only=True)
class Job:
    """A document cleaning job."""

    src: bytes  # Source, the document to clean
    type: JobType  # Source document type, selects a worker to handle this job
    id: Optional[str] = None  # Unique identifier
    log: List[str] = field(
        default_factory=list
    )  # Log data for progress monitoring and debugging
    result: bytes = b""  # Resulting cleaned document
    status: JobStatus = JobStatus.QUEUED
