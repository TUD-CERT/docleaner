from datetime import datetime, timedelta
from typing import Optional

from docleaner.api.services.clock import Clock


class DummyClock(Clock):
    """Clock simulation for tests that has to be set manually."""

    def __init__(self, start: Optional[datetime] = None):
        self._time = start or datetime.now()

    def now(self) -> datetime:
        return self._time  # datetime instances are immutable

    def advance(self, seconds: int) -> datetime:
        """Advances the current time by the given number of seconds."""
        self._time += timedelta(seconds=seconds)
        return self._time
