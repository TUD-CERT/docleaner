from typing import Dict, Optional, Set

from docleaner.api.core.job import Job, JobStatus
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token


class MemoryRepository(Repository):
    """Repository implementation that stores all jobs in memory without further persistence."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}

    async def add_job(self, job: Job) -> str:
        if job.id is not None:
            raise ValueError("Can't add a job with an existing job identifier")
        job.id = generate_token()
        self._jobs[job.id] = job
        return job.id

    async def find_job(self, jid: str) -> Optional[Job]:
        return self._jobs.get(jid)

    async def find_jobs(self) -> Set[Job]:
        return {j for j in self._jobs.values()}

    async def update_job(
        self,
        jid: str,
        result: Optional[bytes] = None,
        status: Optional[JobStatus] = None,
    ) -> None:
        job = self._jobs.get(jid)
        if job is None:
            raise ValueError(f"No job with ID {jid}")
        if result is not None:
            job.result = result
        if status is not None:
            job.status = status

    async def add_to_job_log(self, jid: str, entry: str) -> None:
        job = self._jobs.get(jid)
        if job is None:
            raise ValueError(f"No job with ID {jid}")
        job.log.append(entry)

    async def delete_job(self, jid: str) -> None:
        if jid not in self._jobs:
            raise ValueError(f"Can't delete job {jid}, because the ID doesn't exist")
        del self._jobs[jid]
