from dataclasses import dataclass
from typing import Any, Callable, Dict, List, TYPE_CHECKING

from docleaner.api.core.job import JobType

if TYPE_CHECKING:
    from docleaner.api.services.sandbox import Sandbox


@dataclass(eq=False, kw_only=True)
class SupportedJobType:
    """Represents a supported document type and corresponding handlers."""

    type: JobType
    mimetypes: List[str]
    sandbox: "Sandbox"
    metadata_processor: Callable[[Dict[str, Dict[str, Any]]], Dict[str, Dict[str, Any]]]
