from typing import Any, Dict

from docleaner.api.core.metadata import DocumentMetadata, MetadataField


def process_pdf_metadata(src: Dict[str, Dict[str, Any]]) -> DocumentMetadata:
    """PDF exiftool-generated metadata post-processing. Strips out various tags of
    embedded documents that aren't likely to contain privacy-sensitive metadata."""
    primary_metadata = {}
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
        primary_metadata[field] = MetadataField(
            id=field, name=field_name, group=field_group, value=value
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
                )
        # Only attach embeddings that contain actual metadata
        if len([tag for tag in embed_data.keys() if not tag.startswith("_")]) > 0:
            embeds[str(len(embeds))] = embed_data
    return DocumentMetadata(primary=primary_metadata, embeds=embeds)
