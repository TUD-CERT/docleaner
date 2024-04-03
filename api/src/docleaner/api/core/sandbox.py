import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from docleaner.api.core.job import JobParams


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
    processes it according to a set of rules and returns the result."""

    @abc.abstractmethod
    async def process(self, source: bytes, params: "JobParams") -> SandboxResult:
        """Transforms the given source into a result document. Additional params are
        implementation-specific and can be utilized to configure the transformation process.
        The implementation is required to be fail-safe and not raise any exceptions,
        since those aren't expected to be handled by the responsible job queue."""
        raise NotImplementedError()
