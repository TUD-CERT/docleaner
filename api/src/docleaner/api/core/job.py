from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Dict, List, Optional


class JobStatus(IntEnum):
    CREATED = 0  # Default state for newly created and yet not queued jobs
    QUEUED = 1  # Job is enqueued and waiting to be picked up by a worker
    RUNNING = 2  # Job is currently being executed
    SUCCESS = 3  # Job execution was successful, the result is available
    ERROR = 4  # Job execution threw an error, a log is available


class JobType(IntEnum):
    PDF = 0


@dataclass(eq=False, kw_only=True)
class Job:
    """A document cleaning job."""

    src: bytes = field(repr=False)  # Source, the document to clean
    type: JobType  # Source document type, selects a worker to handle this job
    created: datetime  # Job creation timestamp
    updated: datetime = field(init=False)  # Last update timestamp
    id: Optional[str] = None  # Unique identifier
    # Log data for progress monitoring and debugging
    log: List[str] = field(default_factory=list)
    # Document metadata associated with the resulting document
    metadata_result: Dict[str, str] = field(default_factory=dict)
    # Document metadata associated with the source document
    metadata_src: Dict[str, str] = field(default_factory=dict)
    result: bytes = field(default=b"", repr=False)  # Resulting cleaned document
    status: JobStatus = JobStatus.CREATED

    def __post_init__(self) -> None:
        self.updated = self.created
