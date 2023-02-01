from dataclasses import dataclass
from typing import Any, Dict, List, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
import starlette.status as status
from starlette.templating import _TemplateResponse

from docleaner.api.entrypoints.web.dependencies import (
    get_base_url,
    get_file_identifier,
    get_job_types,
    get_queue,
    get_repo,
    get_version,
    templates,
)
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
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
    request: Request, version: str = Depends(get_version)
) -> _TemplateResponse:
    return templates.TemplateResponse(
        "landing_full.html", {"request": request, "version": version}
    )


@web_api.post("/", response_model=None)
async def landing_post(
    request: Request,
    doc_src: UploadFile,
    file_identifier: FileIdentifier = Depends(get_file_identifier),
    job_types: List[SupportedJobType] = Depends(get_job_types),
    repo: Repository = Depends(get_repo),
    queue: JobQueue = Depends(get_queue),
) -> Union[_TemplateResponse, RedirectResponse]:
    try:
        jid, _ = await create_job(
            await doc_src.read(),
            doc_src.filename,
            repo,
            queue,
            file_identifier,
            job_types,
        )
        if "hx-request" in request.headers:
            return templates.TemplateResponse(
                "job_details.html",
                {
                    "request": request,
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
        "job_details.html"
        if "hx-request" in request.headers
        else "job_details_full.html",
        {
            "request": request,
            "jid": jid,
            "job_status": job_status,
            "job_log": job_log,
            "job_sid": job_sid,
            "meta_src": job_meta_src,
            "meta_result": job_meta_result,
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
    response_headers = {
        "Content-Disposition": f'attachment; filename="{document_name}"'
    }
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
        "job_deleted.html"
        if "hx-request" in request.headers
        else "job_deleted_full.html",
        {"request": request, "jid": jid, "version": version},
    )


@web_api.get("/sessions/{sid}", response_class=HTMLResponse, response_model=None)
async def sessions_get(
    request: Request,
    sid: str,
    repo: Repository = Depends(get_repo),
    version: str = Depends(get_version),
) -> _TemplateResponse:
    try:
        created, updated, jobs_total, jobs_finished, jobs = await get_session(sid, repo)
    except ValueError:
        raise WebException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        "session_details.html"
        if "hx-request" in request.headers
        else "session_details_full.html",
        {
            "request": request,
            "sid": sid,
            "created": created,
            "jobs_total": jobs_total,
            "jobs_finished": jobs_finished,
            "jobs": jobs,
            "version": version,
        },
    )


@web_api.get("/api/usage", response_class=HTMLResponse, response_model=None)
async def doc_api_usage(
    request: Request,
    base_url: str = Depends(get_base_url),
    version: str = Depends(get_version),
) -> _TemplateResponse:
    return templates.TemplateResponse(
        "doc/api.html", {"request": request, "base_url": base_url, "version": version}
    )
