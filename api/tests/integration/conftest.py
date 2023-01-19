import asyncio
import os
from typing import AsyncGenerator

from motor import motor_asyncio
import pytest
import uvicorn

from docleaner.api.adapters.repository.mongodb_repository import MongoDBRepository
from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.services.clock import Clock
from docleaner.api.services.repository import Repository
from docleaner.api.services.sandbox import Sandbox


@pytest.fixture
async def repo(clock: Clock) -> AsyncGenerator[Repository, None]:
    # Delete existing database (if it exists)
    db_host = "database"
    db_port = 27017
    db_name = "docleaner"
    mongo = motor_asyncio.AsyncIOMotorClient(db_host, db_port)
    if db_name in await mongo.list_database_names():
        await mongo.drop_database(db_name)
    mongo.close()
    repo = MongoDBRepository(clock, db_host, db_port, db_name)
    yield repo
    await repo.disconnect()


@pytest.fixture
def sandbox() -> Sandbox:
    return ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )


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
