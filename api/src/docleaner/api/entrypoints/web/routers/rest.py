from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel
import starlette.status as status

from docleaner.api.core.job import JobParams, JobStatus, JobType
from docleaner.api.core.metadata import DocumentMetadata
from docleaner.api.entrypoints.web.dependencies import (
    get_base_url,
    get_file_identifier,
    get_job_types,
    get_queue,
    get_repo,
)
from docleaner.api.entrypoints.web.routers.web import (
    OctetStreamResponse,
    jobs_get_result as web_jobs_get_result,
)
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.jobs import create_job, delete_job, get_job
from docleaner.api.services.repository import Repository
from docleaner.api.services.sessions import create_session, delete_session, get_session


rest_api = APIRouter(prefix="/api/v1")


class JobDetails(BaseModel):
    id: str
    type: str
    log: List[str]
    metadata_result: Optional[DocumentMetadata]
    metadata_src: Optional[DocumentMetadata]
    status: JobStatus


class JobAbbreviatedDetails(BaseModel):
    id: str
    created: datetime
    updated: datetime
    type: str
    status: JobStatus


class SessionDetails(BaseModel):
    id: str
    created: datetime
    updated: datetime
    jobs_total: int
    jobs_finished: int
    jobs: Optional[List[JobAbbreviatedDetails]]


class RESTException(HTTPException):
    pass


@rest_api.post("/jobs", response_model=JobDetails, status_code=201)
async def jobs_create(
    response: Response,
    doc_src: UploadFile,
    session: Optional[str] = None,
    base_url: str = Depends(get_base_url),
    file_identifier: FileIdentifier = Depends(get_file_identifier),
    job_types: List[JobType] = Depends(get_job_types),
    repo: Repository = Depends(get_repo),
    queue: JobQueue = Depends(get_queue),
) -> Any:
    try:
        jid, _ = await create_job(
            await doc_src.read(),
            doc_src.filename or "",
            repo,
            queue,
            file_identifier,
            job_types,
            JobParams(),
            session,
        )
        (
            job_status,
            job_type,
            job_log,
            job_metadata_src,
            job_metadata_result,
            _,
        ) = await get_job(jid, repo)
        response.headers["Location"] = f"{base_url}/api/v1/jobs/{jid}"
        return {
            "id": jid,
            "type": job_type.id,
            "log": job_log,
            "metadata_result": job_metadata_result,
            "metadata_src": job_metadata_src,
            "status": job_status,
        }
    except ValueError:
        raise RESTException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You uploaded an unsupported document type.",
        )


@rest_api.get("/jobs/{jid}", response_model=JobDetails)
async def jobs_get(jid: str, repo: Repository = Depends(get_repo)) -> Any:
    try:
        (
            job_status,
            job_type,
            job_log,
            job_metadata_src,
            job_metadata_result,
            _,
        ) = await get_job(jid, repo)
    except ValueError:
        raise RESTException(status_code=status.HTTP_404_NOT_FOUND)
    return {
        "id": jid,
        "type": job_type.id,
        "log": job_log,
        "metadata_result": job_metadata_result,
        "metadata_src": job_metadata_src,
        "status": job_status,
    }


@rest_api.get(
    "/jobs/{jid}/result", response_class=OctetStreamResponse, response_model=None
)
async def jobs_get_result(jid: str, repo: Repository = Depends(get_repo)) -> Response:
    return await web_jobs_get_result(jid, repo)


@rest_api.delete("/jobs/{jid}", response_model=None, status_code=204)
async def jobs_delete(jid: str, repo: Repository = Depends(get_repo)) -> Response:
    try:
        await delete_job(jid, repo)
    except ValueError:
        raise RESTException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@rest_api.post("/sessions", response_model=SessionDetails, status_code=201)
async def sessions_create(
    response: Response,
    base_url: str = Depends(get_base_url),
    repo: Repository = Depends(get_repo),
) -> Any:
    sid = await create_session(repo)
    response.headers["Location"] = f"{base_url}/api/v1/sessions/{sid}"
    created, updated, jobs_total, jobs_finished, jobs = await get_session(sid, repo)
    jobs_serialized = [
        (created, updated, total_jobs, finished_jobs, jobs.id)
        for created, updated, total_jobs, finished_jobs, jobs in jobs
    ]
    return {
        "id": sid,
        "created": created,
        "updated": updated,
        "jobs_total": jobs_total,
        "jobs_finished": jobs_finished,
        "jobs": jobs_serialized,
    }


@rest_api.get("/sessions/{sid}", response_model=SessionDetails)
async def sessions_get(
    sid: str, jobs: bool = True, repo: Repository = Depends(get_repo)
) -> Any:
    try:
        created, updated, jobs_total, jobs_finished, job_list = await get_session(
            sid, repo
        )
    except ValueError:
        raise RESTException(status_code=status.HTTP_404_NOT_FOUND)
    result = {
        "id": sid,
        "created": created,
        "updated": updated,
        "jobs_total": jobs_total,
        "jobs_finished": jobs_finished,
        "jobs": None,
    }
    if jobs:
        result["jobs"] = [
            {
                "id": jid,
                "created": job_created,
                "updated": job_updated,
                "type": job_type.id,
                "status": job_status,
            }
            for jid, job_created, job_updated, job_status, job_type in job_list
        ]
    return result


@rest_api.delete("/sessions/{sid}", response_model=None, status_code=204)
async def sessions_delete(sid: str, repo: Repository = Depends(get_repo)) -> Response:
    try:
        await delete_session(sid, repo)
    except ValueError:
        raise RESTException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
