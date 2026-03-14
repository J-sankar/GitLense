from datetime import datetime, timezone
from sqlalchemy.orm import Session
import uuid

from app.models.db import Job, Repo, UserRepo
from app.core.database import SessionLocal
from app.core.logger import get_logger
from app.services.github_fetcher import fetch_repo_files
from app.services.code_parser import parse_files
from app.services.embedder import embed_chunks
from app.services.vector import store_embeddings

logger = get_logger(__name__)


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

        # ── Mark started ──────────────────────────────────
        job.status     = "started"
        job.started_at = datetime.now(timezone.utc)
        repo.status    = "processing"
        db.commit()
        logger.info(f"Ingestion started for repo: {repo.name}")

        # ── Fetch ─────────────────────────────────────────
        files = fetch_repo_files(repo.repo_url)
        if not files:
            raise Exception("No files fetched from repo")
        logger.info(f"Fetched {len(files)} files")
        job.progress = 25
        db.commit()

        # ── Parse ─────────────────────────────────────────
        chunks = parse_files(files)
        if not chunks:
            raise Exception("Failed to parse files")
        logger.info(f"Parsed {len(chunks)} chunks")
        job.progress = 50
        db.commit()

        # ── Embed ─────────────────────────────────────────
        embedded_chunks = embed_chunks(chunks=chunks)
        if not embedded_chunks:
            raise Exception("Failed to embed chunks")
        logger.info(f"Embedded {len(embedded_chunks)} chunks")
        job.progress = 75
        db.commit()

        # ── Store ─────────────────────────────────────────
        amnt_embedded = store_embeddings(repo_id=str(repo.id), chunks=embedded_chunks)
        if not amnt_embedded:
            raise Exception("Failed to store embeddings")
        logger.info(f"Stored {amnt_embedded} embeddings")
        job.progress = 100
        db.commit()

        # ── Success ───────────────────────────────────────
        db.add(UserRepo(user_id=uuid.UUID(user_id), repo_id=uuid.UUID(repo_id)))
        job.status          = "finished"
        job.completed_at    = datetime.now(timezone.utc)
        repo.status         = "completed"
        repo.chunks_indexed = amnt_embedded
        db.commit()
        logger.info(f"✅ Ingestion complete for repo: {repo.name} | {amnt_embedded} chunks")

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