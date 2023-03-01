from typing import Tuple

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


async def test_preserve_pdfa_indicators(
    samples_pdfa: Tuple[bytes, bytes, bytes]
) -> None:
    """Preserving the PDF/A-{1,2,3} indicators in accordance with ISO 19005."""
    sandbox = ContainerizedSandbox(
        container_image="localhost/docleaner/pdf_cleaner_qpdf",
        podman_uri="unix:///run/podman.sock",
    )
    for sample, part, conformance in [
        (samples_pdfa[0], 1, "A"),
        (samples_pdfa[1], 2, "B"),
        (samples_pdfa[2], 3, "U"),
    ]:
        result = await sandbox.process(sample)
        assert result.success
        assert result.metadata_src["primary"]["XMP:XMP-pdfaid:Part"] == part
        assert (
            result.metadata_result["primary"]["XMP:XMP-pdfaid:Conformance"]
            == conformance
        )
