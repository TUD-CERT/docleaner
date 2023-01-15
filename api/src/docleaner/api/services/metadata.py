from typing import Any, Dict


def process_pdf_metadata(src: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """PDF metadata post-processing. Strips out various tags of embedded documents that
    aren't likely to contain privacy-sensitive metadata."""
    result: Dict[str, Dict[str, Any]] = {"doc": src["doc"], "embeds": {}}
    for embed_name, embed_meta in src["embeds"].items():
        if embed_name in ["ICC_Profile", "Composite"]:
            continue
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
        # Attach XMP metadata to the primary document
        if embed_name == "XMP":
            for xmp_tag, xmp_val in embed_meta.items():
                result["doc"][f"XMP:{xmp_tag}"] = xmp_val
            continue
        # Type identification
        if "File" in embed_meta:
            if "MIMEType" in embed_meta["File"]:
                embed_data["_type"] = embed_meta["File"]["MIMEType"]
            elif (
                "FileType" in embed_meta["File"]["FileType"]
                and not "unsupported" in embed_meta["File"]["FileType"]
            ):
                embed_data["_type"] = embed_meta["File"]["FileType"]
        # Embedded document metadata
        for embed_meta_type, embed_meta_val in embed_meta.items():
            if embed_meta_type not in ["File", "PDF", "APP14", "ICC_Profile"]:
                embed_data[embed_meta_type] = embed_meta_val
        # Only attach embeddings that contain actual metadata
        if len([tag for tag in embed_data.keys() if not tag.startswith("_")]) > 0:
            embed_name = str(len(result["embeds"].keys()))
            result["embeds"][embed_name] = embed_data
    return result
