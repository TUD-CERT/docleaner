import magic

from docleaner.api.core.job import JobParams
from docleaner.api.core.sandbox import Sandbox


async def test_process_valid_document(
    cont_pdf_sandbox: Sandbox, sample_pdf: bytes
) -> None:
    """Processing a valid document in a containerized sandbox."""
    result = await cont_pdf_sandbox.process(sample_pdf, JobParams())
    assert result.success
    assert isinstance(result.result, bytes)
    assert magic.from_buffer(result.result, mime=True) == "application/pdf"
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)


async def test_process_invalid_document(cont_pdf_sandbox: Sandbox) -> None:
    """Attempting to process an invalid document in a containerized sandbox."""
    result = await cont_pdf_sandbox.process(b"INVALID_PDF", JobParams())
    assert not result.success
    assert result.result == b""
    assert len(result.log) > 0


async def test_nonexisting_container_image(
    cont_pdf_sandbox: Sandbox, sample_pdf: bytes
) -> None:
    """Initializing a sandbox with a nonexisting container image returns unsuccessful jobs."""
    container_image = "localhost/nonexisting/image"
    cont_pdf_sandbox._image = container_image  # type: ignore
    result = await cont_pdf_sandbox.process(sample_pdf, JobParams())
    assert not result.success
    assert result.result == b""
    assert result.log == [f"Invalid container image {container_image}"]
