from app.core.redis import redis_conn, ingest_queue
from app.core.logger import get_logger
from rq import Worker

logger = get_logger(__name__)

if __name__ == "__main__":
    if not redis_conn or not ingest_queue:
        logger.error("❌ Cannot start worker: Redis is not connected")
    else:
        logger.info("✅ Worker is listening on 'ingestion' queue...")
        worker = Worker([ingest_queue], connection=redis_conn)
        worker.work()  # blocking — nothing below this runs