from dataclasses import dataclass, field
from datetime import datetime


@dataclass(eq=False, kw_only=True)
class Session:
    """A session encompasses a batch of jobs. Can be used to
    create and monitor multiple jobs in parallel. In addition,
    jobs associated with a session are treated differently by
    the job cleaner (are kept for a longer duration)."""

    id: str  # Unique identifier
    created: datetime  # Session creation timestamp
    updated: datetime = field(init=False)  # Last update timestamp

    def __post_init__(self) -> None:
        self.updated = self.created
