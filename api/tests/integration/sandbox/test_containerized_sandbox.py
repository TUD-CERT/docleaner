from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox


async def test_process_valid_pdf(sample_pdf: bytes) -> None:
    """Processing a valid PDF sample in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )
    log, success, result = await sandbox.process(sample_pdf)
    assert success
    assert isinstance(result, bytes)
    assert len(result) > 0


async def test_process_invalid_pdf() -> None:
    """Attempting to process an invalid PDF sample in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )
    log, success, result = await sandbox.process(b"INVALID_PDF")
    assert not success
    assert result == b""
    assert len(log) > 0
