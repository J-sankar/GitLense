from redis import Redis
from rq import Queue

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def init_redis():
    try:
        redis_conn = Redis.from_url(settings.REDIS_URL)
        redis_conn.ping()
        logger.info("Redis connection successfull")
        return redis_conn
    except Exception as e:
        logger.error(f" Redis connection failed: {e}")
        return None


def init_queue(name:str ,redis_conn):
    try:
        ingest_queue = Queue(name, connection=redis_conn)
        return ingest_queue
    except Exception as e:
        logger.error(f"Queue initialisation failed: {e}")
        return None


redis_conn   = init_redis()


small_queue = init_queue("ingestion:small",redis_conn) if redis_conn else None
medium_queue = init_queue("ingestion:medium",redis_conn) if redis_conn else None
large_queue = init_queue("ingestion:large",redis_conn) if redis_conn else None