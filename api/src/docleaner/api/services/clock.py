import abc
from datetime import datetime


class Clock(abc.ABC):
    """Interface to keep track of passing time."""

    @abc.abstractmethod
    def now(self) -> datetime:
        """Returns the current date and time."""
        raise NotImplementedError()
