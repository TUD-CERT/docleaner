from datetime import datetime

from docleaner.api.services.clock import Clock


class SystemClock(Clock):
    """Clock implementation based on the local system clock."""

    def now(self) -> datetime:
        return datetime.now()
