from dataclasses import asdict
from datetime import timedelta
import logging
from typing import Any, Dict, List, Optional, Set, Union

from motor import motor_asyncio
import pymongo

from docleaner.api.core.job import Job, JobParams, JobStatus, JobType
from docleaner.api.core.metadata import DocumentMetadata, MetadataField
from docleaner.api.core.session import Session
from docleaner.api.services.clock import Clock
from docleaner.api.services.repository import Repository
from docleaner.api.utils import generate_token

logger = logging.getLogger(__name__)


class MongoDBRepository(Repository):
    """Repository implementation backed by MongoDB."""

    def __init__(
        self,
        clock: Clock,
        job_types: List[JobType],
        db_host: str,
        db_port: int,
        db_name: str = "docleaner",
    ) -> None:
        self._clock = clock
        self._job_types = job_types
        self._mongo = motor_asyncio.AsyncIOMotorClient(db_host, db_port)
        self._db = self._mongo[db_name]
        self._fs = motor_asyncio.AsyncIOMotorGridFSBucket(self._db)  # type: ignore
        logger.info("Database backend: MongoDB (%s:%d/%s)", db_host, db_port, db_name)

    async def add_job(
        self,
        src: bytes,
        src_name: str,
        job_type: JobType,
        params: Optional[JobParams] = None,
        sid: Optional[str] = None,
    ) -> str:
        if sid is not None and await self._db.sessions.find_one({"_id": sid}) is None:
            raise ValueError(
                f"Can't add to session {sid}, because the ID doesn't exist"
            )
        if params is None:
            params = JobParams()
        jid = generate_token()
        now = self._clock.now()
        # Save source document to GridFS
        logger.debug("Storing job %s src in GridFS", jid)
        src_id = await self._fs.upload_from_stream(jid, src)
        job = Job(
            id=jid,
            src=src_id,
            name=src_name,
            type=job_type,
            params=params,
            created=now,
            session_id=sid,
        )
        serialized_job = asdict(job)
        serialized_job["type"] = job_type.id
        serialized_job["_id"] = serialized_job.pop("id")
        logger.debug("Adding job %s (%s)", jid, sid)
        await self._db.jobs.insert_one(serialized_job)
        if sid is not None:
            await self._db.sessions.update_one({"_id": sid}, {"$set": {"updated": now}})
        # Increment total job count
        await self._db.stats.update_one(
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
        metadata_result: Optional[DocumentMetadata] = None,
        metadata_src: Optional[DocumentMetadata] = None,
        result: Optional[bytes] = None,
        status: Optional[JobStatus] = None,
    ) -> None:
        job = await self._db.jobs.find_one({"_id": jid})
        if job is None:
            raise ValueError(f"No job with ID {jid}")
        now = self._clock.now()
        update_fields: Dict[str, Any] = {"updated": now}
        if metadata_result is not None:
            update_fields["metadata_result"] = asdict(metadata_result)
        if metadata_src is not None:
            update_fields["metadata_src"] = asdict(metadata_src)
        if result is not None:
            # Save result document to GridFS
            result_id = await self._fs.upload_from_stream(jid, result)
            update_fields["result"] = result_id
        if status is not None:
            update_fields["status"] = status
        logger.debug("Updating job %s (%s)", jid, ", ".join(update_fields.keys()))
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
        # Delete associated fragments from GridFS
        logger.debug("Deleting GridFS data of job %s", jid)
        self._fs.delete(job_data["src"])
        if job_data["result"] != b"":
            self._fs.delete(job_data["result"])
        logger.debug("Deleting job %s", jid)
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
        logger.debug("Adding session %s", sid)
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
        # Delete associated job fragments from GridFS
        logger.debug("Deleting GridFS data of session %s", sid)
        async for job_data in self._db.jobs.find({"session_id": sid}):
            if job_data["src"] != b"":
                self._fs.delete(job_data["src"])
            if job_data["result"] != b"":
                self._fs.delete(job_data["result"])
        logger.debug("Deleting session %s and all associated jobs", sid)
        await self._db.jobs.delete_many({"session_id": sid})
        await self._db.sessions.delete_one({"_id": sid})

    async def disconnect(self) -> None:
        self._mongo.close()

    @staticmethod
    def _create_document_metadata(
        raw_data: Dict[str, Union[bool, Dict[str, Any]]]
    ) -> DocumentMetadata:
        embeds = {}
        assert isinstance(raw_data["primary"], dict)
        assert isinstance(raw_data["embeds"], dict)
        assert isinstance(raw_data["signed"], bool)
        for embed_id, embed_data in raw_data["embeds"].items():
            embeds[embed_id] = {k: MetadataField(**v) for k, v in embed_data.items()}
        return DocumentMetadata(
            primary={k: MetadataField(**v) for k, v in raw_data["primary"].items()},
            embeds=embeds,
            signed=raw_data["signed"],
        )

    async def _create_job_from_job_data(
        self, job_data: Dict[str, Any], summary_only: bool = False
    ) -> Job:
        """Creates Job instances from raw job data as returned by MongoDB.
        If summary_only is True, omit metadata, the job log, src and result document data from the result.
        """
        job_data["type"] = next(
            filter(lambda jt: jt.id == job_data["type"], self._job_types)
        )
        job_data["id"] = job_data.pop("_id")
        updated = job_data.pop("updated")
        if summary_only:
            job_data["src"] = b""
            job_data["result"] = b""
            job_data["log"] = []
            job_data["metadata_result"] = None
            job_data["metadata_src"] = None
        else:
            # Retrieve src and result documents from GridFS
            job_data["src"] = await (
                await self._fs.open_download_stream(job_data["src"])
            ).read()
            if job_data["result"] != b"":
                job_data["result"] = await (
                    await self._fs.open_download_stream(job_data["result"])
                ).read()
        # Create DocumentMetadata instances
        if job_data["metadata_result"] is not None:
            job_data["metadata_result"] = self._create_document_metadata(
                job_data["metadata_result"]
            )
        if job_data["metadata_src"] is not None:
            job_data["metadata_src"] = self._create_document_metadata(
                job_data["metadata_src"]
            )
        # Create MetadataField and JobParams instances
        job_data["params"]["metadata"] = [
            MetadataField(**m) for m in job_data["params"]["metadata"]
        ]
        job_data["params"] = JobParams(**job_data["params"])
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
