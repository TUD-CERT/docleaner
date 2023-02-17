from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import List, Optional

from docleaner.api.core.metadata import DocumentMetadata


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

    id: str  # Unique identifier
    src: bytes = field(repr=False)  # Source, the document to clean
    name: str  # Source document name, typically its filename
    type: JobType  # Source document type, selects a worker to handle this job
    created: datetime  # Job creation timestamp
    updated: datetime = field(init=False)  # Last update timestamp
    # Log data for progress monitoring and debugging
    log: List[str] = field(default_factory=list)
    # Document metadata associated with the resulting document
    metadata_result: Optional[DocumentMetadata] = None
    # Document metadata associated with the source document
    metadata_src: Optional[DocumentMetadata] = None
    result: bytes = field(default=b"", repr=False)  # Resulting cleaned document
    status: JobStatus = JobStatus.CREATED
    session_id: Optional[str] = None  # Associated session (optional)

    def __post_init__(self) -> None:
        self.updated = self.created
