from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
import starlette.status as status
from starlette.templating import _TemplateResponse
from urllib.parse import quote

from docleaner.api.core.job import JobType
from docleaner.api.entrypoints.web.dependencies import (
    get_base_url,
    get_contact,
    get_file_identifier,
    get_job_types,
    get_queue,
    get_repo,
    get_version,
    templates,
)
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.jobs import create_job, delete_job, get_job, get_job_result
from docleaner.api.services.repository import Repository
from docleaner.api.services.sessions import get_session


web_api = APIRouter(include_in_schema=False)


class WebException(HTTPException):
    pass


class OctetStreamResponse(Response):
    media_type = "application/octet-stream"


@dataclass
class ValidationException(HTTPException):
    params: Dict[str, Any]
    template_full: str
    template_htmx: str

    def __post_init__(self) -> None:
        super().__init__(status_code=422)


@web_api.get("/", response_class=HTMLResponse, response_model=None)
def landing_get(
    request: Request,
    job_types: List[JobType] = Depends(get_job_types),
    version: str = Depends(get_version),
) -> _TemplateResponse:
    return templates.TemplateResponse(
        request,
        "landing_full.html",
        {
            "hide_menu_upload": True,
            "supported_job_types": job_types,
            "version": version,
        },
    )


@web_api.post("/", response_model=None)
async def landing_post(
    request: Request,
    doc_src: UploadFile,
    file_identifier: FileIdentifier = Depends(get_file_identifier),
    job_types: List[JobType] = Depends(get_job_types),
    repo: Repository = Depends(get_repo),
    queue: JobQueue = Depends(get_queue),
    version: str = Depends(get_version),
) -> Union[_TemplateResponse, RedirectResponse]:
    try:
        jid, _ = await create_job(
            await doc_src.read(),
            doc_src.filename or "",
            repo,
            queue,
            file_identifier,
            job_types,
        )
        if "hx-request" in request.headers:
            return templates.TemplateResponse(
                request,
                "job_details.html",
                {
                    "jid": jid,
                    "job_status": 0,
                    "trigger": None,
                    "htmx": True,
                },
                headers={"hx-push-url": f"/jobs/{jid}"},
            )
        else:
            return RedirectResponse(f"/jobs/{jid}", status_code=status.HTTP_302_FOUND)
    except ValueError:
        raise ValidationException(
            params={
                "doc_src_invalid": True,
                "doc_src_feedback": "You uploaded an unsupported document type.",
                "hide_menu_upload": True,
                "supported_job_types": job_types,
                "version": version,
            },
            template_full="landing_full.html",
            template_htmx="landing.html",
        )


@web_api.get("/jobs/{jid}", response_class=HTMLResponse, response_model=None)
async def jobs_get(
    request: Request,
    jid: str,
    repo: Repository = Depends(get_repo),
    version: str = Depends(get_version),
) -> _TemplateResponse:
    try:
        (
            job_status,
            job_type,
            job_log,
            job_meta_src,
            job_meta_result,
            job_sid,
        ) = await get_job(jid, repo)
    except ValueError:
        raise WebException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request,
        (
            "job_details.html"
            if "hx-request" in request.headers
            else "job_details_full.html"
        ),
        {
            "jid": jid,
            "job_status": job_status,
            "job_log": job_log,
            "job_sid": job_sid,
            "meta_src": None if job_meta_src is None else asdict(job_meta_src),
            "meta_result": None if job_meta_result is None else asdict(job_meta_result),
            "htmx": "hx-request" in request.headers,
            "trigger": request.headers.get("hx-trigger"),
            "version": version,
        },
    )


@web_api.get(
    "/jobs/{jid}/result", response_class=OctetStreamResponse, response_model=None
)
async def jobs_get_result(jid: str, repo: Repository = Depends(get_repo)) -> Response:
    try:
        job_result, document_name = await get_job_result(jid, repo)
    except ValueError:
        raise WebException(status_code=status.HTTP_404_NOT_FOUND)
    quoted_document_name = quote(document_name)
    if quoted_document_name != document_name:
        # If quoting was necessary, signal UTF8 encoding (RFC 8187)
        file_name = f"filename*=utf-8''{quoted_document_name}"
    else:
        file_name = f'filename="{document_name}"'
    response_headers = {"Content-Disposition": f"attachment; {file_name}"}
    return Response(
        content=job_result,
        media_type="application/octet-stream",
        headers=response_headers,
    )


@web_api.get("/jobs/{jid}/delete", response_class=HTMLResponse, response_model=None)
async def jobs_delete(
    request: Request,
    jid: str,
    repo: Repository = Depends(get_repo),
    version: str = Depends(get_version),
) -> Response:
    try:
        await delete_job(jid, repo)
    except ValueError:
        raise WebException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request,
        (
            "job_deleted.html"
            if "hx-request" in request.headers
            else "job_deleted_full.html"
        ),
        {"jid": jid, "version": version},
    )


@web_api.get("/sessions/{sid}", response_class=HTMLResponse, response_model=None)
async def sessions_get(
    request: Request,
    sid: str,
    job_types: List[JobType] = Depends(get_job_types),
    jobs: bool = True,
    repo: Repository = Depends(get_repo),
    version: str = Depends(get_version),
) -> _TemplateResponse:
    try:
        created, updated, jobs_total, jobs_finished, job_list = await get_session(
            sid, repo
        )
    except ValueError:
        raise WebException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        request,
        (
            "session_details.html"
            if "hx-request" in request.headers
            else "session_details_full.html"
        ),
        {
            "sid": sid,
            "created": created,
            "jobs_total": jobs_total,
            "jobs_finished": jobs_finished,
            "jobs": job_list if jobs else None,
            "supported_job_types": job_types,
            "version": version,
        },
    )


@web_api.get("/api/usage", response_class=HTMLResponse, response_model=None)
async def doc_api_usage(
    request: Request,
    base_url: str = Depends(get_base_url),
    contact: Optional[str] = Depends(get_contact),
    version: str = Depends(get_version),
) -> _TemplateResponse:
    return templates.TemplateResponse(
        request,
        "doc/api.html",
        {
            "base_url": base_url,
            "contact": contact,
            "version": version,
        },
    )
