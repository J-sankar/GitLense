import asyncio
from app.core.logger import get_logger
from app.services.github_fetcher import fetch_repo_files
from app.ingestion.processor import process_repository
from app.models.db import Repo,Job
from app.core.database import SessionLocal
from uuid import UUID 

logger = get_logger(__name__)
async def test_run_ingestion( job_id: str, repo_id: str):
    db = SessionLocal()
    repo = None
    job = None
    try:
        repo = db.query(Repo).filter(Repo.id == UUID(repo_id)).first()
        if not repo:
            raise Exception("Repo not found")
        
        job = db.query(Job).filter(Job.id == UUID(job_id)).first()

        if not job:
            raise Exception("Job not found")

        repo.status = "processing"
        job.status = "processing"

        db.add_all([repo,job])
        db.commit()

        files = await fetch_repo_files(repo.repo_url)

        logger.info("Processing repo...")
        process_repository(db, repo=repo, job= job,files=files)
       
        repo.status = "completed"
        repo.error_message = None
        job.status = "finished"
        job.error_message= ""

        db.commit()

        logger.info("\n--- INGESTION COMPLETE ---")
        logger.info(f"Final Status: {repo.status}")
        logger.info(f"Final Progress: {job.progress}%")

        if repo.status == "completed":
            logger.info("SUCCESS: INGESTION COMPLETE.")
        else:
            logger.error(f"FAILED: {repo.error_message}")

    except Exception as e:
        db.rollback()
        if repo is not None:
            repo.status = "failed"
            repo.error_message = "failed to ingest"
        if job is not None:
            job.status = "failed"
            job.error_message = "failed"
            db.commit()
        else:
            logger.warning("Could not update job status because job object is None")
        
        # If it's a "Job not found" error, maybe don't re-raise it 
        # so RQ doesn't try to retry a non-existent job.
        try:
            if repo or job:
                db.commit()
        except Exception as commit_err:
            logger.error(f"Failed to save 'failed' status to DB: {commit_err}")
        if "job not found" in str(e).lower():
            logger.warning(f"Aborting task: {e}. No retry will be attempted.")
            return
        if "repo not found" in str(e).lower():
            logger.warning(f"Aborting task: {e}. No retry will be attempted.")
            return
        
        raise e 
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_run_ingestion())




    