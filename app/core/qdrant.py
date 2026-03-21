from qdrant_client import QdrantClient
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def init_qdrant() -> QdrantClient | None:
    try:
        client = QdrantClient(
            url     = settings.QDRANT_URL,
            api_key = settings.QDRANT_API_KEY,
            timeout = 60
        )
        # ── verify connection ─────────────────────────
        client.get_collections()
        logger.info("✅ Qdrant connected successfully")
        return client
    except Exception as e:
        logger.error(f"❌ Qdrant connection failed: {e}")
        return None


qdrant_client = init_qdrant()