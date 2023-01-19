import os
from typing import List

from fastapi.templating import Jinja2Templates

from docleaner.api.bootstrap import bootstrap
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.job_types import SupportedJobType
from docleaner.api.services.repository import Repository


_base_url: str
_clock: Clock
_file_identifier: FileIdentifier
_job_types: List[SupportedJobType]
_queue: JobQueue
_repo: Repository

base_path = os.path.dirname(os.path.realpath(__file__))
templates = Jinja2Templates(directory=os.path.join(base_path, "templates"))


def init() -> None:
    global _clock, _file_identifier, _job_types, _queue, _repo, _base_url
    _clock, _file_identifier, _job_types, _queue, _repo = bootstrap()
    if "DOCLEANER_URL" not in os.environ:
        raise ValueError("Environment variable DOCLEANER_URL is not set!")
    _base_url = os.environ["DOCLEANER_URL"]


def get_clock() -> Clock:
    return _clock


def get_file_identifier() -> FileIdentifier:
    return _file_identifier


def get_job_types() -> List[SupportedJobType]:
    return _job_types


def get_queue() -> JobQueue:
    return _queue


def get_repo() -> Repository:
    return _repo


def get_base_url() -> str:
    return _base_url
