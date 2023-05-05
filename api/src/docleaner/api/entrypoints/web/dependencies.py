from configparser import ConfigParser
from importlib.metadata import version
import logging
import os
from typing import List, Optional

from fastapi.templating import Jinja2Templates

from docleaner.api.bootstrap import bootstrap
from docleaner.api.core.job import JobType
from docleaner.api.core.metadata import MetadataTag
from docleaner.api.services.clock import Clock
from docleaner.api.services.file_identifier import FileIdentifier
from docleaner.api.services.job_queue import JobQueue
from docleaner.api.services.repository import Repository

logger = logging.getLogger(__name__)


_base_url: str
_config: ConfigParser
_clock: Clock
_file_identifier: FileIdentifier
_job_types: List[JobType]
_queue: JobQueue
_repo: Repository
_version: str

base_path = os.path.dirname(os.path.realpath(__file__))
templates = Jinja2Templates(directory=os.path.join(base_path, "templates"))
templates.env.globals["MetadataTag"] = MetadataTag


def init() -> None:
    global _clock, _config, _file_identifier, _job_types, _queue, _repo, _base_url, _version
    if "DOCLEANER_CONF" not in os.environ:
        raise ValueError("Environment variable DOCLEANER_CONF is not set!")
    logger.info("Reading configuration from %s", os.environ["DOCLEANER_CONF"])
    _config = ConfigParser()
    _config.read(os.environ["DOCLEANER_CONF"])
    if "DOCLEANER_URL" not in os.environ:
        raise ValueError("Environment variable DOCLEANER_URL is not set!")
    _base_url = os.environ["DOCLEANER_URL"]
    _version = version("docleaner-api")
    optional_params = {}
    if "DOCLEANER_LOGLVL" in os.environ:
        optional_params["log_level"] = os.environ["DOCLEANER_LOGLVL"]
    _clock, _file_identifier, _job_types, _queue, _repo = bootstrap(
        _config, **optional_params  # type: ignore
    )


def get_clock() -> Clock:
    global _clock
    return _clock


def get_file_identifier() -> FileIdentifier:
    global _file_identifier
    return _file_identifier


def get_job_types() -> List[JobType]:
    global _job_types
    return _job_types


def get_queue() -> JobQueue:
    global _queue
    return _queue


def get_repo() -> Repository:
    global _repo
    return _repo


def get_base_url() -> str:
    global _base_url
    return _base_url


def get_contact() -> Optional[str]:
    global _config
    contact = _config.get("docleaner", "contact", fallback="")
    if len(contact) == 0:
        return None
    return contact


def get_version() -> str:
    global _version
    return _version
