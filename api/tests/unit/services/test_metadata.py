from typing import Any, Dict

from docleaner.api.services.metadata import process_pdf_metadata


def test_process_pdf() -> None:
    metadata: Dict[str, Dict[str, Any]] = {
        "doc": {
            "PDFVersion": "1.5",
            "Creator": "Acrobat PDFMaker 11 für PowerPoint",
            "Title": "Folie 1",
            "Language": "DE-DE",
        },
        "embeds": {
            "XMP": {
                "CreatorTool": "Acrobat PDFMaker 11 für PowerPoint",
                "Format": "application/pdf",
                "Title": "Folie 1",
            },
            "ICC_Profile": {"ProfileVersion": "2.1.0", "ColorSpaceData": "RGB "},
            "Composite": {"ImageSize": "456x318", "Megapixels": 0.145},
            "Doc1": {
                "PDF": {"EmbeddedImageColorSpace": "ICCBased"},
                "File": {
                    "FileType": "JPEG",
                    "FileTypeExtension": "jpg",
                    "MIMEType": "image/jpeg",
                    "ImageWidth": 456,
                    "ImageHeight": 789,
                },
                "APP14": {"DCTEncodeVersion": 100},
                "EXIF": {"XResolution": 72, "YResolution": 72, "ColorSpace": "sRGB"},
                "XMP": {"XMPToolkit": "XMP toolkit 2.8.2-33, framework 1.5"},
                "Photoshop": {
                    "WriterName": "Adobe Photoshop",
                    "PhotoshopFormat": "Standard",
                },
                "JFIF": {
                    "JFIFVersion": 1.01,
                    "ResolutionUnit": "inches",
                    "XResolution": 72,
                    "YResolution": 72,
                },
            },
        },
    }
    expected_result = {
        "doc": {
            "PDFVersion": "1.5",
            "Creator": "Acrobat PDFMaker 11 für PowerPoint",
            "Title": "Folie 1",
            "Language": "DE-DE",
            "XMP:CreatorTool": "Acrobat PDFMaker 11 für PowerPoint",
            "XMP:Format": "application/pdf",
            "XMP:Title": "Folie 1",
        },
        "embeds": {
            "0": {
                "_type": "image/jpeg",
                "EXIF": {"XResolution": 72, "YResolution": 72, "ColorSpace": "sRGB"},
                "XMP": {"XMPToolkit": "XMP toolkit 2.8.2-33, framework 1.5"},
                "Photoshop": {
                    "WriterName": "Adobe Photoshop",
                    "PhotoshopFormat": "Standard",
                },
                "JFIF": {
                    "JFIFVersion": 1.01,
                    "ResolutionUnit": "inches",
                    "XResolution": 72,
                    "YResolution": 72,
                },
            }
        },
    }
    result = process_pdf_metadata(metadata)
    assert result == expected_result
