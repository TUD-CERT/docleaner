from docleaner.api.services.file_identifier import FileIdentifier


async def test_identify_pdf(file_identifier: FileIdentifier, sample_pdf: bytes) -> None:
    """Identifies a PDF file via its MIME type."""
    assert file_identifier.identify(sample_pdf) == "application/pdf"


async def test_identify_no_bytes(file_identifier: FileIdentifier) -> None:
    """Identifies an empty byte string as application/x-empty."""
    assert file_identifier.identify(b"") == "application/x-empty"


async def test_identify_random_bytes(file_identifier: FileIdentifier) -> None:
    """Identifies some random bytes as application/octet-stream."""
    assert file_identifier.identify(b"\x01\x02\x03\x04") == "application/octet-stream"
