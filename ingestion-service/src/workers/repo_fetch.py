import asyncio

from src.core.logger import get_logger
from src.services.github_fetcher import fetch_repo_files
from src.core.redis import (
    redis_manager,
    STREAM_REPO_FETCH,
    GROUP_FETCH,
    STREAM_FILE_PROCESS,
)
from src.models.db import Repo, Job
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.utils.progress import  flush_to_db,init_progress,increment_fetch
import uuid

logger = get_logger(__name__)
CONSUMER_NAME = "fetch-worker-1"

MAX_RETRIES = 3


async def process_fetch_message(message_id: str, payload: str):
    repo_id = payload.get("repo_id")
    job_id = payload.get("job_id")
    repo_url = payload.get("repo_url")
    retries = int(payload.get("retries", 0))
    async with AsyncSessionLocal() as db:
        try:
            # Fetch DB records
            result = await db.execute(select(Repo).where(Repo.id == uuid.UUID(repo_id)))
            repo = result.scalar_one_or_none()

            job_result = await db.execute(
                select(Job).where(Job.id == uuid.UUID(job_id))
            )
            job = job_result.scalar_one_or_none()

            if not repo or not job:
                logger.error(f"Repo or Job not found in DB for payload: {payload}")
                await redis_manager.ack(
                    STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME, message_id
                )
                return

            # Update status to processing
            repo.status = "fetching"
            job.status = "processing"
            repo.error_message = ""

            await db.commit()
            await db.refresh(repo)
            await db.refresh(job)

            logger.info(f"Processing job: {job_id} | repo_id: {repo_id}")

            files = await fetch_repo_files(repo_url=repo_url)
            logger.info(f"Obtained {len(files)} files from {repo_url}")
            if not files:
                repo.status = "failed"
                repo.error_message = "No files returned from GitHub"
                job.status = "failed"
                job.error_message = "No files returned from GitHub"
                db.add(job)
                db.add(repo)
                await db.commit()  

                await redis_manager.ack(
                    STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME, message_id
                )
                logger.error(f"No files found for {repo_url} - marked as failed")
                return  

            total_files = len(files)
            await init_progress(job_id, total_files=total_files)
            job.total_files = total_files
            await db.commit()

            for file in files:
                logger.info(f"{file['path']} fetched from {repo_url}")
                logger.debug(
                    f"file_name: {file['path']}, language: {file['language']}, content: {file['content'][:10]}"
                )

                
                file_payload = {
                    "repo_id": str(repo_id),
                    "job_id": str(job_id),
                    "repo_url": str(repo_url),
                    "file_path": str(file["path"]),
                    "language": str(file["language"]),
                    "content": str(file["content"]),
                    "retries": "0",
                }
              
                await redis_manager.publish(STREAM_FILE_PROCESS, file_payload)

            # 4. ACK ONLY AFTER EVERYTHING SUCCEEDS
            await increment_fetch(job_id, total_files)
            await flush_to_db(db,job,repo)
            repo.status = "processing"
            db.add(repo)
            await db.commit()
            await redis_manager.ack(
                STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME, message_id
            )
            logger.info(f"Successfully processed and ACKed job {job_id}")

        except Exception as e:
            await db.rollback()  # Revert any unsaved DB changes
            error_msg = str(e).lower()
            logger.error(f"ERROR processing {repo_url}: {error_msg}")

            try:
                if repo and job:
                    repo.status = "failed"
                    job.status = "failed"
                    repo.error_message = error_msg[:200]
                    job.error_message = error_msg[:200]
                    await db.commit()
            except Exception as db_err:
                logger.error(f"Failed to save db status : {str(db_err).lower()} ")

            if "quota" in error_msg or "rate" in error_msg:
                logger.warning(
                    f"Quota hit for repo_url : {repo_url}| try: {payload.get('retries')} -- DEAD LETTER"
                )
                await redis_manager.dead_letter(
                    STREAM_REPO_FETCH,
                    payload,
                    error=error_msg[:200],
                    reason="quota_hit",
                )
                logger.info(f"DEAD LETTER SENT | repo_url : {repo_url}")
                await redis_manager.ack(
                    STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME, message_id
                )
                logger.info(f"ACK repo_url: {repo_url}")

            elif retries < MAX_RETRIES:
                logger.warning(
                    f"Retrying {repo_url} attempt {retries + 1}/{MAX_RETRIES}"
                )
                await redis_manager.republish_with_retry(
                    STREAM_REPO_FETCH, payload, retries=retries + 1
                )
                await redis_manager.ack(
                    STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME, message_id
                )
            else:
                logger.warning(f"Max retries exceeded : {repo_url} | DEAD LETTER")
                await redis_manager.dead_letter(
                    STREAM_REPO_FETCH, payload, error_msg, reason="Max retries reached"
                )
                logger.info(f"DEAD LETTER SENT: {repo_url}")
                await redis_manager.ack(
                    STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME, message_id
                )


async def start_worker():

    await redis_manager.init_redis()
    await redis_manager._init_consumer_groups()
    claimed_messages = await redis_manager.reclaim_abandoned(
        STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME
    )
    if claimed_messages:
        logger.info(f"Processing {len(claimed_messages)} reclaimed messages...")
        for message_id, payload in claimed_messages:
            # Process them exactly like new messages
            await process_fetch_message(message_id, payload)

    logger.info(f"Worker {GROUP_FETCH} listening on {STREAM_REPO_FETCH}")

    while True:
        try:
            results = await redis_manager.consume(
                STREAM_REPO_FETCH, GROUP_FETCH, CONSUMER_NAME
            )

            if not results:
                continue
            for stream_name, messages in results:
                for message_id, payload in messages:
                    logger.debug(f"{message_id}:{payload}")
                    await process_fetch_message(message_id, payload)
            logger.debug(f"Obtained result: {results}")

        except Exception as e:
            await asyncio.sleep(2)
            logger.warning(f"Fetch Worker Loop Error: {e}")


if __name__ == "__main__":
    asyncio.run(start_worker())
