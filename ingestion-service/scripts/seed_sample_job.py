import asyncio
import uuid
from src.core.database import AsyncSessionLocal
from src.models.db import Repo, Job
from src.core.redis import redis_manager, STREAM_REPO_FETCH
from src.core.logger import get_logger
from src.utils.github import parse_repo_name

logger = get_logger(__name__)

async def seed_test_data():
    # 1. Initialize Redis connection
    await redis_manager.init_redis()

    # We will use the minimal test repo to keep the fan-out small
    test_repo_url = "https://github.com/spring-guides/gs-rest-service"
    
    # 2. Generate valid UUIDs
    new_repo_id = uuid.uuid4()
    new_job_id = uuid.uuid4()

    logger.info(f"Generated Repo UUID: {new_repo_id}")
    logger.info(f"Generated Job UUID: {new_job_id}")

    # 3. Insert into PostgreSQL via SQLAlchemy
    async with AsyncSessionLocal() as db:
        try:
            # NOTE: You may need to adjust these field names (like 'url' or 'repo_url') 
            # to match exactly what is defined in your src.models.db classes!
            owner, repo_name =  parse_repo_name(test_repo_url)
            new_repo = Repo(
                id=new_repo_id,
                # url=test_repo_url,  <-- Uncomment/adjust based on your actual Repo model fields
                status="pending"
            )
            new_repo.repo_url = test_repo_url
            new_job = Job(
                id=new_job_id,
                # repo_id=new_repo_id, <-- Uncomment/adjust if your Job model has a foreign key to Repo
                status="queued"
            )
            new_job.repo_id = new_repo_id
            new_repo.name = repo_name
        

            db.add(new_repo)
            db.add(new_job)
            await db.commit()
            logger.info("Successfully committed Repo and Job to the database.")

        except Exception as e:
            await db.rollback()
            logger.error(f"Database error. Did you miss a required field?: {e}")
            await redis_manager.close()
            return

    # 4. Publish to Redis Stream to wake up your worker
    payload = {
        "job_id": str(new_job_id),
        "repo_id": str(new_repo_id),
        "repo_url": test_repo_url,
        "retries": 0
    }

    try:
        msg_id = await redis_manager.publish(STREAM_REPO_FETCH, payload)
        logger.info(f"Successfully published to stream '{STREAM_REPO_FETCH}' (Msg ID: {msg_id})")
    except Exception as e:
        logger.error(f"Failed to publish to Redis: {e}")
    finally:
        # Clean up the Redis connection pool before exiting
        await redis_manager.close()

if __name__ == "__main__":
    asyncio.run(seed_test_data())