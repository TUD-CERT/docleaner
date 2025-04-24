from contextlib import asynccontextmanager
from importlib.metadata import version
import os
import secrets
from typing import Annotated, AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
import starlette.status as status

from docleaner.api.entrypoints.web.dependencies import (
    base_path,
    get_config,
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

security = HTTPBasic()


def verify_credentials(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    config = get_config()
    user_ok = secrets.compare_digest(credentials.username, config.get("docleaner", "auth_user"))
    pass_ok = secrets.compare_digest(credentials.password, config.get("docleaner", "auth_pass"))
    if not (user_ok and pass_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})


#app.include_router(rest.rest_api)
app.include_router(web.web_api, dependencies=[Depends(verify_credentials)])


@app.exception_handler(web.ValidationException)
async def validation_exception_handler(
    request: Request, exc: web.ValidationException
) -> Response:
    return templates.TemplateResponse(
        request,
        exc.template_htmx if "hx-request" in request.headers else exc.template_full,
        exc.params,
        status_code=exc.status_code,
    )


@app.exception_handler(web.WebException)
async def web_exception_handler(request: Request, exc: web.WebException) -> Response:
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        return templates.TemplateResponse(
            request,
            "error.html",
            {
                "msg": exc.detail,
                "version": version("docleaner-api"),
            },
            status_code=exc.status_code,
        )
    else:
        return await http_exception_handler(request, exc)


#@app.exception_handler(RequestValidationError)
async def web_validation_error_handler(request: Request, exc: RequestValidationError) -> Response:
    return templates.TemplateResponse(
        request,
        "landing.html",
        {
            "doc_src_invalid": True,
            "doc_src_feedback": "Invalid data submitted",
        },
        status_code=422,
    )


@app.exception_handler(rest.RESTException)
async def rest_exception_handler(request: Request, exc: rest.RESTException) -> Response:
    return JSONResponse(content={"msg": exc.detail}, status_code=exc.status_code)
