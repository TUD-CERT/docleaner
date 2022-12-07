import abc
from typing import List, Tuple

from docleaner.api.core.job import JobStatus
from docleaner.api.services.repository import Repository


class Sandbox(abc.ABC):
    """Interface for an isolated process that receives a document file,
    attempts to purge its metadata and returns the result."""

    @abc.abstractmethod
    async def process(self, source: bytes) -> Tuple[List[str], bool, bytes]:
        """Transforms the given source document by removing associated metadata.
        Returns a tuple of the form (log_data, success, resulting clean file)."""
        raise NotImplementedError()


async def process_job_in_sandbox(jid: str, sandbox: Sandbox, repo: Repository) -> None:
    """Executes the job identified by jid in a sandbox and updates the job within the
    repository according to the result."""
    job = await repo.find_job(jid)
    if job is None:
        raise ValueError(f"No job with ID {jid} found")
    if job.status != JobStatus.QUEUED:
        raise ValueError(
            f"Can't execute job {jid}, because it's not in QUEUED state (state is {job.status})"
        )
    log_data, success, result = await sandbox.process(job.src)
    for d in log_data:
        await repo.add_to_job_log(jid, d)
    await repo.update_job(
        jid=jid, status=JobStatus.SUCCESS if success else JobStatus.ERROR, result=result
    )
