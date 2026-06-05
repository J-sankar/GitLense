import asyncio
import sys
from uuid import UUID

from sqlalchemy import select, delete

from src.core.database import AsyncSessionLocal
from src.core.logger import get_logger
from src.models.db import UserRepo, Job, Repo, FileMetaData
from src.services.vector import delete_embeddings
from src.core.redis import (
    redis_manager,
    STREAM_REPO_FETCH,
    STREAM_FILE_PROCESS,
    STREAM_FILE_STORE,
    STREAM_FAILED,
    GROUP_FETCH,
    GROUP_PROCESS,
    GROUP_STORE,
)

logger = get_logger(__name__)


async def clear_streams(repo_id: str):
    """Remove all stream messages related to this repo_id"""
    r = redis_manager.client
    if not r:
        logger.warning("Redis not connected — skipping stream cleanup")
        return

    streams = [
        STREAM_REPO_FETCH,
        STREAM_FILE_PROCESS,
        STREAM_FILE_STORE,
        STREAM_FAILED,
    ]

    total_deleted = 0

    for stream in streams:
        try:
            # read all messages in stream
            messages = await r.xrange(stream, "-", "+")
            if not messages:
                continue

            # filter messages belonging to this repo_id
            to_delete = [
                msg_id
                for msg_id, data in messages
                if data.get("repo_id") == repo_id
            ]

            if to_delete:
                await r.xdel(stream, *to_delete)
                total_deleted += len(to_delete)
                logger.info(f"Deleted {len(to_delete)} messages from {stream}")

        except Exception as e:
            logger.error(f"Failed to clean stream {stream}: {e}")

    logger.info(f"Stream cleanup complete — {total_deleted} messages deleted")


async def clear_progress(repo_id: str):
    """Remove progress keys from Redis for all jobs of this repo"""
    r = redis_manager.client
    if not r:
        return

    try:
        # find all progress keys for jobs related to this repo
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Job.id).where(Job.repo_id == UUID(repo_id))
            )
            job_ids = result.scalars().all()

        for job_id in job_ids:
            key = f"ingestion:progress:{str(job_id)}"
            await r.delete(key)
            logger.info(f"Deleted progress key for job {str(job_id)[:8]}")

    except Exception as e:
        logger.error(f"Failed to clear progress keys: {e}")


async def clear_repo(repo_id: str):
    await redis_manager.init_redis()

    async with AsyncSessionLocal() as db:
        try:
            repo_uuid = UUID(repo_id)

            result = await db.execute(select(Repo).where(Repo.id == repo_uuid))
            repo   = result.scalar_one_or_none()

            if not repo:
                logger.error(f"Repo {repo_id} not found")
                return

            logger.info(f"Cleaning repo: {repo.name}")

            # 1. delete vectors from Qdrant
            await delete_embeddings(repo_id=repo_id)
            logger.info("Deleted embeddings from Qdrant")

            # 2. clean Redis streams
            await clear_streams(repo_id)

            # 3. clean progress keys
            await clear_progress(repo_id)

            # 4. delete DB records
            await db.execute(delete(FileMetaData).where(FileMetaData.repo_id == repo_uuid))
            logger.info("Deleted file metadata")

            await db.execute(delete(Job).where(Job.repo_id == repo_uuid))
            logger.info("Deleted jobs")

            await db.execute(delete(UserRepo).where(UserRepo.repo_id == repo_uuid))
            logger.info("Deleted user repos")

            await db.delete(repo)
            await db.commit()
            logger.info(f"Repo {repo_id} fully deleted ✓")

        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting repo: {e}")

    await redis_manager.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(clear_repo(sys.argv[1]))
    else:
        print("Usage: uv run python scripts/clear_repo.py <repo_id>")