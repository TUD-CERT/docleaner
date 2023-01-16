import os
from typing import Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
import starlette.status as status
from starlette.templating import _TemplateResponse

from docleaner.api.bootstrap import Adapters, bootstrap
from docleaner.api.services.jobs import create_job, get_job, get_job_result


app = FastAPI()
base_path = os.path.dirname(os.path.realpath(__file__))
app.mount(
    "/static", StaticFiles(directory=os.path.join(base_path, "static")), name="static"
)
templates = Jinja2Templates(directory=os.path.join(base_path, "templates"))
adapters: Optional[Adapters] = None


@app.on_event("startup")
def on_startup() -> None:
    global adapters
    adapters = bootstrap()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global adapters
    assert adapters is not None
    await adapters.queue.shutdown()


@app.exception_handler(StarletteHTTPException)
async def template_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> Response:
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        return templates.TemplateResponse(
            "errors/400.html",
            {"request": request, "msg": exc.detail},
            status_code=exc.status_code,
        )
    else:
        return await http_exception_handler(request, exc)


@app.get("/", response_class=HTMLResponse, response_model=None)
def landing_get(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("landing.html", {"request": request})


@app.post("/", response_model=None)
async def landing_post(
    request: Request, doc_src: UploadFile
) -> Union[_TemplateResponse, RedirectResponse]:
    assert isinstance(adapters, Adapters)
    try:
        jid, _ = await create_job(
            await doc_src.read(),
            doc_src.filename,
            adapters.repo,
            adapters.queue,
            adapters.file_identifier,
            adapters.job_types,
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You uploaded an unsupported document type.",
        )


@app.get("/jobs/{jid}", response_class=HTMLResponse, response_model=None)
async def jobs_get(request: Request, jid: str) -> _TemplateResponse:
    assert isinstance(adapters, Adapters)
    try:
        job_status, job_type, job_log, job_meta_src, job_meta_result = await get_job(
            jid, adapters.repo
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
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


@app.get("/jobs/{jid}/result", response_class=Response, response_model=None)
async def jobs_get_result(jid: str) -> Response:
    assert isinstance(adapters, Adapters)
    try:
        job_result, document_name = await get_job_result(jid, adapters.repo)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    response_headers = {
        "Content-Disposition": f'attachment; filename="{document_name}"'
    }
    return Response(
        content=job_result,
        media_type="application/octet-stream",
        headers=response_headers,
    )
