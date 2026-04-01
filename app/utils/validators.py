
from urllib.parse import urlparse



def validate_repo_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https") and
            "github.com" in parsed.netloc
        )
    except Exception:
        return False