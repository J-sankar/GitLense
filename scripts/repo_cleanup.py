from app.core.database import SessionLocal
from app.core.logger import get_logger
from app.models.db import UserRepo,Job,Repo,FileMetaData,Query
from app.services.vector import delete_embeddings
from uuid import UUID

logger = get_logger(__name__)

def clear_repo( repo_id : str):
    db = SessionLocal()
    try:
        repo = db.query(Repo).filter(Repo.id == UUID(repo_id)).first()
        if not repo:
            logger.error("Repo not found")
            return 
        
        logger.info("Cleaning repo data....")
        delete_embeddings(repo_id=repo_id)
        logger.info("Deleted Embeddings...")
        db.query(Job).filter(Job.repo_id == repo.id).delete()
        logger.info("Deleted Jobs...")

        db.query(Query).filter(Query.repo_id == repo.id).delete()
        logger.info("Deleted Query History...")
        db.query(UserRepo).filter(UserRepo.repo_id == repo.id).delete()
        logger.info("Deleted User Repos...")

        db.query(FileMetaData).filter(FileMetaData.repo_id == repo.id).delete()
        logger.info("Deleted File Metadata...")

        db.delete(repo)
        db.commit()
        logger.info("Success:Deleted Repo")
    except Exception as e:
        db.rollback()
        logger.error(str(e))
        
    finally:
        db.close()
        return 
    

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        clear_repo(sys.argv[1])
    else:
        print("Please provide a repo_id")






