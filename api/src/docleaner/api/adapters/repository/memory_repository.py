from typing import Any, Dict, Optional, Set

from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.services.clock import Clock
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token


class MemoryRepository(Repository):
    """Repository implementation that stores all jobs in memory without further persistence."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._jobs: Dict[str, Job] = {}

    async def add_job(self, src: bytes, src_name: str, job_type: JobType) -> str:
        jid = generate_token()
        job = Job(
            id=jid, src=src, name=src_name, type=job_type, created=self._clock.now()
        )
        self._jobs[jid] = job
        return jid

    async def find_job(self, jid: str) -> Optional[Job]:
        return self._jobs.get(jid)

    async def find_jobs(self) -> Set[Job]:
        return {j for j in self._jobs.values()}

    async def update_job(
        self,
        jid: str,
        metadata_result: Optional[Dict[str, Dict[str, Any]]] = None,
        metadata_src: Optional[Dict[str, Dict[str, Any]]] = None,
        result: Optional[bytes] = None,
        status: Optional[JobStatus] = None,
    ) -> None:
        job = self._jobs.get(jid)
        if job is None:
            raise ValueError(f"No job with ID {jid}")
        if metadata_result is not None:
            job.metadata_result = metadata_result
        if metadata_src is not None:
            job.metadata_src = metadata_src
        if result is not None:
            job.result = result
        if status is not None:
            job.status = status
        job.updated = self._clock.now()

    async def add_to_job_log(self, jid: str, entry: str) -> None:
        job = self._jobs.get(jid)
        if job is None:
            raise ValueError(f"No job with ID {jid}")
        job.log.append(entry)

    async def delete_job(self, jid: str) -> None:
        if jid not in self._jobs:
            raise ValueError(f"Can't delete job {jid}, because the ID doesn't exist")
        del self._jobs[jid]
