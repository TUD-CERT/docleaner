import magic

from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox


async def test_process_valid_pdf(sample_pdf: bytes) -> None:
    """Processing a valid PDF sample in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner_qpdf",
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(sample_pdf)
    assert result.success
    assert isinstance(result.result, bytes)
    assert magic.from_buffer(result.result, mime=True) == "application/pdf"
    assert result.metadata_src["primary"]["PDF:Subject"] == "testing"
    assert result.metadata_src["primary"]["PDF:Author"] == "John Doe"
    assert (
        result.metadata_src["primary"]["PDF:Producer"]
        == "PDF Studio 2018.4.0 Pro - https://www.qoppa.com"
    )
    assert result.metadata_src["primary"]["PDF:Creator"] == "PDF Studio 2018 Pro"
    assert result.metadata_src["primary"]["PDF:Title"] == "A sample PDF"
    assert result.metadata_src["primary"]["PDF:Keywords"] == [
        "anime",
        "plane",
        "generated",
    ]
    assert result.metadata_src["primary"]["XMP:XMP-dc:Title"] == "A sample PDF"
    for key in ["Author", "Producer", "Creator"]:
        assert key not in result.metadata_result["primary"]


async def test_process_invalid_pdf() -> None:
    """Attempting to process an invalid PDF sample in a containerized sandbox."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner_qpdf",
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
