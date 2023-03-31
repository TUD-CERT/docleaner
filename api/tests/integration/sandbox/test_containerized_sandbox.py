import magic

from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox


async def test_process_valid_document(sample_pdf: bytes) -> None:
    """Processing a valid document in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(sample_pdf)
    assert result.success
    assert isinstance(result.result, bytes)
    assert magic.from_buffer(result.result, mime=True) == "application/pdf"
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)


async def test_process_invalid_document() -> None:
    """Attempting to process an invalid document in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(b"INVALID_PDF")
    assert not result.success
    assert result.result == b""
    assert len(result.log) > 0


async def test_nonexisting_container_image(sample_pdf: bytes) -> None:
    """Initializing a sandbox with a nonexisting container image returns unsuccessful jobs."""
    container_image = "localhost/nonexisting/image"
    sandbox = ContainerizedSandbox(
        container_image=container_image,
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(sample_pdf)
    assert not result.success
    assert result.result == b""
    assert result.log == [f"Invalid container image {container_image}"]
