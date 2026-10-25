from qdrant_client import AsyncQdrantClient
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


def init_qdrant() -> AsyncQdrantClient | None:
    try:
        client = AsyncQdrantClient(
            url     = settings.QDRANT_URL,
            api_key = settings.QDRANT_API_KEY,
            timeout = 10
        )
        # ── verify connection ─────────────────────────

        logger.info("Qdrant connected successfully")
        return client
    except Exception as e:
        logger.error(f"Qdrant connection failed: {e}")
        return None


qdrant_client = init_qdrant()