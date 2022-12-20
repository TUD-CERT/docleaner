import abc


class FileIdentifier(abc.ABC):
    """Interface for an identification mechanism that guesses file/document formats."""

    def identify(self, source: bytes) -> str:
        """Guesses a MIME type for the given source document."""
        raise NotImplementedError()
