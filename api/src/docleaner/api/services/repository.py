import abc
from datetime import timedelta
from typing import List, Optional, Set

from docleaner.api.core.job import Job, JobStatus, JobType
from docleaner.api.core.metadata import DocumentMetadata
from docleaner.api.core.session import Session


class Repository(abc.ABC):
    """Repository to store and retrieve job data without support for transactions."""

    @abc.abstractmethod
    async def add_job(
        self, src: bytes, src_name: str, job_type: JobType, sid: Optional[str] = None
    ) -> str:
        """Creates a job of a specific type for a given source document and returns the
        resulting job id. If sid is given, the job is association with that session."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_job(self, jid: str) -> Optional[Job]:
        """Returns the job identified by jid, if it exists. Otherwise, this returns None."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_jobs(
        self,
        sid: Optional[str] = None,
        status: Optional[List[JobStatus]] = None,
        not_updated_for: Optional[timedelta] = None,
    ) -> List[Job]:
        """Returns a list of all currently registered jobs, optionally filtered by different criteria:
        * a session id to find all jobs associated with that session
        * a list of status flags to only find jobs that have one of the given statuses
        * a timedelta to find jobs that haven't been updated for a given amount of time.
        The result is sorted descending by job creation date.
        To improve performance, the resulting Job objects hold no metadata, no job log
        and no src/result document data. Those attributes have to be fetched individually via find_job().
        """
        raise NotImplementedError()

    @abc.abstractmethod
    async def update_job(
        self,
        jid: str,
        metadata_result: Optional[DocumentMetadata] = None,
        metadata_src: Optional[DocumentMetadata] = None,
        result: Optional[bytes] = None,
        status: Optional[JobStatus] = None,
    ) -> None:
        """Updates a job's result and/or status flag.
        In addition, transparently refreshes the 'updated' field of the job itself and its
        session (in case its associated with one)."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def add_to_job_log(self, jid: str, entry: str) -> None:
        """Adds an entry to a job's log."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def delete_job(self, jid: str) -> None:
        """Deletes a job, identified by its jid, from the repository."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_total_job_count(self) -> int:
        """Returns the total number of jobs this database has processed,
        no matter the job status or whether those jobs still exist in the repository."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def add_session(self) -> str:
        """Creates a session and returns the resulting session id."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_session(self, sid: str) -> Optional[Session]:
        """Returns the session identified by sid, if it exists. Otherwise, this returns None."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_sessions(
        self, not_updated_for: Optional[timedelta] = None
    ) -> Set[Session]:
        """Returns a set of all currently registered sessions, optionally filtered by
        a timedelta to find sessions that haven't been updated for a given amount of time."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def delete_session(self, sid: str) -> None:
        """Deletes a session, identified by its sid, from the repository.
        In addition, deletes all jobs associated with that session regardless of their status."""
        raise NotImplementedError()

    async def disconnect(self) -> None:
        """Instruct the repository to disconnect from its backend and perform cleanup work."""
        pass
