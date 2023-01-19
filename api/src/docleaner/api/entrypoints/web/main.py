import os

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import starlette.status as status

from docleaner.api.entrypoints.web.dependencies import (
    base_path,
    init as init_dependencies,
    get_queue,
    templates,
)
from docleaner.api.entrypoints.web.routers import rest, web


app = FastAPI()
app.mount(
    "/static", StaticFiles(directory=os.path.join(base_path, "static")), name="static"
)
app.include_router(rest.rest_api)
app.include_router(web.web_api)


@app.on_event("startup")
def on_startup() -> None:
    init_dependencies()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await get_queue().shutdown()


@app.exception_handler(web.WebException)
async def web_exception_handler(request: Request, exc: web.WebException) -> Response:
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        return templates.TemplateResponse(
            "errors/400.html",
            {"request": request, "msg": exc.detail},
            status_code=exc.status_code,
        )
    else:
        return await http_exception_handler(request, exc)


@app.exception_handler(rest.RESTException)
async def rest_exception_handler(request: Request, exc: rest.RESTException) -> Response:
    if exc.status_code == status.HTTP_400_BAD_REQUEST:
        return JSONResponse(content={"msg": exc.detail}, status_code=exc.status_code)
    else:
        return await http_exception_handler(request, exc)
