import asyncio
from typing import AsyncGenerator

import pytest
import uvicorn

from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.services.sandbox import Sandbox


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
    cfg = uvicorn.Config("docleaner.api.entrypoints.web.main:app", port=unused_tcp_port)
    server = uvicorn.Server(cfg)
    task = asyncio.ensure_future(server.serve())
    await asyncio.sleep(0.1)
    try:
        yield f"http://127.0.0.1:{unused_tcp_port}"
    finally:
        await server.shutdown()
        task.cancel()
