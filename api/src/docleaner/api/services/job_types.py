from dataclasses import dataclass
from typing import Any, Callable, Dict, List, TYPE_CHECKING, Union

from docleaner.api.core.job import JobType
from docleaner.api.core.metadata import DocumentMetadata

if TYPE_CHECKING:
    from docleaner.api.services.sandbox import Sandbox


@dataclass(eq=False, kw_only=True)
class SupportedJobType:
    """Represents a supported document type and corresponding handlers."""

    type: JobType
    mimetypes: List[str]
    sandbox: "Sandbox"
    metadata_processor: Callable[
        [Dict[str, Union[bool, Dict[str, Any]]]], DocumentMetadata
    ]
