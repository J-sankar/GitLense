from datetime import datetime, timezone
from sqlalchemy.orm import Session
import uuid

from app.models.db import Job, Repo, UserRepo
from app.core.database import SessionLocal
from app.core.logger import get_logger
from app.services.github_fetcher import fetch_repo_files
from app.services.code_parser import parse_files
from app.services.embedder import  embed_batch
from app.services.vector import store_embeddings_batch
from app.services.ingest_cache import (save_job_id,get_resume_state,get_stored_chunk_count,save_batch_index, clear_cache)

import math
import time
logger = get_logger(__name__)

MAX_ATTEMPTS = 3 
BATCH_SIZE = 10

WAIT_TIME = 60

def run_ingestion(job_id: str, repo_id: str, user_id: str):
    db: Session = SessionLocal()

    try:
        # ── Setup ─────────────────────────────────────────
        job  = db.query(Job).filter(Job.id  == uuid.UUID(job_id)).first()
        repo = db.query(Repo).filter(Repo.id == uuid.UUID(repo_id)).first()

        if not job:
            raise Exception(f"Job {job_id} not found")
        if not repo:
            raise Exception(f"Repo {repo_id} not found")
        
        existing_user_repo = db.query(UserRepo).filter(
            UserRepo.user_id == uuid.UUID(user_id),
            UserRepo.repo_id == uuid.UUID(repo_id)
        ).first()

        if not existing_user_repo:
            db.add(UserRepo(
                user_id = uuid.UUID(user_id),
                repo_id = uuid.UUID(repo_id)
            ))
            logger.info(f"[{job_id[:8]}] UserRepo created")
        # ── Mark started ──────────────────────────────────
        job.status     = "started"
        job.started_at = datetime.now(timezone.utc)
        repo.status    = "processing"

        
        db.commit()
        logger.info(f"Ingestion started for repo: {repo.name}")



        state  = get_resume_state(repo_id=repo_id)
        save_job_id(repo_id, job_id)

        logger.info(f"[{job_id[:8]}] Resume state: "
            f"batch_index={state['batch_index']} | "
            f"chunks_in_db={state['chunks_in_db']} | "
            f"safe_index={state['safe_index']}")



        # ── Fetch ─────────────────────────────────────────
       
        files = fetch_repo_files(repo.repo_url)

        if not files:
            raise Exception("No files fetched from repo")
        
        logger.info(f"{job_id[:8]} | Fetched {len(files)} files")
         
        job.status = "parsing"
        job.progress = 25
        db.commit()

        # ── Parse ─────────────────────────────────────────
        
        chunks = parse_files(files)
        if not chunks:
            raise Exception("Failed to parse files")
        logger.info(f"Parsed {len(chunks)} chunks")
        job.status = "storing"
        job.progress = 50
        db.commit()


        

        start_index =   state["safe_index"]
        chunks_to_embed = chunks[start_index:]
        total_chunks = len(chunks)
        batch_length = math.ceil(total_chunks/BATCH_SIZE)

        


        if start_index > 0:
            logger.info(
                f"[{job_id[:8]}] Resuming from index {start_index} "
                f"({len(chunks_to_embed)} chunks remaining)"
            )

        for i in range (0, len(chunks_to_embed), BATCH_SIZE):
            batch = chunks_to_embed[i:i + BATCH_SIZE]
            batch_num = (start_index // BATCH_SIZE) + (i // BATCH_SIZE) + 1


            for attempt in range(MAX_ATTEMPTS):
                logger.info(
                    f"[{job_id[:8]}] "
                    f"Batch {batch_num}/{batch_length} "
                    f"attempt {attempt + 1}/{MAX_ATTEMPTS}"
                )
                try:
                    
                    embedded_chunks = embed_batch(chunks=batch)

                    logger.info(f"Embedded {len(embedded_chunks)} chunks")

                # ── Store ─────────────────────────────────────────
                    amnt_embedded = store_embeddings_batch(repo_id=str(repo.id), chunks=embedded_chunks)
                    
                    current_index = start_index + i + len(batch)
                    save_batch_index(repo_id, current_index)
                    logger.info(f"Stored {amnt_embedded} embeddings")
                    job.progress = 50 + int(50*(current_index/total_chunks))
                    repo.chunks_indexed = current_index
                    db.commit()
                    break
                except Exception as e:
                    error_msg = str(e).lower()

                    if "rate limit" in error_msg or "quota" in error_msg or "429" in error_msg:
                        logger.warning(
                            f"[{job_id[:8]}] Rate limit on batch {batch_num} "
                            f"attempt {attempt + 1}/{MAX_ATTEMPTS}"
                        )

                        if attempt < MAX_ATTEMPTS - 1:
                            logger.info(f"[{job_id[:8]}] Waiting {WAIT_TIME}s...")
                            time.sleep(WAIT_TIME)
                            continue
                        else:
                            repo.status = "failed"
                            
                            job.status = "failed"
                            repo.error_message = "Max tries reached, retry later"
                            job.error_message = f"Rate limit after {MAX_ATTEMPTS} attempts on batch {batch_num} Progress saved: {start_index + i} chunks."
                            raise Exception(
                                f"Rate limit after {MAX_ATTEMPTS} attempts "
                                f"on batch {batch_num}. "
                                f"Progress saved: {start_index + i} chunks."
                            )
                    else:
                        logger.error(f"[{job_id[:8]}] Embed failed: {str(e)}")
                        raise


        # ── Success ───────────────────────────────────────
        total_stored = get_stored_chunk_count(repo_id)
        
        job.status          = "finished"
        job.error_message = None
        job.completed_at    = datetime.now(timezone.utc)
        repo.status         = "completed"
        repo.error_message = None
        repo.chunks_indexed = total_stored
        db.commit()
        clear_cache(repo_id)
        logger.info(f"✅ Ingestion complete for repo: {repo.name} | {total_stored} chunks")
    except Exception as e:
        # ── Failure ───────────────────────────────────────
        logger.error(f"❌ Ingestion failed for repo {repo_id}: {e}")
        if job:
            job.status        = "failed"
            job.error_message = str(e)
        if repo:
            repo.status        = "failed"
            repo.error_message = str(e)
        db.commit()
        raise   # ← re-raise so RQ marks job as failed too

    finally:
        # ── Cleanup ───────────────────────────────────────
        db.close()  # always runs whether success or failure