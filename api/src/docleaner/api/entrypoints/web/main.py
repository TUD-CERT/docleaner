from contextlib import asynccontextmanager
from importlib.metadata import version
import os
from typing import AsyncIterator

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_dependencies()
    yield
    await get_queue().shutdown()


app = FastAPI(
    version=version("docleaner-api"), title="docleaner API", lifespan=lifespan
)
app.mount(
    "/static", StaticFiles(directory=os.path.join(base_path, "static")), name="static"
)
app.include_router(rest.rest_api)
app.include_router(web.web_api)


@app.exception_handler(web.ValidationException)
async def validation_exception_handler(
    request: Request, exc: web.ValidationException
) -> Response:
    exc.params["request"] = request
    return templates.TemplateResponse(
        exc.template_htmx if "hx-request" in request.headers else exc.template_full,
        exc.params,
        status_code=exc.status_code,
    )


@app.exception_handler(web.WebException)
async def web_exception_handler(request: Request, exc: web.WebException) -> Response:
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "msg": exc.detail,
                "version": version("docleaner-api"),
            },
            status_code=exc.status_code,
        )
    else:
        return await http_exception_handler(request, exc)


@app.exception_handler(rest.RESTException)
async def rest_exception_handler(request: Request, exc: rest.RESTException) -> Response:
    return JSONResponse(content={"msg": exc.detail}, status_code=exc.status_code)
