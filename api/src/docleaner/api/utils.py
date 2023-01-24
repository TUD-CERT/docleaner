import secrets


def generate_token() -> str:
    """Generates a base64-encoded 160 bit token."""
    return secrets.token_bytes(20).hex()
