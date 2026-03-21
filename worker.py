from app.core.redis import redis_conn,small_queue,medium_queue,large_queue
from app.core.logger import get_logger
from app.core.queue import recover_abandoned_jobs
from rq import Worker
import sys
logger = get_logger(__name__)



QUEUES = {
    "small":small_queue,
    "medium": medium_queue,
    "large": large_queue
}

if __name__ == "__main__":
    if not redis_conn :
        logger.error("❌ Cannot start worker: Redis is not connected")
        sys.exit(1)
    else:
        recover_abandoned_jobs()
        queue_type = sys.argv[1] if  len(sys.argv) > 1 else "all"

        logger.info(f"Worker listening on queue, type: {queue_type}")
        if queue_type == "all":
            queues = [small_queue, medium_queue, large_queue]
        elif queue_type in QUEUES :
            queues = [QUEUES[queue_type]]
        else :
            logger.error(f" Unknown Queue: {queue_type}")
            sys.exit(1)

        queues = [q for q in queues if q is not  None]

        if not queues :
            logger.error("No queues available")
            sys.exit(1)

        worker = Worker(queues=queues, connection=redis_conn)
        worker.work()