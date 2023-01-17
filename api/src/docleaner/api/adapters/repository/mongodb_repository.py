from dataclasses import asdict
from typing import Optional, Dict, Any, Set

from motor import motor_asyncio

from docleaner.api.core.job import JobStatus, Job, JobType
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

    async def add_job(self, src: bytes, src_name: str, job_type: JobType) -> str:
        jid = generate_token()
        job = Job(
            id=jid, src=src, name=src_name, type=job_type, created=self._clock.now()
        )
        serialized_job = asdict(job)
        serialized_job["_id"] = serialized_job.pop("id")
        await self._db.jobs.insert_one(serialized_job)
        return jid

    async def find_job(self, jid: str) -> Optional[Job]:
        job_data = await self._db.jobs.find_one({"_id": jid})
        if job_data is None:
            return None
        return self._create_job_from_job_data(job_data)

    async def find_jobs(self) -> Set[Job]:
        return {
            self._create_job_from_job_data(job_data)
            async for job_data in self._db.jobs.find()
        }

    async def update_job(
        self,
        jid: str,
        metadata_result: Optional[Dict[str, Dict[str, Any]]] = None,
        metadata_src: Optional[Dict[str, Dict[str, Any]]] = None,
        result: Optional[bytes] = None,
        status: Optional[JobStatus] = None,
    ) -> None:
        if await self.find_job(jid) is None:
            raise ValueError(f"No job with ID {jid}")
        update_fields: Dict[str, Any] = {"updated": self._clock.now()}
        if metadata_result is not None:
            update_fields["metadata_result"] = metadata_result
        if metadata_src is not None:
            update_fields["metadata_src"] = metadata_src
        if result is not None:
            update_fields["result"] = result
        if status is not None:
            update_fields["status"] = status
        await self._db.jobs.update_one({"_id": jid}, {"$set": update_fields})

    async def add_to_job_log(self, jid: str, entry: str) -> None:
        if await self.find_job(jid) is None:
            raise ValueError(f"No job with ID {jid}")
        await self._db.jobs.update_one({"_id": jid}, {"$push": {"log": entry}})

    async def delete_job(self, jid: str) -> None:
        result = await self._db.jobs.delete_one({"_id": jid})
        if result.deleted_count == 0:
            raise ValueError(f"Can't delete job {jid}, because the ID doesn't exist")

    async def disconnect(self) -> None:
        self._mongo.close()

    @staticmethod
    def _create_job_from_job_data(job_data: Dict[str, Any]) -> Job:
        """Creates Job instances from raw job data returned by MongoDB."""
        job_data["id"] = job_data.pop("_id")
        updated = job_data.pop("updated")
        job = Job(**job_data)
        job.updated = updated
        return job
