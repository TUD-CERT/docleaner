from importlib.metadata import version
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


app = FastAPI(version=version("docleaner-api"), title="docleaner API")
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


@app.exception_handler(web.ValidationException)
async def validation_exception_handler(
    request: Request, exc: web.ValidationException
) -> Response:
    exc.params["request"] = request
    return templates.TemplateResponse(
        exc.template_htmx if "hx-request" in request.headers else exc.template_full,
        exc.params,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
