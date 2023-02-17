from typing import Any, Dict

from docleaner.api.core.metadata import DocumentMetadata, MetadataField
from docleaner.api.services.metadata import process_pdf_metadata


def test_process_pdf() -> None:
    metadata: Dict[str, Dict[str, Any]] = {
        "primary": {
            "FileSize": "154 KiB",
            "Composite:ImageSize": "456x318",
            "Composite:Megapixels": 0.145,
            "ICC_Profile:ProfileVersion": "2.1.0",
            "ICC_Profile:ColorSpaceData": "RGB",
            "PDF:PDFVersion": "1.7",
            "PDF:Linearized": "No",
            "PDF:Subject": "testing",
            "PDF:CreateDate": "2022:12:06 11:29:06+01:00",
            "PDF:Author": "John Doe",
            "PDF:Producer": "PDF Tool",
            "PDF:Creator": "PDF Tool Pro",
            "PDF:Title": "A sample PDF",
            "PDF:ModifyDate": "2022:12:06 11:30:34+01:00",
            "PDF:Keywords": ["anime", "plane", "generated"],
            "PDF:PageCount": 1,
            "XMP:XMP-xmp:CreateDate": "2022:12:06 11:29:06+01:00",
            "XMP:XMP-xmp:ModifyDate": "2022:12:06 11:30:34+01:00",
            "XMP:XMP-xmp:CreatorTool": "PDF Tool Pro",
            "XMP:XMP-xmp:MetadataDate": "2022:12:06 11:30:34+01:00",
            "XMP:XMP-pdf:Producer": "PDF Tool Pro",
            "XMP:XMP-pdf:Keywords": "anime, plane, generated",
            "XMP:XMP-dc:Title": "A sample PDF",
            "XMP:XMP-dc:Creator": "John Doe",
            "XMP:XMP-dc:Description": "testing",
            "XMP:XMP-dc:Subject": ["anime", "plane", "generated"],
        },
        "embeds": {
            "Doc1": {
                "PDF:EmbeddedImageColorSpace": "ICCBased",
                "File:FileType": "JPEG",
                "File:FileTypeExtension": "jpg",
                "File:MIMEType": "image/jpeg",
                "File:ImageWidth": 456,
                "File:ImageHeight": 789,
                "APP14:DCTEncodeVersion": 100,
                "EXIF:XResolution": 72,
                "EXIF:YResolution": 72,
                "EXIF:ColorSpace": "sRGB",
                "XMP:XMP-x:XMPToolkit": "XMP toolkit 2.8.2-33, framework 1.5",
                "Photoshop:WriterName": "Adobe Photoshop",
                "Photoshop:PhotoshopFormat": "Standard",
                "JFIF:JFIFVersion": 1.01,
                "JFIF:ResolutionUnit": "inches",
                "JFIF:XResolution": 72,
                "JFIF:YResolution": 72,
            },
            "Doc2": {
                "PDF:EmbeddedImageColorSpace": "ICCBased",
                "PDF:EmbeddedImageFilter": "FlateDecode",
                "File:FileType": "(unsupported)",
            },
        },
    }
    result = process_pdf_metadata(metadata)
    assert result == DocumentMetadata(
        primary={
            # Data without a group (no ":" in the field name) is assigned to the "File" group
            "File:FileSize": MetadataField(
                id="File:FileSize", name="FileSize", group="File", value="154 KiB"
            ),
            "PDF:PDFVersion": MetadataField(
                id="PDF:PDFVersion", name="PDFVersion", group="PDF", value="1.7"
            ),
            "PDF:Linearized": MetadataField(
                id="PDF:Linearized", name="Linearized", group="PDF", value="No"
            ),
            "PDF:Subject": MetadataField(
                id="PDF:Subject", name="Subject", group="PDF", value="testing"
            ),
            "PDF:CreateDate": MetadataField(
                id="PDF:CreateDate",
                name="CreateDate",
                group="PDF",
                value="2022:12:06 11:29:06+01:00",
            ),
            "PDF:Author": MetadataField(
                id="PDF:Author", name="Author", group="PDF", value="John Doe"
            ),
            "PDF:Producer": MetadataField(
                id="PDF:Producer", name="Producer", group="PDF", value="PDF Tool"
            ),
            "PDF:Creator": MetadataField(
                id="PDF:Creator", name="Creator", group="PDF", value="PDF Tool Pro"
            ),
            "PDF:Title": MetadataField(
                id="PDF:Title", name="Title", group="PDF", value="A sample PDF"
            ),
            "PDF:ModifyDate": MetadataField(
                id="PDF:ModifyDate",
                name="ModifyDate",
                group="PDF",
                value="2022:12:06 11:30:34+01:00",
            ),
            "PDF:Keywords": MetadataField(
                id="PDF:Keywords",
                name="Keywords",
                group="PDF",
                value=["anime", "plane", "generated"],
            ),
            "PDF:PageCount": MetadataField(
                id="PDF:PageCount", name="PageCount", group="PDF", value=1
            ),
            "XMP:XMP-xmp:CreateDate": MetadataField(
                id="XMP:XMP-xmp:CreateDate",
                name="XMP-xmp:CreateDate",
                group="XMP",
                value="2022:12:06 11:29:06+01:00",
            ),
            "XMP:XMP-xmp:ModifyDate": MetadataField(
                id="XMP:XMP-xmp:ModifyDate",
                name="XMP-xmp:ModifyDate",
                group="XMP",
                value="2022:12:06 11:30:34+01:00",
            ),
            "XMP:XMP-xmp:CreatorTool": MetadataField(
                id="XMP:XMP-xmp:CreatorTool",
                name="XMP-xmp:CreatorTool",
                group="XMP",
                value="PDF Tool Pro",
            ),
            "XMP:XMP-xmp:MetadataDate": MetadataField(
                id="XMP:XMP-xmp:MetadataDate",
                name="XMP-xmp:MetadataDate",
                group="XMP",
                value="2022:12:06 11:30:34+01:00",
            ),
            "XMP:XMP-pdf:Producer": MetadataField(
                id="XMP:XMP-pdf:Producer",
                name="XMP-pdf:Producer",
                group="XMP",
                value="PDF Tool Pro",
            ),
            "XMP:XMP-pdf:Keywords": MetadataField(
                id="XMP:XMP-pdf:Keywords",
                name="XMP-pdf:Keywords",
                group="XMP",
                value="anime, plane, generated",
            ),
            "XMP:XMP-dc:Title": MetadataField(
                id="XMP:XMP-dc:Title",
                name="XMP-dc:Title",
                group="XMP",
                value="A sample PDF",
            ),
            "XMP:XMP-dc:Creator": MetadataField(
                id="XMP:XMP-dc:Creator",
                name="XMP-dc:Creator",
                group="XMP",
                value="John Doe",
            ),
            "XMP:XMP-dc:Description": MetadataField(
                id="XMP:XMP-dc:Description",
                name="XMP-dc:Description",
                group="XMP",
                value="testing",
            ),
            "XMP:XMP-dc:Subject": MetadataField(
                id="XMP:XMP-dc:Subject",
                name="XMP-dc:Subject",
                group="XMP",
                value=["anime", "plane", "generated"],
            ),
        },
        embeds={
            "0": {
                "_type": MetadataField(
                    id="_type", name="type", group=None, value="image/jpeg"
                ),
                "EXIF:XResolution": MetadataField(
                    id="EXIF:XResolution", name="XResolution", group="EXIF", value=72
                ),
                "EXIF:YResolution": MetadataField(
                    id="EXIF:YResolution", name="YResolution", group="EXIF", value=72
                ),
                "EXIF:ColorSpace": MetadataField(
                    id="EXIF:ColorSpace", name="ColorSpace", group="EXIF", value="sRGB"
                ),
                "XMP:XMP-x:XMPToolkit": MetadataField(
                    id="XMP:XMP-x:XMPToolkit",
                    name="XMP-x:XMPToolkit",
                    group="XMP",
                    value="XMP toolkit 2.8.2-33, framework 1.5",
                ),
                "Photoshop:WriterName": MetadataField(
                    id="Photoshop:WriterName",
                    name="WriterName",
                    group="Photoshop",
                    value="Adobe Photoshop",
                ),
                "Photoshop:PhotoshopFormat": MetadataField(
                    id="Photoshop:PhotoshopFormat",
                    name="PhotoshopFormat",
                    group="Photoshop",
                    value="Standard",
                ),
                "JFIF:JFIFVersion": MetadataField(
                    id="JFIF:JFIFVersion", name="JFIFVersion", group="JFIF", value=1.01
                ),
                "JFIF:ResolutionUnit": MetadataField(
                    id="JFIF:ResolutionUnit",
                    name="ResolutionUnit",
                    group="JFIF",
                    value="inches",
                ),
                "JFIF:XResolution": MetadataField(
                    id="JFIF:XResolution", name="XResolution", group="JFIF", value=72
                ),
                "JFIF:YResolution": MetadataField(
                    id="JFIF:YResolution", name="YResolution", group="JFIF", value=72
                ),
            }
        },
    )
