from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException,Request,Depends,status
from sqlalchemy.orm import Session
from app.core.database import get_db

from app.models.db import Repo,UserRepo,Job,User
from app.core.limiter import limiter
from app.core.logger import get_logger
from app.core.security import get_current_user
from app.schemas.ingest import IngestRequest,IngestResponse
from app.utils.github import parse_repo_name
from app.utils.validators import validate_repo_url
from app.core.queue import queue_ingestion
logger = get_logger(__name__)

router = APIRouter()

@router.post("", response_model=IngestResponse)
@limiter.limit("10/minute")
def ingest_repo(
    payload:      IngestRequest,
    request: Request,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    
    user_id = current_user.id
    repo_url = payload.repo_url
    if not validate_repo_url(repo_url):
        raise HTTPException(400, "Invalid GitHub URL")

    try:

        existing_repo = db.query(Repo).filter(Repo.repo_url == repo_url).first()

        if not existing_repo:
            repo_name = parse_repo_name(payload.repo_url)
            logger.info(f"Creating new Repo: {repo_name}")
            repo = Repo(repo_url=repo_url,name=repo_name,status="queued")
            db.add(repo)
            db.flush()

            db.add(UserRepo(user_id=user_id,repo_id=repo.id))
            job = Job(repo_id=repo.id,status = "queued",started_at=datetime.now(timezone.utc))
            db.add(job)
            logger.info(f"User {str(user_id)[:8]} linked to repo {str(repo.id)[:8]}")
            db.commit()
            queue_ingestion(repo_url=repo_url,job_id=str(job.id),repo_id=str(repo.id))
            logger.info(f"Job Scheduled for ingestion, job:{job.id}")
            return IngestResponse(job_id=job.id, repo_id=repo.id, status=repo.status, message="New job scheduled for ingestion")
        
        logger.info(f"Repo already exists: {existing_repo.name}")
        latest_job = db.query(Job).filter(
            Job.repo_id == existing_repo.id
        ).order_by(Job.started_at.desc()).first()

        already_linked = db.query(UserRepo).filter(UserRepo.user_id== user_id, UserRepo.repo_id == existing_repo.id).first()

        if not already_linked:
            logger.info(f"Linking user to repo: {str(existing_repo.id)[:8]}")
            user_repo = UserRepo(user_id=user_id, repo_id = existing_repo.id)
            db.add(user_repo)
            db.commit()
            logger.info(f"user {str(user_id)[:8]} linked to repo {str(existing_repo.id)[:8]}")
        
        logger.info(f"user {str(user_id)[:8]} already linked to repo {str(existing_repo.id)[:8]}")
        if existing_repo.status in ("queued", "processing","completed"):
            return IngestResponse(
                job_id=latest_job.id if latest_job else None,
                repo_id=existing_repo.id,
                status=existing_repo.status,
                message="Already Linked" if existing_repo.status == "completed" else "Ingestion in Progress"
            )
        new_job = Job(repo_id=existing_repo.id,status = "queued",started_at=datetime.now(timezone.utc))
        db.add(new_job)
        existing_repo.status = "queued"
        db.commit()
        queue_ingestion(repo_url=existing_repo.repo_url,job_id=str(new_job.id),repo_id=str(existing_repo.id))
        logger.info(f"New job scheduled for repo {str(existing_repo.id)[:8]}")
        return IngestResponse(job_id=new_job.id, repo_id=existing_repo.id,status=existing_repo.status,message="job scheduled")
    except Exception as e:
        db.rollback()
        logger.error(f"CRITICAL: Ingestion API failure: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e).lower())

        

