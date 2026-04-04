from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session
from app.models.db import Repo,UserRepo,User
from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.repo import RepoResponse
from app.core.logger import get_logger
from app.core.limiter import limiter


logger = get_logger(__name__)

router = APIRouter()



@router.get(path="", response_model=list[RepoResponse])
@limiter.limit("60/minute")
def get_repos(
    request:Request,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    try:
        logger.debug("fetching user repos....")
        user_repos = db.query(UserRepo).filter(UserRepo.user_id == current_user.id).all()

        repos = db.query(Repo).filter(Repo.id.in_([repo.repo_id for repo in user_repos])).all()
        logger.info(f"Fetched repos count: {len(repos)}")
        for repo in repos:
            if repo.status == "completed":
                repo.error_message is None
                db.commit()
        return [RepoResponse(id=str(repo.id), name=repo.name, url=repo.repo_url,status=repo.status,chunks_indexed=repo.chunks_indexed,created_at=repo.created_at,error=repo.error_message) for repo in repos]
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail='Internal Server Error')

        
        