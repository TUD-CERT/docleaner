import os
from typing import Optional

from fastapi import FastAPI, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
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


class JobRequest(BaseModel):
    pass


@app.on_event("startup")
def on_startup() -> None:
    global adapters
    adapters = bootstrap()


@app.get("/", response_class=HTMLResponse)
def landing_get(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("landing.html", {"request": request})


@app.post("/")
async def landing_post(doc_src: bytes = File()) -> RedirectResponse:
    assert isinstance(adapters, Adapters)
    jid, _ = await create_job(
        doc_src, adapters.repo, adapters.queue, adapters.file_identifier, adapters.clock
    )
    return RedirectResponse(f"/jobs/{jid}", status_code=status.HTTP_302_FOUND)


@app.get("/jobs/{jid}", response_class=HTMLResponse)
async def jobs_get(request: Request, jid: str) -> _TemplateResponse:
    assert isinstance(adapters, Adapters)
    job_status, job_type, job_log, job_meta_src, job_meta_result = await get_job(
        jid, adapters.repo
    )
    return templates.TemplateResponse(
        "job_details.html",
        {
            "request": request,
            "jid": jid,
            "job_status": job_status,
            "meta_src": job_meta_src,
            "meta_result": job_meta_result,
        },
    )


@app.get("/jobs/{jid}/result", response_class=Response)
async def jobs_get_result(jid: str) -> Response:
    assert isinstance(adapters, Adapters)
    job_result = await get_job_result(jid, adapters.repo)
    response_headers = {"Content-Disposition": 'attachment; filename="out.pdf"'}
    return Response(
        content=job_result,
        media_type="application/octet-stream",
        headers=response_headers,
    )
