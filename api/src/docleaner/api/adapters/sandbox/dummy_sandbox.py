from docleaner.api.services.sandbox import Sandbox, SandboxResult


class DummySandbox(Sandbox):
    """For testing, executes each job by successfully returning a dummy result or an error (configurable)."""

    def __init__(self, simulate_errors: bool = False):
        """Set simulate_errors to True to force this sandbox to simulate an error on each job."""
        self._simulate_errors = simulate_errors

    async def process(self, source: bytes) -> SandboxResult:
        return SandboxResult(
            success=not self._simulate_errors,
            log=["Executing job in dummy sandbox"],
            result=b"" if self._simulate_errors else b"%PDF-1.7",
            metadata_result={"author": "Alice", "domain": "example.com"},
            metadata_src={
                "domain": "example.com"
            },  # Assumes the sandbox didn't purge all metadata
        )
