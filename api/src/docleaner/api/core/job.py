from dataclasses import dataclass
from enum import IntEnum
from typing import List


class JobStatus(IntEnum):
    QUEUED = 0  # Job is waiting to be picked by a worker
    RUNNING = 1  # Job is currently being executed
    SUCCESS = 2  # Job execution was successful, the result is available
    ERROR = 3  # Job execution threw an error, a log is available


@dataclass
class Job:
    """A document cleaning job."""

    id: str  # Base64-encoded 160 bit identifier
    log: List[str]  # Log data for progress monitoring and debugging
    result: bytes  # Resulting cleaned document
    src: bytes  # Source, the document to clean
    status: JobStatus = JobStatus.QUEUED
