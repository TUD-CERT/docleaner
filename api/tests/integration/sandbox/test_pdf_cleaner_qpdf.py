from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox


async def test_preserve_pdfua1_indicator(sample_pdfua1: bytes) -> None:
    """Preserving the PDF/UA-1 indicator in accordance with ISO 14289-1."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner_qpdf",
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(sample_pdfua1)
    assert result.success
    assert result.metadata_src["primary"]["XMP:XMP-pdfuaid:Part"] == 1
    assert result.metadata_result["primary"]["XMP:XMP-pdfuaid:Part"] == 1


async def test_preserve_pdfe1_indicator(sample_pdfe1: bytes) -> None:
    """Preserving the PDF/E-1 indicator in accordance with ISO 24517-1:2008-05."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner_qpdf",
        podman_uri="unix:///run/podman.sock",
    )
    result = await sandbox.process(sample_pdfe1)
    assert result.success
    assert result.metadata_src["primary"]["XMP:XMP-pdfe:ISO_PDFEVersion"] == "PDF/E-1"
    assert (
        result.metadata_result["primary"]["XMP:XMP-pdfe:ISO_PDFEVersion"] == "PDF/E-1"
    )
