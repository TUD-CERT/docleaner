from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox


async def test_process_valid_pdf(sample_pdf: bytes) -> None:
    """Processing a valid PDF sample in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(sample_pdf)
    assert result.success
    assert isinstance(result.result, bytes)
    assert len(result.result) > 0
    assert result.metadata_src["Subject"] == "testing"
    assert result.metadata_src["Author"] == "John Doe"
    assert (
        result.metadata_src["Producer"]
        == "PDF Studio 2018.4.0 Pro - https://www.qoppa.com"
    )
    assert result.metadata_src["Creator"] == "PDF Studio 2018 Pro"
    assert result.metadata_src["Title"] == "A sample PDF"
    assert result.metadata_src["Keywords"] == "anime, plane, generated"
    for key in ["Author", "Producer", "Creator"]:
        assert key not in result.metadata_result


async def test_process_invalid_pdf() -> None:
    """Attempting to process an invalid PDF sample in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner",
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(b"INVALID_PDF")
    assert not result.success
    assert result.result == b""
    assert len(result.log) > 0
