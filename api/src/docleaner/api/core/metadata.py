from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, Optional, List


class MetadataTag(IntEnum):
    # Capabilities
    DELETABLE = 0
    # Categorizations
    ACCESSIBILITY = 100
    SIGNATURE = 101
    COMPLIANCE = 102  # A tag required to conform to a certain document standard


@dataclass(eq=True, kw_only=True)
class MetadataField:
    """A document's unique key-value metadata field with associated data
    such as an optional description and a set of tags."""

    id: str  # Document-wide unique identifier
    value: Any
    description: Optional[str] = None
    name: Optional[str] = None  # Display name (to assist UI/presentation)
    group: Optional[str] = None  # String-based grouping (to assist UI/presentation)
    tags: List[MetadataTag] = field(default_factory=list)


@dataclass(eq=True, kw_only=True)
class DocumentMetadata:
    """Aggregation of metadata fields for a single document, covering both
    primary (of the document itself) and secondary metadata (of embedded documents)."""

    primary: Dict[str, MetadataField] = field(default_factory=dict)
    embeds: Dict[str, Dict[str, MetadataField]] = field(default_factory=dict)
