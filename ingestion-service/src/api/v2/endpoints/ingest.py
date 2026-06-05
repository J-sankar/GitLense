from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException,Request,Depends,status
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db
from sqlalchemy import select
from src.models.db import Repo,UserRepo,Job
from src.core.limiter import limiter
from src.core.logger import get_logger
from src.core.security import get_current_user
from src.schemas.ingest import IngestRequest,IngestResponse  
from src.utils.github import parse_repo_name
from src.utils.validators import validate_repo_url
from src.core.redis import redis_manager,STREAM_REPO_FETCH
from src.utils.progress import get_progress
from sse_starlette import EventSourceResponse
import uuid
import asyncio
import json
logger = get_logger(__name__)

router = APIRouter()

@router.post("", response_model=IngestResponse)
@limiter.limit("10/minute")
async def ingest_repo(
    payload:      IngestRequest,
    request: Request,
    db:           AsyncSession = Depends(get_db),
    # current_user: User    = Depends(get_current_user)
):
    
    user_id = uuid.UUID("e8daa55f-49c8-495b-8ff1-8c8c88976269")
    repo_url = payload.repo_url
    if not validate_repo_url(repo_url):
        raise HTTPException(400, "Invalid GitHub URL")

    try:

        repo_res = await db.execute(select(Repo).where(Repo.repo_url == repo_url))

        existing_repo = repo_res.scalar_one_or_none()

        if not existing_repo:
            owner, repo_name = parse_repo_name(payload.repo_url)
            logger.info(f"Creating new Repo: {repo_name}")
            repo = Repo(repo_url=repo_url,name=repo_name,status="queued")
            db.add(repo)
            await db.flush()

            db.add(UserRepo(user_id=user_id,repo_id=repo.id))
            job = Job(repo_id=repo.id,status = "queued",started_at=datetime.now(timezone.utc))
            db.add(job)
            logger.info(f"User {str(user_id)[:8]} linked to repo {str(repo.id)[:8]}")
            await db.commit()
            stream_payload = {
                "repo_url": repo_url,
                "job_id": str(job.id),
                "repo_id": str(repo.id),
                "retries": "0"
                
            }
            await redis_manager.publish(STREAM_REPO_FETCH,payload=stream_payload)
            logger.info(f"Job Scheduled for ingestion, job:{job.id}")
            return IngestResponse(job_id=job.id, repo_id=repo.id, status=repo.status, message="New job scheduled for ingestion")
        
        logger.info(f"Repo already exists: {existing_repo.name}")
        
        already_exists = await db.execute(select(UserRepo).where(UserRepo.user_id == user_id, UserRepo.repo_id == existing_repo.id))
        already_linked = already_exists.scalar_one_or_none()

        if not already_linked:
            logger.info(f"Linking user to repo: {str(existing_repo.id)[:8]}")
            user_repo = UserRepo(user_id=user_id, repo_id = existing_repo.id)
            db.add(user_repo)
            await db.commit()
            logger.info(f"user {str(user_id)[:8]} linked to repo {str(existing_repo.id)[:8]}")
        
        logger.info(f"user {str(user_id)[:8]} already linked to repo {str(existing_repo.id)[:8]}")
        if existing_repo.status in ("queued","fetching", "processing","storing","completed"):

            logger.debug(f"Repo status: {existing_repo.status}")
            
            latest_job_res = await db.execute(select(Job).where(Job.repo_id == existing_repo.id).order_by(Job.started_at.desc()))
            latest_job = latest_job_res.scalar_one_or_none()
            progress = await get_progress(str(latest_job.id))
            if progress:
                logger.info("Progress obtained")
                return IngestResponse(
                job_id=latest_job.id ,
                repo_id=existing_repo.id,
                status=latest_job.status, 
                progress=progress.get("progress", 0),
                message="Already Linked" if existing_repo.status == "completed" else "Ingestion in Progress"
            )
        
            return IngestResponse(
                job_id=latest_job.id if latest_job else None,
                repo_id=existing_repo.id,
                status=existing_repo.status,
                progress=latest_job.progress,
                message="Already Linked" if existing_repo.status == "completed" else "Ingestion in Progress"
            )
        new_job = Job(repo_id=existing_repo.id,status = "queued",started_at=datetime.now(timezone.utc))
        db.add(new_job)
        existing_repo.status = "queued"
        await db.commit()
        data = {
            "repo_url": repo_url,
                "job_id": str(new_job.id),
                "repo_id": str(existing_repo.id),
                "retries": "0"
        }
        await redis_manager.publish(STREAM_REPO_FETCH, payload=data)
        logger.info(f"New job scheduled for repo {str(existing_repo.id)[:8]}")
        return IngestResponse(job_id=new_job.id, repo_id=existing_repo.id,status=existing_repo.status,message="job scheduled", progress=new_job.progress)
    except Exception as e:
        await db.rollback()
        logger.error(f"CRITICAL: Ingestion API failure: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e).lower())

        
@router.get(path='/stream/{job_id}')
async def stream_job_status(
    job_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    async def event_generator():
        while True:
            # 1. Prevent infinite loops if the user closes their browser!
            if await request.is_disconnected():
                logger.info(f"Client disconnected. Stopping SSE for job {job_id}")
                break

            try:
                # 2. FIXED: Typo in uuid.UUID
                try:
                    job_uuid = uuid.UUID(job_id)
                except ValueError:
                    yield {"event": "error", "data": json.dumps({"error": "Invalid Job ID format"})}
                    break

                job_res = await db.execute(select(Job).where(Job.id == job_uuid))
                job = job_res.scalar_one_or_none()

                # 3. FIXED: Added break so it doesn't crash on the next line
                if not job:
                    logger.error(f"ERROR: Job id {job_id} not found")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": "Job Not Found"})
                    }
                    break

                # 4. FIXED: Added await
                await db.refresh(job)

                repo_res = await db.execute(select(Repo).where(Repo.id == job.repo_id))
                repo = repo_res.scalar_one_or_none()

                # 5. Get the ultra-fast progress from Redis
                redis_progress = await get_progress(job_id)
                
                # Combine DB truth with Redis speed
                current_progress = redis_progress.get("progress", 0) if redis_progress else job.progress

                payload = {
                    "job_id": str(job.id),
                    "status": job.status,
                    "progress": current_progress, # Use the fast Redis number!
                    "error": job.error_message,
                    "repo_status": repo.status if repo else None
                }

                logger.info(f"SSE [{job_id[:8]}...] status={job.status} progress={current_progress}%")

                yield {
                    "event": "update",
                    "data":  json.dumps(payload)
                }

                # 6. Stop polling if we are done
                if job.status in ('completed', 'failed'):
                    yield {
                        "event": "done",
                        "data":  json.dumps(payload)
                    }
                    break

                db.expire_all()
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"SSE ERROR: {str(e)}")
                yield {
                    "event": "error",
                    "data":  json.dumps({"error": str(e)})
                }
                break

    return EventSourceResponse(event_generator())