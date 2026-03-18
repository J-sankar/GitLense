from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.db import Repo,UserRepo
from app.core.database import get_db
from app.schemas.repo import RepoResponse
from app.core.logger import get_logger
import uuid

logger = get_logger(__name__)

router = APIRouter(prefix='/repos',tags=["Repos"])

TEST_USER_ID = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


@router.get(path='/', response_model=list[RepoResponse])
def get_repos(
    db:Session = Depends(get_db)
):
    try:
        logger.debug("fetching user repos....")
        user_repos = db.query(UserRepo).filter(UserRepo.user_id == TEST_USER_ID).all()

        repos = db.query(Repo).filter(Repo.id.in_([repo.repo_id for repo in user_repos])).all()
        logger.info(f"Fetched repos count: {len(repos)}")
        if len(user_repos) == 0:
            raise HTTPException(status_code=200, detail='No repo found')
        return [RepoResponse(id=str(repo.id), name=repo.name, url=repo.repo_url,status=repo.status,chunks_indexed=repo.chunks_indexed,created_at=repo.created_at,error=repo.error_message) for repo in repos]
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail='Internal Server Error')

        
        