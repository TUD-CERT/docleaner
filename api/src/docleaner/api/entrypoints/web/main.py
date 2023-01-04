import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse


app = FastAPI()
base_path = os.path.dirname(os.path.realpath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(base_path, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(base_path, "templates"))


@app.get("/", response_class=HTMLResponse)
def get_landing(request: Request) -> _TemplateResponse:
    return templates.TemplateResponse("landing.html", {"request": request})
