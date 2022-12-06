import base64
import secrets


def generate_token() -> str:
    """Generates a base64-encoded 160 bit token."""
    return base64.urlsafe_b64encode(secrets.token_bytes(20)).decode("ascii")
