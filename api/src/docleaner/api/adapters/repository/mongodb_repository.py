from dataclasses import asdict
from datetime import timedelta
from typing import Any, Dict, List, Optional, Set

from motor import motor_asyncio
import pymongo

from docleaner.api.core.job import JobStatus, Job, JobType
from docleaner.api.core.session import Session
from docleaner.api.services.clock import Clock
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token


class MongoDBRepository(Repository):
    """Repository implementation backed by MongoDB."""

    def __init__(
        self, clock: Clock, db_host: str, db_port: int, db_name: str = "docleaner"
    ) -> None:
        self._clock = clock
        self._mongo = motor_asyncio.AsyncIOMotorClient(db_host, db_port)
        self._db = self._mongo[db_name]
        self._fs = motor_asyncio.AsyncIOMotorGridFSBucket(self._db)  # type: ignore

    async def add_job(
        self, src: bytes, src_name: str, job_type: JobType, sid: Optional[str] = None
    ) -> str:
        if sid is not None and await self._db.sessions.find_one({"_id": sid}) is None:
            raise ValueError(
                f"Can't add to session {sid}, because the ID doesn't exist"
            )
        jid = generate_token()
        now = self._clock.now()
        # Save source document in GridFS
        src_id = await self._fs.upload_from_stream(jid, src)
        job = Job(
            id=jid,
            src=src_id,
            name=src_name,
            type=job_type,
            created=now,
            session_id=sid,
        )
        serialized_job = asdict(job)
        serialized_job["_id"] = serialized_job.pop("id")
        await self._db.jobs.insert_one(serialized_job)
        if sid is not None:
            await self._db.sessions.update_one({"_id": sid}, {"$set": {"updated": now}})
        # Increment total job count
        self._db.stats.update_one(
            {"type": "jobs"}, {"$inc": {"total_count": 1}}, upsert=True
        )
        return jid

    async def find_job(self, jid: str) -> Optional[Job]:
        job_data = await self._db.jobs.find_one({"_id": jid})
        if job_data is None:
            return None
        return await self._create_job_from_job_data(job_data)

    async def find_jobs(
        self,
        sid: Optional[str] = None,
        status: Optional[List[JobStatus]] = None,
        not_updated_for: Optional[timedelta] = None,
    ) -> List[Job]:
        if sid is not None and await self._db.sessions.find_one({"_id": sid}) is None:
            raise ValueError(
                f"Can't fetch jobs from session {sid}, because the ID doesn't exist"
            )
        conditions: Dict[str, Any] = {}
        if sid is not None:
            conditions["session_id"] = sid
        if status is not None:
            conditions["status"] = {"$in": status}
        if not_updated_for is not None:
            conditions["updated"] = {"$lt": self._clock.now() - not_updated_for}
        return [
            await self._create_job_from_job_data(job_data, True)
            async for job_data in self._db.jobs.find(conditions).sort(
                "created", pymongo.DESCENDING
            )
        ]

    async def update_job(
        self,
        jid: str,
        metadata_result: Optional[Dict[str, Dict[str, Any]]] = None,
        metadata_src: Optional[Dict[str, Dict[str, Any]]] = None,
        result: Optional[bytes] = None,
        status: Optional[JobStatus] = None,
    ) -> None:
        job = await self._db.jobs.find_one({"_id": jid})
        if job is None:
            raise ValueError(f"No job with ID {jid}")
        now = self._clock.now()
        update_fields: Dict[str, Any] = {"updated": now}
        if metadata_result is not None:
            update_fields["metadata_result"] = metadata_result
        if metadata_src is not None:
            update_fields["metadata_src"] = metadata_src
        if result is not None:
            # Save result document in GridFS
            result_id = await self._fs.upload_from_stream(jid, result)
            update_fields["result"] = result_id
        if status is not None:
            update_fields["status"] = status
        await self._db.jobs.update_one({"_id": jid}, {"$set": update_fields})
        # If associated with a session, also update that session
        if job["session_id"] is not None:
            await self._db.sessions.update_one(
                {"_id": job["session_id"]}, {"$set": {"updated": now}}
            )

    async def add_to_job_log(self, jid: str, entry: str) -> None:
        if await self._db.jobs.find_one({"_id": jid}) is None:
            raise ValueError(f"No job with ID {jid}")
        await self._db.jobs.update_one({"_id": jid}, {"$push": {"log": entry}})

    async def delete_job(self, jid: str) -> None:
        job_data = await self._db.jobs.find_one({"_id": jid})
        if job_data is None:
            raise ValueError(f"Can't delete job {jid}, because the ID doesn't exist")
        if job_data["session_id"] is not None:
            await self._db.sessions.update_one(
                {"_id": job_data["session_id"]},
                {"$set": {"updated": self._clock.now()}},
            )
        # Delete associated fragments in GridFS
        self._fs.delete(job_data["src"])
        if job_data["result"] != b"":
            self._fs.delete(job_data["result"])
        await self._db.jobs.delete_one({"_id": jid})

    async def get_total_job_count(self) -> int:
        job_stats = await self._db.stats.find_one({"type": "jobs"})
        if job_stats is None:
            return 0
        assert isinstance(job_stats["total_count"], int)
        return job_stats["total_count"]

    async def add_session(self) -> str:
        sid = generate_token()
        session = Session(id=sid, created=self._clock.now())
        serialized_session = asdict(session)
        serialized_session["_id"] = serialized_session.pop("id")
        await self._db.sessions.insert_one(serialized_session)
        return sid

    async def find_session(self, sid: str) -> Optional[Session]:
        session_data = await self._db.sessions.find_one({"_id": sid})
        if session_data is None:
            return None
        return self._create_session_from_session_data(session_data)

    async def find_sessions(
        self, not_updated_for: Optional[timedelta] = None
    ) -> Set[Session]:
        conditions = {}
        if not_updated_for is not None:
            conditions["updated"] = {"$lt": self._clock.now() - not_updated_for}
        return {
            self._create_session_from_session_data(session_data)
            async for session_data in self._db.sessions.find(conditions)
        }

    async def delete_session(self, sid: str) -> None:
        session = await self.find_session(sid)
        if session is None:
            raise ValueError(
                f"Can't delete session {sid}, because the ID doesn't exist"
            )
        await self._db.jobs.delete_many({"session_id": sid})
        await self._db.sessions.delete_one({"_id": sid})

    async def disconnect(self) -> None:
        self._mongo.close()

    async def _create_job_from_job_data(
        self, job_data: Dict[str, Any], summary_only: bool = False
    ) -> Job:
        """Creates Job instances from raw job data as returned by MongoDB.
        If summary_only is True, omit metadata, the job log, src and result document data from the result."""
        job_data["id"] = job_data.pop("_id")
        updated = job_data.pop("updated")
        if summary_only:
            job_data["src"] = b""
            job_data["result"] = b""
            job_data["log"] = []
            job_data["metadata_result"] = {}
            job_data["metadata_src"] = {}
        else:
            # Retrieve src and result documents from GridFS
            job_data["src"] = await (
                await self._fs.open_download_stream(job_data["src"])
            ).read()
            if job_data["result"] != b"":
                job_data["result"] = await (
                    await self._fs.open_download_stream(job_data["result"])
                ).read()
        job = Job(**job_data)
        job.updated = updated
        return job

    @staticmethod
    def _create_session_from_session_data(session_data: Dict[str, Any]) -> Session:
        """Creates Session instances from raw session data as returned by MongoDB."""
        session_data["id"] = session_data.pop("_id")
        updated = session_data.pop("updated")
        session = Session(**session_data)
        session.updated = updated
        return session
