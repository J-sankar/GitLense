from app.core.redis import (small_queue, medium_queue, large_queue)
from app.core.logger import get_logger
from app.services.github_fetcher import get_repo_size
from rq import Queue, Retry

from app.models.db import (Repo, Job)
from app.core.database import SessionLocal
from datetime import datetime ,timezone, timedelta



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
    from app.tasks.ingest_task import run_ingestion
    queue = get_ingestion_queue(repo_url)

    if not queue:
        raise Exception("Queue Service Not Available")
    queue.enqueue(
        run_ingestion, str(job_id),str(repo_id),
        job_timeout = 600,
        retry = Retry(max=3, interval=[60,120,240])
    )

    logger.info(f"Job {str(job_id)[:8]} enqueued successfully")



def recover_abandoned_jobs():
    from app.core.redis import redis_conn
    from rq.job import Job as RQJob
    db = SessionLocal()
    try:
        time_treshold = datetime.now(timezone.utc) - timedelta(minutes=30)

        stuck_jobs = db.query(Job).join(Repo).filter(
            Job.status.in_(["started","queued","processing","storing", "parsing"]),
            Job.started_at < time_treshold,
            Repo.status == "processing").all()

        if not stuck_jobs :
            logger.info("No stuck jobs found")
            return
        
        recovered = 0 
        for job in stuck_jobs :
            repo = db.query(Repo).filter(Repo.id == job.repo_id).first()

            if repo.status in ("completed","failed", "queued"):
                logger.info(
                    f"Skipping job {str(job.id)[:8]} → "
                    f"repo already {repo.status}"
                )
                continue

            new_job = db.query(Job).filter(
                Job.repo_id == job.repo_id,
                Job.id != job.id,
                Job.status.in_(["queued","started","processing","storing","parsing"]),
                Job.created_at >  job.created_at
                ).first()

            if new_job :
                logger.info(
                    f"Skipping job {str(job.id)[:8]} → "
                    f"newer job {str(new_job.id)[:8]} exists"
                )
                continue

            try :
                rq_job = RQJob.fetch(str(job.id),connection=redis_conn)
                if rq_job.get_status() in ("queued", "started"):
                    logger.info(
                        f"Skipping job {str(job.id)[:8]} → "
                        f"still active in Redis"
                    )
                    continue
            except Exception:
                pass


            logger.warning(
                f"Recovering abandoned job {str(job.id)[:8]} "
                f"repo: {str(job.repo_id)[:8]}"
            )

            job.status = "failed"
            job.error_message = "failed to embed"

            repo.status = "failed"
            repo.error_message = "failed to embed"
            recovered += 1


        if recovered > 0:
            db.commit()
            logger.info(f"✅ Recovered {recovered} abandoned jobs")
        else:
            logger.info("No jobs needed recovery")

    except Exception as e:
        logger.error(f"Failed to recover jobs: {e}")
        db.rollback()
    finally:
        db.close()


            


