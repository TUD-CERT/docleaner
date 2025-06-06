from typing import Any, Dict, List, Union

from docleaner.api.core.metadata import DocumentMetadata, MetadataField, MetadataTag


PDF_TAGS = {
    "XMP:XMP-pdfuaid:Part": [MetadataTag.ACCESSIBILITY],
    "XMP:XMP-pdfe:ISO_PDFEVersion": [MetadataTag.COMPLIANCE],
    "XMP:XMP-pdfaid:Part": [MetadataTag.COMPLIANCE],
    "XMP:XMP-pdfaid:Conformance": [MetadataTag.COMPLIANCE],
    "PDF:GTS_PDFXVersion": [MetadataTag.COMPLIANCE],
    "PDF:GTS_PDFXConformance": [MetadataTag.COMPLIANCE],
    "XMP:XMP-pdfx:GTS_PDFXVersion": [MetadataTag.COMPLIANCE],
    "XMP:XMP-pdfx:GTS_PDFXConformance": [MetadataTag.COMPLIANCE],
    "XMP:XMP-pdfxid:GTS_PDFXVersion": [MetadataTag.COMPLIANCE],
    "XMP:XMP-pdfaExtension": [MetadataTag.COMPLIANCE],
    "PDF:GTS_PDFVTVersion": [MetadataTag.COMPLIANCE],
    "XMP:XMP-pdfvtid:GTS_PDFVTVersion": [MetadataTag.COMPLIANCE],
    "XMP:XMP-dc:Rights": [MetadataTag.LEGAL],
    "XMP:XMP-xmpRights": [MetadataTag.LEGAL],
}


def _identify_tags(field: str) -> List[MetadataTag]:
    """Returns the matching tags for the given field id. Takes language such as
    the "-en" in "XMP:XMP-dc:Rights-en" into account by treating the PDF_TAGS
    keys as prefixes."""
    for prefix, tags in PDF_TAGS.items():
        if field.startswith(prefix):
            return tags
    return []


def process_pdf_metadata(
    src: Dict[str, Union[bool, Dict[str, Any]]],
) -> DocumentMetadata:
    """PDF exiftool-generated metadata post-processing. Strips out various tags of
    embedded documents that aren't likely to contain privacy-invasive metadata."""
    primary_metadata = {}
    assert isinstance(src["primary"], dict)
    assert isinstance(src["embeds"], dict)
    assert isinstance(src["signed"], bool)
    embeds: Dict[str, Dict[str, MetadataField]] = {}
    for field, value in src["primary"].items():
        if ":" in field:
            field_group, field_name = field.split(":", 1)
        else:
            field_group = "File"
            field_name = field
            field = f"File:{field}"
        if field_group in ["ICC_Profile", "Composite"]:
            continue
        # Aggregate all XMP-pdfaExtension:Schemas* into a single tag listing all embedded schemas
        if field == "XMP:XMP-pdfaExtension:SchemasSchema":
            field = "XMP:XMP-pdfaExtension:Schemas"
            field_name = "XMP-pdfaExtension:Schemas"
        elif field.startswith("XMP:XMP-pdfaExtension:Schemas"):
            continue
        primary_metadata[field] = MetadataField(
            id=field,
            name=field_name,
            group=field_group,
            value=value,
            tags=_identify_tags(field),
        )
    for embed_name, embed_meta in src["embeds"].items():
        embed_data = {}
        # Replace "use -b option to extract" warning about binary data (2 levels deep)
        for embed_tag, embed_val in embed_meta.copy().items():
            if isinstance(embed_val, str) and "option to extract" in embed_val:
                embed_meta[embed_tag] = "<binary data>"
            elif isinstance(embed_val, dict):
                for e_embed_tag, e_embed_val in embed_val.copy().items():
                    if (
                        isinstance(e_embed_val, str)
                        and "option to extract" in e_embed_val
                    ):
                        embed_meta[embed_tag][e_embed_tag] = "<binary data>"
        # Type identification
        if "File:MIMEType" in embed_meta:
            embed_data["_type"] = MetadataField(
                id="_type", name="type", value=embed_meta["File:MIMEType"]
            )
        elif (
            "File:FileType" in embed_meta
            and "unsupported" not in embed_meta["File:FileType"]
        ):
            embed_data["_type"] = MetadataField(
                id="_type", name="type", value=embed_meta["File:FileType"]
            )
        # Embedded document metadata
        for embed_meta_field, embed_meta_val in embed_meta.items():
            field_group, field_name = embed_meta_field.split(":", 1)
            if field_group not in ["File", "PDF", "APP14", "ICC_Profile"]:
                embed_data[embed_meta_field] = MetadataField(
                    id=embed_meta_field,
                    name=field_name,
                    value=embed_meta_val,
                    group=field_group,
                    tags=_identify_tags(embed_meta_field),
                )
        # Only attach embeddings that contain actual metadata
        if len([tag for tag in embed_data.keys() if not tag.startswith("_")]) > 0:
            embeds[str(len(embeds))] = embed_data
    return DocumentMetadata(
        primary=primary_metadata, embeds=embeds, signed=src["signed"]
    )
