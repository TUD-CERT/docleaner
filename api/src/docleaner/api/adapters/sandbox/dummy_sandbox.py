import asyncio

from docleaner.api.services.sandbox import Sandbox, SandboxResult


class DummySandbox(Sandbox):
    """For testing, executes each job by successfully returning a dummy result or an error (configurable)."""

    def __init__(self, simulate_errors: bool = False):
        """Set simulate_errors to True to force this sandbox to simulate an error on each job."""
        self._running = asyncio.Event()
        self._running.set()
        self._simulate_errors = simulate_errors

    async def process(self, source: bytes) -> SandboxResult:
        await self._running.wait()
        return SandboxResult(
            success=not self._simulate_errors,
            log=["Executing job in dummy sandbox"],
            result=b"" if self._simulate_errors else b"%PDF-1.7",
            metadata_result={
                "primary": {"XMP:Author": "Alice", "XMP:Domain": "example.com"},
                "embeds": {"Doc1": {"XMP:Domain": "example.com"}},
            },
            metadata_src={
                "primary": {"XMP:Domain": "example.com"},
                "embeds": {
                    "Doc1": {"XMP:Author": "Alice", "XMP:Domain": "example.com"}
                },
            },  # Assumes the sandbox didn't purge all metadata
        )

    async def halt(self) -> None:
        """For testing, stops job processing. Processing will resume after resume() has been called."""
        self._running.clear()

    async def resume(self) -> None:
        """For testing, resumes job processing."""
        self._running.set()
