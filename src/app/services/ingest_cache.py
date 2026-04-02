import json
from app.core.redis import redis_conn as redis 
from app.core.database import SessionLocal
from app.core.logger import get_logger
import uuid

logger = get_logger(__name__)

TTL = 3600 * 6

def save_job_id(repo_id: str, job_id: str):
    try:
        redis.setex(f"ingest:job:{repo_id}", TTL, job_id)
        logger.debug(f"[{repo_id[:8]}] Job ID saved: {job_id[:8]}")
    except Exception as e:
        logger.error(f"Failed to save job_id: {e}")

def load_job_id(repo_id: str) -> str | None:
    try:
        val = redis.get(f"ingest:job:{repo_id}")
        return val.decode() if val else None
    except Exception as e:
        logger.error(f"Failed to load job_id: {e}")
        return None
    


def save_step(repo_id: str, step: str):
    try:
        redis.setex(f"ingest:step:{repo_id}", TTL, step)
        logger.info(f"[{repo_id[:8]}] Step saved: {step}")
    except Exception as e:
        logger.error(f"[{repo_id[:8]}] Failed to save step: {e}")

def save_batch_index(repo_id: str, index: int):
    try:
        redis.setex(f"ingest:progress:{repo_id}", TTL, str(index))
        logger.debug(f"[{repo_id[:8]}] Batch index saved: {index}")
    except Exception as e:
        logger.error(f"[{repo_id[:8]}] Failed to save batch index: {e}")
        

def save_file_paths(repo_id: str, files: list[dict]):
    try:
        paths = [f["path"] for f in files]  # ✅ paths only
        redis.setex(
            f"ingest:files:{repo_id}",
            TTL,
            json.dumps(paths)
        )
        logger.info(f"[{repo_id[:8]}] File paths saved: {len(paths)}")
    except Exception as e:
        logger.error(f"[{repo_id[:8]}] Failed to save file paths: {e}")



def load_step(repo_id: str) -> str:
    try:
        val = redis.get(f"ingest:step:{repo_id}")
        if val:
            step = val.decode()
            logger.info(f"[{repo_id[:8]}] Loaded step from cache: {step}")
            return step
        logger.info(f"[{repo_id[:8]}] No step found in cache → starting fresh")
        return "start"   # ← default if no cache found
    except Exception as e:
        logger.error(f"[{repo_id[:8]}] Failed to load step: {e}")
        return "start"   # ← safe default on error




def load_batch_index(repo_id: str) -> int:
    try:
        val = redis.get(f"ingest:progress:{repo_id}")
        index = int(val) if val else 0
        logger.debug(f"[{repo_id[:8]}] Batch index loaded: {index}")
        return index
    except Exception as e:
        logger.error(f"[{repo_id[:8]}] Failed to load batch index: {e}")
        return 0


def get_stored_chunk_count(repo_id: str) -> int:
    from app.models.db import Repo
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(
            Repo.id == uuid.UUID(repo_id)
        ).first()
        count = repo.chunks_indexed or 0
        logger.debug(f"Chunks in DB for repo {repo_id[:8]}: {count}")
        return count
    except Exception as e:
        logger.error(f"Failed to get chunk count: {e}")
        return 0
    finally:
        db.close()

def get_resume_state( repo_id: str) -> dict:
    batch_index  = load_batch_index(repo_id)
    chunks_in_db = get_stored_chunk_count(repo_id)
    safe_index   = min(batch_index, chunks_in_db)
    cached_job_id = load_job_id(repo_id)

    logger.info(
        f"[{repo_id[:8]}] Resume state → "
        f"cached_job={cached_job_id[:8] if cached_job_id else 'none'} | "
        f"redis_index={batch_index} | "
        f"chunks_in_db={chunks_in_db} | "
        f"safe_index={safe_index}"
    )

    return {
        "batch_index":  batch_index,
        "chunks_in_db": chunks_in_db,
        "safe_index":   safe_index,
        "cached_job_id":  cached_job_id
    }




def clear_cache(repo_id: str):
    try:
        redis.delete(
            f"ingest:step:{repo_id}",
            f"ingest:progress:{repo_id}",
            f"ingest:files:{repo_id}" ,
            f"ingest:job:{repo_id}"    
        )
        logger.info(f"[{repo_id[:8]}] Cache cleared")
    except Exception as e:
        logger.error(f"[{repo_id[:8]}] Failed to clear cache: {e}")

