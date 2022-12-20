import pytest

from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.services.sandbox import Sandbox


@pytest.fixture
def sandbox() -> Sandbox:
    return ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )
