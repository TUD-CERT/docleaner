import abc
from dataclasses import dataclass, field
import traceback
from typing import Any, Dict, List

from docleaner.api.core.job import JobStatus
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.repository import Repository


@dataclass(kw_only=True)
class SandboxResult:
    """After processing a job, a sandbox returns an instance of this
    to indicate success or errors, pass on log data, the actual result
    and associated document metadata."""

    success: bool
    log: List[str]  # A list of collected log lines
    result: bytes = field(repr=False)  # Raw result document
    metadata_result: Dict[str, Dict[str, Any]]  # Document metadata after conversion
    metadata_src: Dict[str, Dict[str, Any]]  # Document metadata prior to conversion


class Sandbox(abc.ABC):
    """Interface for an isolated process that receives a document file,
    attempts to purge its metadata and returns the result."""

    @abc.abstractmethod
    async def process(self, source: bytes) -> SandboxResult:
        """Transforms the given source document by removing associated metadata.
        Returns a tuple of the form (log_data, success, resulting clean file)."""
        raise NotImplementedError()


async def process_job_in_sandbox(
    jid: str, job_types: List[SupportedJobType], repo: Repository
) -> None:
    """Executes the job identified by jid in a sandbox, post-processes the resulting metadata
    and updates the job within the repository according to the result."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"No job with ID {jid} found")
    if job.status != JobStatus.QUEUED:
        raise ValueError(
            f"Can't execute job {jid}, because it's not in QUEUED state (state is {job.status})"
        )
    job_type = next(jt for jt in job_types if jt.type == job.type)
    await repo.update_job(jid, status=JobStatus.RUNNING)
    result = await job_type.sandbox.process(job.src)
    for logline in result.log:
        await repo.add_to_job_log(jid, logline)
    try:
        metadata_result = job_type.metadata_processor(result.metadata_result)
        metadata_src = job_type.metadata_processor(result.metadata_src)
        await repo.update_job(
            jid=jid,
            status=JobStatus.SUCCESS if result.success else JobStatus.ERROR,
            result=result.result,
            metadata_result=metadata_result,
            metadata_src=metadata_src,
        )
    except Exception:
        traceback.print_exc()
        await repo.add_to_job_log(jid, "Error during metadata post-processing")
        await repo.update_job(
            jid=jid,
            status=JobStatus.ERROR,
            result=None,
            metadata_result=None,
            metadata_src=None,
        )
