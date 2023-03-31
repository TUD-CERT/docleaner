import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Union


@dataclass(kw_only=True)
class SandboxResult:
    """After processing a job, a sandbox returns an instance of this
    to indicate success or errors, pass on log data, the actual result
    and associated document metadata."""

    success: bool
    log: List[str]  # A list of collected log lines
    result: bytes = field(repr=False)  # Raw result document
    metadata_result: Dict[
        str, Union[bool, Dict[str, Any]]
    ]  # Document metadata after conversion
    metadata_src: Dict[
        str, Union[bool, Dict[str, Any]]
    ]  # Document metadata prior to conversion


class Sandbox(abc.ABC):
    """Interface for an isolated process that receives a document file,
    attempts to purge its metadata and returns the result."""

    @abc.abstractmethod
    async def process(self, source: bytes) -> SandboxResult:
        """Transforms the given source document by removing associated metadata.
        Returns a tuple of the form (log_data, success, resulting clean file)."""
        raise NotImplementedError()
