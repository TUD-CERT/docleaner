from collections import OrderedDict
import dataclasses
from datetime import timedelta
import logging
from typing import Dict, List, Optional, Set

from docleaner.api.core.job import Job, JobParams, JobStatus, JobType
from docleaner.api.core.metadata import DocumentMetadata
from docleaner.api.core.session import Session
from docleaner.api.services.clock import Clock
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token

logger = logging.getLogger(__name__)


class MemoryRepository(Repository):
    """Repository implementation that stores all jobs in memory without further persistence."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._jobs: Dict[str, Job] = (
            OrderedDict()
        )  # Preserve insertion order (job creation)
        self._sessions: Dict[str, Session] = {}
        self._total_jobs = 0
        logger.info("Database backend: In-Memory Repository")

    async def add_job(
        self,
        src: bytes,
        src_name: str,
        job_type: JobType,
        params: Optional[JobParams] = None,
        sid: Optional[str] = None,
    ) -> str:
        if sid is not None and sid not in self._sessions:
            raise ValueError(
                f"Can't add to session {sid}, because the ID doesn't exist"
            )
        if params is None:
            params = JobParams()
        jid = generate_token()
        now = self._clock.now()
        job = Job(
            id=jid,
            src=src,
            name=src_name,
            type=job_type,
            params=params,
            created=now,
            session_id=sid,
        )
        self._jobs[jid] = job
        if sid is not None:
            self._sessions[sid].updated = now
        self._total_jobs += 1
        return jid

    async def find_job(self, jid: str) -> Optional[Job]:
        return self._jobs.get(jid)

    async def find_jobs(
        self,
        sid: Optional[str] = None,
        status: Optional[List[JobStatus]] = None,
        not_updated_for: Optional[timedelta] = None,
    ) -> List[Job]:
        result = []
        if sid is not None and sid not in self._sessions:
            raise ValueError(
                f"Can't fetch jobs from session {sid}, because the ID doesn't exist"
            )
        for job in self._jobs.values():
            if sid is not None and job.session_id != sid:
                continue
            if status is not None and job.status not in status:
                continue
            if (
                not_updated_for is not None
                and self._clock.now() - job.updated < not_updated_for
            ):
                continue
            # Strip metadata, src and result document
            j = dataclasses.replace(
                job,
                src=b"",
                result=b"",
                log=[],
                metadata_result=None,
                metadata_src=None,
            )
            j.updated = job.updated
            result.append(j)
        return result

    async def update_job(
        self,
        jid: str,
        metadata_result: Optional[DocumentMetadata] = None,
        metadata_src: Optional[DocumentMetadata] = None,
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
        now = self._clock.now()
        job.updated = now
        # If associated with a session, also update that session
        if job.session_id is not None:
            self._sessions[job.session_id].updated = now

    async def add_to_job_log(self, jid: str, entry: str) -> None:
        job = self._jobs.get(jid)
        if job is None:
            raise ValueError(f"No job with ID {jid}")
        job.log.append(entry)

    async def delete_job(self, jid: str) -> None:
        if jid not in self._jobs:
            raise ValueError(f"Can't delete job {jid}, because the ID doesn't exist")
        sid = self._jobs[jid].session_id
        if sid is not None:
            self._sessions[sid].updated = self._clock.now()
        del self._jobs[jid]

    async def get_total_job_count(self) -> int:
        return self._total_jobs

    async def add_session(self) -> str:
        sid = generate_token()
        session = Session(id=sid, created=self._clock.now())
        self._sessions[sid] = session
        return sid

    async def find_session(self, sid: str) -> Optional[Session]:
        return self._sessions.get(sid)

    async def find_sessions(
        self, not_updated_for: Optional[timedelta] = None
    ) -> Set[Session]:
        result = set()
        for session in self._sessions.values():
            if (
                not_updated_for is not None
                and self._clock.now() - session.updated < not_updated_for
            ):
                continue
            result.add(session)
        return result

    async def delete_session(self, sid: str) -> None:
        if sid not in self._sessions:
            raise ValueError(
                f"Can't delete session {sid}, because the ID doesn't exist"
            )
        for job in await self.find_jobs(sid):
            await self.delete_job(job.id)
        del self._sessions[sid]
