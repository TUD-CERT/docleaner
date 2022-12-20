import magic

from docleaner.api.services.file_identifier import FileIdentifier


class MagicFileIdentifier(FileIdentifier):
    """Identifies file types via libmagic."""

    def identify(self, source: bytes) -> str:
        return magic.from_buffer(source, mime=True)
