import configparser
import logging
from typing import Any, Dict, List, Union

from docleaner.api.adapters.sandbox.containerized_sandbox import ContainerizedSandbox
from docleaner.api.core.job import JobType
from docleaner.api.core.metadata import DocumentMetadata

logger = logging.getLogger(__name__)


def process_metadata(src: Dict[str, Union[bool, Dict[str, Any]]]) -> DocumentMetadata:
    return DocumentMetadata()


def get_job_types(config: configparser.ConfigParser) -> List[JobType]:
    section = "plugins.watermark"
    if not config.has_section(section):
        logger.warning("Config section %s is missing, not loading Watermark plugin", section)
        return []
    return [
        JobType(
            id="watermark",
            mimetypes=["application/pdf"],
            readable_types=["PDF"],
            sandbox=ContainerizedSandbox(
                container_image=config.get(section, "containerized.image"),
                podman_uri=config.get("docleaner", "podman_uri"),
            ),
            metadata_processor=process_metadata
        )
    ]
