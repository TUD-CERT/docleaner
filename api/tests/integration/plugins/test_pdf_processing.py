import magic
from typing import Tuple

from docleaner.api.core.sandbox import Sandbox


async def test_process_valid_pdf(cont_pdf_sandbox: Sandbox, sample_pdf: bytes) -> None:
    """Processing a valid PDF sample in a containerized sandbox."""
    result = await cont_pdf_sandbox.process(sample_pdf)
    assert result.success
    assert magic.from_buffer(result.result, mime=True) == "application/pdf"
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
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


async def test_retrieve_signature_status(
    cont_pdf_sandbox: Sandbox, sample_pdf: bytes, sample_pdf_signed: bytes
) -> None:
    """The metadata analysis includes a signed marker that indicates
    whether a document has a digital signature."""
    result = await cont_pdf_sandbox.process(sample_pdf_signed)
    assert result.metadata_src["signed"] is result.metadata_result["signed"] is True
    result = await cont_pdf_sandbox.process(sample_pdf)
    assert result.metadata_src["signed"] is result.metadata_result["signed"] is False


async def test_preserve_pdfua1_indicator(cont_pdf_sandbox: Sandbox, sample_pdfua1: bytes) -> None:
    """Preserving the PDF/UA-1 indicator in accordance with ISO 14289-1."""
    result = await cont_pdf_sandbox.process(sample_pdfua1)
    assert result.success
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
    assert (
        result.metadata_src["primary"]["XMP:XMP-pdfuaid:Part"]
        == result.metadata_result["primary"]["XMP:XMP-pdfuaid:Part"]
        == 1
    )


async def test_preserve_pdfe1_indicator(cont_pdf_sandbox: Sandbox, sample_pdfe1: bytes) -> None:
    """Preserving the PDF/E-1 indicator in accordance with ISO 24517-1:2008-05."""
    result = await cont_pdf_sandbox.process(sample_pdfe1)
    assert result.success
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
    assert (
        result.metadata_src["primary"]["XMP:XMP-pdfe:ISO_PDFEVersion"]
        == "PDF/E-1"
        == result.metadata_result["primary"]["XMP:XMP-pdfe:ISO_PDFEVersion"]
        == "PDF/E-1"
    )


async def test_preserve_pdfa_indicators(
    cont_pdf_sandbox: Sandbox, samples_pdfa: Tuple[bytes, bytes, bytes, bytes]
) -> None:
    """Preserving the PDF/A-{1,2,3} indicators and schemas in accordance with ISO 19005."""
    for sample, part, conformance in [
        (samples_pdfa[0], 1, "A"),
        (samples_pdfa[1], 2, "B"),
        (samples_pdfa[2], 3, "U"),
    ]:
        result = await cont_pdf_sandbox.process(sample)
        assert result.success
        assert isinstance(result.metadata_src["primary"], dict)
        assert isinstance(result.metadata_result["primary"], dict)
        assert (
            result.metadata_src["primary"]["XMP:XMP-pdfaid:Part"]
            == result.metadata_result["primary"]["XMP:XMP-pdfaid:Part"]
            == part
        )
        assert (
            result.metadata_src["primary"]["XMP:XMP-pdfaid:Conformance"]
            == result.metadata_result["primary"]["XMP:XMP-pdfaid:Conformance"]
            == conformance
        )
        assert (
            result.metadata_src["primary"]["XMP:XMP-pdfaExtension:SchemasPrefix"]
            == result.metadata_result["primary"]["XMP:XMP-pdfaExtension:SchemasPrefix"]
            == ["pdfx", "pdfuaid", "prism"]
        )
        assert (
            result.metadata_src["primary"]["XMP:XMP-pdfaExtension:SchemasPropertyName"]
            == result.metadata_result["primary"][
                "XMP:XMP-pdfaExtension:SchemasPropertyName"
            ]
            == ["AuthoritativeDomain", "part", "aggregationType", "url"]
        )
        result = await cont_pdf_sandbox.process(samples_pdfa[3])
        assert isinstance(result.metadata_src["primary"], dict)
        assert isinstance(result.metadata_result["primary"], dict)
        assert (
            result.metadata_src["primary"]["XMP:XMP-pdfaExtension:SchemasValueTypeType"]
            == result.metadata_result["primary"][
                "XMP:XMP-pdfaExtension:SchemasValueTypeType"
            ]
            == "ContactInfo"
        )


async def test_preserve_pdfx_indicators(cont_pdf_sandbox: Sandbox, samples_pdfx: Tuple[bytes, bytes]) -> None:
    """Preserving the PDF/X indicators in accordance with ISO 15930."""
    x1 = samples_pdfx[0]
    result = await cont_pdf_sandbox.process(x1)
    assert result.success
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
    assert (
        result.metadata_src["primary"]["PDF:GTS_PDFXVersion"]
        == result.metadata_result["primary"]["PDF:GTS_PDFXVersion"]
        == "PDF/X-1a:2003"
    )
    assert (
        result.metadata_src["primary"]["PDF:GTS_PDFXConformance"]
        == result.metadata_result["primary"]["PDF:GTS_PDFXConformance"]
        == "PDF/X-1a:2003"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-pdfx:GTS_PDFXVersion"]
        == result.metadata_result["primary"]["XMP:XMP-pdfx:GTS_PDFXVersion"]
        == "PDF/X-1a:2003"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-pdfx:GTS_PDFXConformance"]
        == result.metadata_result["primary"]["XMP:XMP-pdfx:GTS_PDFXConformance"]
        == "PDF/X-1a:2003"
    )
    x4 = samples_pdfx[1]
    result = await cont_pdf_sandbox.process(x4)
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
    assert (
        result.metadata_src["primary"]["XMP:XMP-pdfxid:GTS_PDFXVersion"]
        == result.metadata_result["primary"]["XMP:XMP-pdfxid:GTS_PDFXVersion"]
        == "PDF/X-4"
    )


async def test_preserve_pdfvt_indicators(cont_pdf_sandbox: Sandbox, sample_pdfvt: bytes) -> None:
    """Preserving the PDF/VT indicators."""
    result = await cont_pdf_sandbox.process(sample_pdfvt)
    assert result.success
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
    assert (
        result.metadata_src["primary"]["PDF:GTS_PDFVTVersion"]
        == result.metadata_result["primary"]["PDF:GTS_PDFVTVersion"]
        == "PDF/VT-1"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-pdfvtid:GTS_PDFVTVersion"]
        == result.metadata_result["primary"]["XMP:XMP-pdfvtid:GTS_PDFVTVersion"]
        == "PDF/VT-1"
    )


async def test_preserve_legal_tags(cont_pdf_sandbox: Sandbox, sample_pdf_tagged: bytes) -> None:
    """Preserving tags related to legal/copyright matters."""
    result = await cont_pdf_sandbox.process(sample_pdf_tagged)
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
    assert (
        result.metadata_src["primary"]["XMP:XMP-dc:Rights-en"]
        == result.metadata_result["primary"]["XMP:XMP-dc:Rights-en"]
        == "Copyright (C) 1905, Albert Einstein"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-xmpRights:Marked"]
        is result.metadata_result["primary"]["XMP:XMP-xmpRights:Marked"]
        is True
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-xmpRights:WebStatement"]
        == result.metadata_result["primary"]["XMP:XMP-xmpRights:WebStatement"]
        == "http://creativecommons.org/licenses/by-nc-nd/3.0/"
    )


async def test_preserve_misc_benign_tags(cont_pdf_sandbox: Sandbox, sample_pdf_tagged: bytes) -> None:
    """Preserving various unproblematic tags (non-exhaustive)."""
    result = await cont_pdf_sandbox.process(sample_pdf_tagged)
    assert isinstance(result.metadata_src["primary"], dict)
    assert isinstance(result.metadata_result["primary"], dict)
    assert (
        result.metadata_src["primary"]["XMP:XMP-pdf:PDFVersion"]
        == result.metadata_result["primary"]["XMP:XMP-pdf:PDFVersion"]
        == 1.5
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-dc:Format"]
        == result.metadata_result["primary"]["XMP:XMP-dc:Format"]
        == "application/pdf"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-dc:Language"]
        == result.metadata_result["primary"]["XMP:XMP-dc:Language"]
        == "en"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-dc:Type"]
        == result.metadata_result["primary"]["XMP:XMP-dc:Type"]
        == "Text"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-dc:Title-en"]
        == result.metadata_result["primary"]["XMP:XMP-dc:Title-en"]
        == "On a heuristic viewpoint concerning the production and transformation of light"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-dc:Title-de"]
        == result.metadata_result["primary"]["XMP:XMP-dc:Title-de"]
        == "Über einen die Erzeugung und Verwandlung des Lichtes betreffenden heuristischen Gesichtspunkt"
    )
    assert (
        result.metadata_src["primary"]["XMP:XMP-dc:Description-en"]
        == result.metadata_result["primary"]["XMP:XMP-dc:Description-en"]
        == "photoelectric effect"
    )
    assert (
        result.metadata_src["primary"]["PDF:Trapped"]
        is result.metadata_result["primary"]["PDF:Trapped"]
        is False
    )
    assert result.metadata_result["primary"]["XMP:XMP-pdf:Trapped"] is False


async def test_exclude_xmptoolkit_tag(cont_pdf_sandbox: Sandbox, sample_pdfua1: bytes) -> None:
    """The XMP-x:XMPToolkit should neither be preserved nor added by the cleaning process."""
    result = await cont_pdf_sandbox.process(sample_pdfua1)
    assert isinstance(result.metadata_result["primary"], dict)
    assert "XMP:XMP-x:XMPToolkit" not in result.metadata_result["primary"]
