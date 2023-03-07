from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, Optional, List


class MetadataTag(IntEnum):
    # Capabilities
    DELETABLE = 0
    # Categorizations
    ACCESSIBILITY = 100
    COMPLIANCE = 101  # A tag required to conform to a certain document standard
    LEGAL = 102  # Tag related to legal/copyright matters


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
    """Aggregation of metadata fields for a single document, covering signature status
    and primary (of the document itself) as well as secondary metadata (of embedded documents)."""

    primary: Dict[str, MetadataField] = field(default_factory=dict)
    embeds: Dict[str, Dict[str, MetadataField]] = field(default_factory=dict)
    signed: bool = False
