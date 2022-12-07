from typing import Tuple, List

from docleaner.api.services.sandbox import Sandbox


class DummySandbox(Sandbox):
    """For testing, executes each job by successfully returning a dummy result or an error (configurable)."""

    def __init__(self, simulate_errors: bool = False):
        """Set simulate_errors to True to force this sandbox to simulate an error on each job."""
        self._simulate_errors = simulate_errors

    async def process(self, source: bytes) -> Tuple[List[str], bool, bytes]:
        return (
            ["Executing job in dummy sandbox"],
            not self._simulate_errors,
            b"" if self._simulate_errors else b"RESULT",
        )
