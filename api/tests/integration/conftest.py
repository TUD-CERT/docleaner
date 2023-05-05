import asyncio
from configparser import ConfigParser
import os
from typing import AsyncGenerator, List

from motor import motor_asyncio
import pytest
import uvicorn

from docleaner.api.adapters.repository.mongodb_repository import MongoDBRepository
from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.core.job import JobType
from docleaner.api.core.sandbox import Sandbox
from docleaner.api.services.clock import Clock
from docleaner.api.services.repository import Repository


@pytest.fixture
def app_config() -> ConfigParser:
    config = ConfigParser()
    config.read(os.environ["DOCLEANER_CONF"])
    return config


@pytest.fixture
async def repo(
    clock: Clock, job_types: List[JobType]
) -> AsyncGenerator[Repository, None]:
    # Delete existing database (if it exists)
    db_host = "database"
    db_port = 27017
    db_name = "docleaner"
    mongo = motor_asyncio.AsyncIOMotorClient(db_host, db_port)
    if db_name in await mongo.list_database_names():
        await mongo.drop_database(db_name)
    mongo.close()
    repo = MongoDBRepository(clock, job_types, db_host, db_port, db_name)
    yield repo
    await repo.disconnect()


@pytest.fixture
def sandbox(app_config: ConfigParser) -> Sandbox:
    return ContainerizedSandbox(
        container_image=app_config.get("plugins.pdf", "containerized.image"),
        podman_uri=app_config.get("docleaner", "podman_uri"),
    )


@pytest.fixture
def cont_pdf_sandbox(sandbox: Sandbox) -> Sandbox:
    return sandbox


@pytest.fixture
async def web_app(unused_tcp_port: int) -> AsyncGenerator[str, None]:
    """Launches a temporary instance of the web entrypoint,
    taken from the uvicorn test suite. Returns the server's base URL."""
    base_url = f"http://127.0.0.1:{unused_tcp_port}"
    os.environ["DOCLEANER_URL"] = base_url
    cfg = uvicorn.Config("docleaner.api.entrypoints.web.main:app", port=unused_tcp_port)
    server = uvicorn.Server(cfg)
    task = asyncio.ensure_future(server.serve())
    await asyncio.sleep(0.1)
    try:
        yield base_url
    finally:
        await server.shutdown()
        task.cancel()
