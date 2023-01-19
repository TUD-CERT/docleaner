from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
import starlette.status as status
from starlette.templating import _TemplateResponse

from docleaner.api.entrypoints.web.dependencies import (
    get_file_identifier,
    get_job_types,
    get_queue,
    get_repo,
    templates,
)
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.jobs import create_job, get_job, get_job_result
from docleaner.api.services.repository import Repository


web_api = APIRouter()


class WebException(HTTPException):
    pass


@web_api.get("/", response_class=HTMLResponse, response_model=None)
def landing_get(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("landing.html", {"request": request})


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
                "job_status.html",
                {"request": request, "jid": jid, "job_status": 0, "htmx": True},
                headers={"hx-push-url": f"/jobs/{jid}"},
            )
        else:
            return RedirectResponse(f"/jobs/{jid}", status_code=status.HTTP_302_FOUND)
    except ValueError:
        raise WebException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You uploaded an unsupported document type.",
        )


@web_api.get("/jobs/{jid}", response_class=HTMLResponse, response_model=None)
async def jobs_get(
    request: Request, jid: str, repo: Repository = Depends(get_repo)
) -> _TemplateResponse:
    try:
        job_status, job_type, job_log, job_meta_src, job_meta_result = await get_job(
            jid, repo
        )
    except ValueError:
        raise WebException(status_code=status.HTTP_404_NOT_FOUND)
    return templates.TemplateResponse(
        "job_status.html" if "hx-request" in request.headers else "job_details.html",
        {
            "request": request,
            "jid": jid,
            "job_status": job_status,
            "job_log": job_log,
            "meta_src": job_meta_src,
            "meta_result": job_meta_result,
            "htmx": "hx-request" in request.headers,
        },
    )


@web_api.get("/jobs/{jid}/result", response_class=Response, response_model=None)
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
