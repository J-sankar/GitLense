from app.core.redis import (small_queue, medium_queue, large_queue,redis_conn)
from app.core.logger import get_logger
from app.services.github_fetcher import get_repo_size
from rq import Queue, Retry
from sqlalchemy import  not_,select,and_
from app.models.db import (Repo, Job)
from app.core.database import SessionLocal
from datetime import datetime ,timezone, timedelta

from rq.job import Job as RQJob




logger = get_logger(__name__)


SMALL_REPO_MAX  = 1000   # < 1MB
MEDIUM_REPO_MAX = 5000


def get_ingestion_queue(repo_url: str) -> Queue :
    repo_size = get_repo_size(repo_url)

    if repo_size < SMALL_REPO_MAX:
        logger.info(f"Repo {repo_size}KB → small queue")
        return small_queue
    elif repo_size < MEDIUM_REPO_MAX :
        logger.info(f"Repo {repo_size}KB → medium queue")
        return medium_queue
    else :
        logger.info(f"Repo {repo_size}KB → large queue")
        return large_queue
    

def queue_ingestion(repo_url: str, job_id: str, repo_id: str) :
    # from app.tasks.ingest_task import run_ingestion
    from app.tasks.ingestion_task_v2 import test_run_ingestion
    queue = get_ingestion_queue(repo_url)

    if not queue:
        raise Exception("Queue Service Not Available")
    queue.enqueue(
        test_run_ingestion, str(job_id),str(repo_id),
        job_timeout = 600,
        retry = Retry(max=3, interval=[60,120,240])
    )

    logger.info(f"Job {str(job_id)[:8]} enqueued successfully")



def recover_abandoned_jobs():
    db = SessionLocal()
    try:
        
        threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        TRANSIENT_STATUSES = ["started", "queued", "processing", "storing", "parsing"]

        
        active_repo_ids = select(Job.repo_id).where(
            and_(
                Job.created_at > threshold,
                Job.status.in_(TRANSIENT_STATUSES + ["completed"])
            )
        ).distinct()
        
        stuck_items = db.query(Job, Repo).join(Repo).filter(
            Job.status.in_(TRANSIENT_STATUSES),
            Job.started_at < threshold,
            Repo.status == "processing",
            not_(Job.repo_id.in_(active_repo_ids)) 
        ).all()

        if not stuck_items:
            logger.info("Scan complete: No abandoned jobs found.")
            return

        # 3. THE BATCH UPDATE
        # Since 'repo' is already loaded, we just update the objects in memory
        for job, repo in stuck_items:
            job.status = "failed"
            repo.status = "failed"
            job.error_message = repo.error_message = "Failed to embed"

            try:
                rq_job = RQJob.fetch(job.id, connection=redis_conn)
                rq_job.move_to_failed_queue() 
            except Exception:
                pass
        
        # One single commit for all changes
        db.commit()
        logger.info(f"Successfully recovered {len(stuck_items)} jobs")

    except Exception as e:
        db.rollback()
        logger.error(f"Recovery failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    from app.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Starting manual job recovery...")
    recover_abandoned_jobs()