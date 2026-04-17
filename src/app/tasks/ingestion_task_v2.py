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
        await process_repository(db, repo=repo, job= job,files=files)
       
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
        error_msg = str(e).lower()
        logger.error(f"Ingestion Task Failed: {error_msg}")

        # 1. CRITICAL: Rollback the poisoned transaction
        try:
            db.rollback() 
        except Exception as rb_err:
            logger.error(f"Rollback failed: {rb_err}")

        # 2. Update status safely
        if repo:
            repo.status = "failed"
            # It's better to store the actual error so you can see it in the UI
            repo.error_message = f"Ingestion failed: {error_msg[:100]}" 
        
        if job:
            job.status = "failed"
            job.error_message = error_msg
        
        # 3. Final attempt to save the failure status
        try:
            db.commit()
        except Exception as commit_err:
            logger.error(f"Final status commit failed: {commit_err}")

        # 4. Filtered Re-raising
        if "quota" in str(e).lower() or "429" in str(e).lower():
            logger.error("Quota hit. Stopping job without retry.")
            # By NOT raising, RQ treats this as 'Done'
            return
        if any(stop_word in error_msg for stop_word in ["job not found", "repo not found"]):
            logger.warning("Aborting task permanently: Resource not found.")
            return

        # Re-raise for RQ to handle retries if configured
        raise Exception(f"INGESTION FAILED: {error_msg}")

    finally:
        # 5. Always close, but make sure the session is valid
        db.close()


if __name__ == "__main__":
    asyncio.run(test_run_ingestion())




    