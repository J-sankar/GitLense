


def normalize_content(content: str) -> str:
    """Standardize line endings and whitespace for consistent hashing."""
    return content.replace("\r\n", "\n").strip()
