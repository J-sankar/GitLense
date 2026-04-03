import asyncio

from app.core.logger import get_logger
from app.services.github_fetcher import fetch_repo_files
from app.ingestion.processor import process_repository
from app.models.db import Repo,Job
from app.core.database import SessionLocal

logger = get_logger(__name__)
async def test_run_ingestion():
    db = SessionLocal()
    TEST_URL = "https://github.com/teamwhiplash/Emo-tunes"
    try:
        test_repo = db.query(Repo).filter(Repo.name == "teamwhiplash/Emo-tunes").first()
        if not test_repo:
            test_repo = Repo(name="teamwhiplash/Emo-tunes",repo_url=TEST_URL,status="queued")
            db.add(test_repo)
            db.flush()
        

        test_job = Job(
            repo_id=test_repo.id,
            status="queued",
            progress=0
        )
        db.add(test_job)
        db.commit()

        logger.info("created test repo and job")
        files = await fetch_repo_files(TEST_URL)

        logger.info("Processing repo...")
        process_repository(db,str(test_repo.id), job_id=str(test_job.id), files=files)
        db.refresh(test_repo)
        db.refresh(test_job)

        logger.info("\n--- TEST COMPLETE ---")
        logger.info(f"Final Status: {test_repo.status}")
        logger.info(f"Final Progress: {test_job.progress}%")

        if test_repo.status == "completed":
            logger.info("SUCCESS: Data is in Postgres and Qdrant.")
        else:
            logger.error(f"FAILED: {test_repo.error_message}")

    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_run_ingestion())




    