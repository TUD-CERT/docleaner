from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Union

from docleaner.api.core.metadata import DocumentMetadata, MetadataField
from docleaner.api.core.sandbox import Sandbox


class JobStatus(IntEnum):
    CREATED = 0  # Default state for newly created and yet not queued jobs
    QUEUED = 1  # Job is enqueued and waiting to be picked up by a worker
    RUNNING = 2  # Job is currently being executed
    SUCCESS = 3  # Job execution was successful, the result is available
    ERROR = 4  # Job execution threw an error, a log is available


@dataclass(eq=False, kw_only=True)
class JobType:
    """Represents a supported document type and corresponding handlers."""

    id: str  # Unique identification string
    mimetypes: List[
        str
    ]  # Documents are assigned a job type based on a matching mimetype
    readable_types: List[str]  # Human-readable list of supported document types
    sandbox: Sandbox  # Sandbox instance to hand jobs of this type to
    # Metadata post-processor
    metadata_processor: Callable[
        [Dict[str, Union[bool, Dict[str, Any]]]], DocumentMetadata
    ]


@dataclass(frozen=True, kw_only=True)
class JobParams:
    """Additional parameters that guide job execution."""

    metadata: List[MetadataField] = field(
        default_factory=list
    )  # Metadata to assign to specific fields (instead of using the plugin defaults)


@dataclass(eq=False, kw_only=True)
class Job:
    """A document transformation job."""

    id: str  # Unique identifier
    src: bytes = field(repr=False)  # Source, the document to clean
    name: str  # Source document name, typically its filename
    params: JobParams  # Additional data handed over to the transformation task
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
