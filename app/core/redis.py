from redis import Redis
from rq import Queue

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def init_redis():
    try:
        redis_conn = Redis.from_url(settings.REDIS_URL)
        redis_conn.ping()
        logger.info("✅ Redis connection successful")
        return redis_conn
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return None


def init_queue(redis_conn):
    try:
        ingest_queue = Queue("ingestion", connection=redis_conn)
        logger.info("✅ Queue initialised")
        return ingest_queue
    except Exception as e:
        logger.error(f"❌ Queue initialisation failed: {e}")
        return None


redis_conn   = init_redis()
ingest_queue = init_queue(redis_conn) if redis_conn else None
