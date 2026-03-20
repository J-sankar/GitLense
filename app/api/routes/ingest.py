from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.logger import get_logger
from app.models.db import Repo, Job, UserRepo,User
from app.schemas.ingest import IngestResponse, IngestRequest
from app.services.github_fetcher import parse_repo_name


from app.core.queue import queue_ingestion
from app.utils.validators import validate_repo_url
from sse_starlette import EventSourceResponse
import uuid
import asyncio
import json

logger = get_logger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"],dependencies=[Depends(get_current_user)])


@router.post("/", response_model=IngestResponse)
def ingest_repo(
    payload: IngestRequest,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    
    if not validate_repo_url(payload.repo_url) :
        raise HTTPException(400, "Invalid GitHub URL")
    repo = db.query(Repo).filter(Repo.repo_url == payload.repo_url).first()

    if repo:
        logger.info("Repo found")
        already_linked = db.query(UserRepo).filter(
            UserRepo.user_id == current_user.id,
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
            if repo.status in ("queued", "processing","storing"):
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
                queue_ingestion(repo_url=repo.repo_url, job_id=str(new_job.id), repo_id=str(repo.id),user_id=str(current_user.id))
                return IngestResponse(        # ✅ return here
                    job_id=new_job.id,
                    repo_id=repo.id,
                    status="queued",
                    message="Re-ingestion started"
                )
        else:
            
            
            logger.debug("Repo not linked")
            logger.debug(f"Repo status: {repo.status}")
            if repo.status == "completed":
                return IngestResponse(
                    job_id  = latest_job.id,
                    repo_id = repo.id,
                    status  = "completed",
                    message = "Repo already ingested, linking to your account"
                )

            if repo.status in ("queued","processing","storing"):
                return IngestResponse(
                    job_id  = latest_job.id,
                    repo_id = repo.id,
                    status  = repo.status,
                    message = "Repo being ingested, you'll get access when done"
                )

            if repo.status == "failed":
                repo.status        = "queued"
                repo.error_message = None
                new_job = Job(repo_id=repo.id, status="queued", progress=0)
                db.add(new_job)
                db.commit()
                queue_ingestion(
                    repo_url = repo.repo_url,
                    job_id   = str(new_job.id),
                    repo_id  = str(repo.id),
                    user_id  = str(current_user.id)
                )
                return IngestResponse(
                    job_id  = new_job.id,
                    repo_id = repo.id,
                    status  = "queued",
                    message = "Re-ingestion started"
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
    queue_ingestion(repo_url=new_repo.repo_url, job_id=str(new_job.id), repo_id=str(new_repo.id), user_id=str(current_user.id))

    return IngestResponse(
        job_id=new_job.id,
        repo_id=new_repo.id,
        status="queued",
        message="Ingestion started"
    )


@router.get(path='/stream/{job_id}')
async def stream_job_status(
    job_id:str,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)):
    async def event_generator():
        while True:
            try:
                job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()

                if not job:
                    logger.error(f"ERROR: Job id {job_id} not found")
                    yield {
                        "event": "error",
                        "data": json.dumps({"ERROR":"Job Not Found"})
                    }

                repo = db.query(Repo).filter(Repo.id == job.repo_id).first()

                payload = {
                    "job_id":str(job.id),
                    "status":job.status,
                    "progress":job.progress,
                    "error":job.error_message,
                    "repo_status": repo.status  if repo else None
                }

                logger.info(
                    f"SSE [{job_id[:8]}...] "
                    f"status={job.status} "
                    f"progress={job.progress}%"
                )

                yield {
                    "event": "update",
                    "data":  json.dumps(payload)
                }

                if job.status in ('finished','failed'):
                    yield {
                        "event": "done",
                        "data":  json.dumps(payload)
                    }
                    break

                db.expire_all()

                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"ERROR: {str(e)}")
                yield {
                    "event": "error",
                    "data":  json.dumps({"error": str(e)})
                }
                break
    return EventSourceResponse(event_generator())