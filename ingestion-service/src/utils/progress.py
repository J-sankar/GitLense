from src.core.redis import redis_manager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from src.models.db import Job, Repo
from src.core.logger import get_logger
logger = get_logger(__name__)

PREFIX = "ingestion:progress"

async def init_progress(job_id: str, total_files: int):
    r = redis_manager.client
    await r.hset(f"{PREFIX}:{job_id}", mapping={
        "total_files": total_files,
        "fetched":     0,
        "processed":   0,
        "stored":      0,
    })
    await r.expire(f"{PREFIX}:{job_id}", 86400)

async def increment_fetch(job_id:str, count:int):
    r = redis_manager.client
    await r.hset(f"{PREFIX}:{job_id}", "fetched", count )

async def increment_processed(job_id:str):
    r = redis_manager.client
    await r.hincrby(f"{PREFIX}:{job_id}", "processed", 1 )

async def increment_stored(job_id:str):
    r = redis_manager.client
    await r.hincrby(f"{PREFIX}:{job_id}", "stored", 1 )

def _calculate_progress(fetched: int,processed:int, stored:int,  total: int) -> int:
    if total == 0:
        return 0
    fetch_progress = (fetched/total) * 33
    processed_progress = (processed/total) * 33
    stored_progress = (stored/total)*34
    total_progress = int(fetch_progress+processed_progress+stored_progress)
    return total_progress



async def flush_to_db(
    db:      AsyncSession,    # ← caller passes their session
    job:  Job,
    repo: Repo
):
    """
    Reads from Redis and writes to DB.
    Uses caller's session — rollback covers this too.
    """
    try:
        job_id = str(job.id)
        data = await get_progress((str(job.id)))
        if not data:
            return

        await db.execute(
            update(Job)
            .where(Job.id == job.id)
            .values(
                progress   = data["progress"],
                fetched_files = data["fetched"],
                processed_files = data["processed"],
                stored_files = data["stored"]

            )
        )

        await db.refresh(job)

        

        # caller commits — not us
        logger.debug(f"Progress staged for DB: job={job_id[:8]}")

    except Exception as e:
        logger.error(f"Failed to stage progress for DB: {e}")
        raise  

            



async def get_progress(job_id: str) -> dict | None:
    """Gets current progress from Redis"""
    try:
        r    = redis_manager.client
        data = await r.hgetall(f"{PREFIX}:{job_id}")
        if not data:
            return None
        total     = int(data.get("total_files", 0))
        fetched   = int(data.get("fetched",     0))
        processed = int(data.get("processed",   0))
        stored    = int(data.get("stored",      0))
        progress =  _calculate_progress(fetched,processed,stored,total)
        return {
            "total_files": total,
            "fetched":     fetched,
            "processed":   processed,
            "stored":      stored,
            "progress":    progress,
        }
    except Exception as e:
        logger.error(f"Failed to get progress from Redis: {e}")
        return None