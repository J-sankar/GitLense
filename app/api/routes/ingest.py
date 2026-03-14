from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.redis import ingest_queue
from app.core.logger import get_logger
from app.models.db import Repo, Job, UserRepo
from app.schemas.ingest import IngestResponse, IngestRequest
from app.services.github_fetcher import parse_repo_name
from app.tasks.ingest_task import run_ingestion
# from app.tasks.ingest_task import run_ingestion
import uuid

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# ── Hardcoded test user until auth is ready ───────────
TEST_USER_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


@router.post("/", response_model=IngestResponse)
def ingest_repo(
    payload: IngestRequest,
    db: Session = Depends(get_db),
):
    if not ingest_queue:
        logger.warning("Ingestion queue unavailable")
        raise HTTPException(503, "Queue service unavailable")

    repo = db.query(Repo).filter(Repo.repo_url == payload.repo_url).first()

    if repo:
        logger.info("Repo found")
        already_linked = db.query(UserRepo).filter(
            UserRepo.user_id == TEST_USER_ID,
            UserRepo.repo_id == repo.id
        ).first()

        latest_job = db.query(Job).filter(
            Job.repo_id == repo.id
        ).order_by(Job.created_at.desc()).first()

        if already_linked:
            if repo.status == "completed":
                return IngestResponse(
                    job_id=latest_job.id,
                    repo_id=repo.id,
                    status=repo.status,
                    message="Repo already linked to your account"
                )
            if repo.status in ("queued", "processing"):
                return IngestResponse(
                    job_id=latest_job.id,
                    repo_id=repo.id,
                    status=repo.status,
                    message="Repo is already being ingested"
                )

            if repo.status == "failed":
                repo.status        = "queued"   # ✅ no trailing comma
                repo.error_message = None
                new_job = Job(repo_id=repo.id, status="queued", progress=0)
                db.add(new_job)
                db.commit()
                logger.info(f"Repo re-enqueued, job id: {new_job.id}")
                ingest_queue.enqueue(run_ingestion, str(new_job.id), str(repo.id), str(TEST_USER_ID), job_timeout=600)
                return IngestResponse(        # ✅ return here
                    job_id=new_job.id,
                    repo_id=repo.id,
                    status="queued",
                    message="Re-ingestion started"
                )
        else:
            ingest_queue.enqueue(run_ingestion, str(latest_job.id), str(repo.id), str(TEST_USER_ID), job_timeout=600)
            return IngestResponse(        # ✅ return here
                job_id=latest_job.id,
                repo_id=repo.id,
                status="queued",
                message="Re-ingestion started"
            )


    # ── Fresh repo ────────────────────────────────────
    repo_name = parse_repo_name(payload.repo_url)
    new_repo  = Repo(name=repo_name, repo_url=payload.repo_url, status="queued")
    db.add(new_repo)
    db.flush()                             # ✅ get new_repo.id before commit

    new_job = Job(repo_id=new_repo.id, status="queued", progress=0)  # ✅ progress not status
    db.add(new_job)
    db.commit()

    logger.info(f"Job scheduled, job id: {new_job.id}")
    ingest_queue.enqueue(run_ingestion, str(new_job.id), str(new_repo.id), str(TEST_USER_ID), job_timeout=600)

    return IngestResponse(
        job_id=new_job.id,
        repo_id=new_repo.id,
        status="queued",
        message="Ingestion started"
    )