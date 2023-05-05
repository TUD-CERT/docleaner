import configparser
import logging
from typing import List

from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.core.job import JobType
from docleaner.api.plugins.pdf.metadata import process_pdf_metadata

logger = logging.getLogger(__name__)


def get_job_types(config: configparser.ConfigParser) -> List[JobType]:
    section = "plugins.pdf"
    if not config.has_section(section):
        logger.warning("Config section %s is missing, not loading PDF plugin", section)
        return []
    return [
        JobType(
            id="pdf",
            mimetypes=["application/pdf"],
            readable_types=["PDF"],
            sandbox=ContainerizedSandbox(
                container_image=config.get(section, "containerized.image"),
                podman_uri=config.get("docleaner", "podman_uri"),
            ),
            metadata_processor=process_pdf_metadata,
        )
    ]
