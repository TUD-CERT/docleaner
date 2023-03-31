import configparser
from typing import List

from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.core.job import JobType
from docleaner.api.plugins.pdf.metadata import process_pdf_metadata


def get_job_types(config: configparser.ConfigParser) -> List[JobType]:
    section = "plugins.pdf"
    if not config.has_section(section):
        return []
    return [
        JobType(
            id="pdf",
            mimetypes=["application/pdf"],
            readable_types=["PDF"],
            sandbox=ContainerizedSandbox(
                container_image=config.get(section, "container_image"),
                podman_uri=config.get(section, "podman_uri"),
            ),
            metadata_processor=process_pdf_metadata,
        )
    ]