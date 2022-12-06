import abc
from typing import Optional, Set

from docleaner.api.core.job import Job, JobStatus


class Repository(abc.ABC):
    """Repository to store and retrieve job data without support for transactions."""

    @abc.abstractmethod
    async def add_job(self, job: Job) -> str:
        """Adds a job to the repository and returns the resulting job id."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_job(self, jid: str) -> Optional[Job]:
        """Returns the job identified by jid, if it exists. Otherwise, this returns None."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_jobs(self) -> Set[Job]:
        """Returns a set of all currently registered jobs."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def update_job(
        self,
        jid: str,
        result: Optional[bytes] = None,
        status: Optional[JobStatus] = None,
    ) -> None:
        """Updates a job's result and/or status flag."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def add_to_job_log(self, jid: str, entry: str) -> None:
        """Adds an entry to a job's log."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def delete_job(self, jid: str) -> None:
        """Deletes a job, identified by its jid, from the repository."""
        raise NotImplementedError()
