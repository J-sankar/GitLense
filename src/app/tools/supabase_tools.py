from app.core.database import SessionLocal
from app.core.logger import get_logger
from app.models.db import Repo,FileMetaData
from sqlalchemy import select
from uuid import UUID
from typing import List

logger = get_logger(__name__)

def list_repo_files(repo_id:str) ->List[str]:
    logger.info(f"Tool call: list repo files (repo: ${repo_id[:8]})")
    db = SessionLocal()
    try :
        results = db.query(FileMetaData.file_path).filter(FileMetaData.repo_id == UUID(repo_id)).all()
        if not results:
            logger.info("No match found")
            return []
        repo_files = [row[0] for row in results]
        logger.info(f"Obtained repo files: {len(repo_files)}")
        return repo_files
    except Exception as e:
        raise Exception(f"ERROR in tool call (list repo files) : {str(e).lower()}")
    
    

def get_file_metadata(repo_id:str, file_path:str) ->dict:

    logger.info(f"Tool call: get file metadata (repo: ${repo_id[:8]}, filepath: {file_path})")
    with SessionLocal() as db:
        try:
            stmnt = select(FileMetaData.imports,FileMetaData.exports,FileMetaData.skeleton,FileMetaData.summary).where(Repo.id == UUID(repo_id), FileMetaData.file_path == file_path)
            file_data = db.execute(stmnt).first()
            if not file_data:
                logger.inf("No match found")
                return {"error": f"No data found for {file_path}"}
            logger.info(f"Obtained file_data for file {file_path} in repo: {repo_id[:8]}")
            return dict(file_data._mapping)
        except Exception as e:
            raise Exception(f"ERROR in tool call (list repo files) : {str(e).lower()}")
            

def get_all_metadata(repo_id:str) ->List[dict]:
    logger.info(f"Tool call: get all metadata (repo_id: ${repo_id[:8]})")
    with SessionLocal() as db:
        try:
            stmnt = select(FileMetaData.file_path,FileMetaData.imports,FileMetaData.exports,FileMetaData.skeleton,FileMetaData.summary).where(FileMetaData.repo_id == UUID(repo_id))
            result = db.execute(stmnt).all()
            if not result:
                logger.info("No match found")
                return []
            metadata = [
                dict(data._mapping) for data in result
            ]
            return metadata
        except Exception as e:
            raise Exception(f"ERROR in tool call (get all metadata) : {str(e).lower()}")


def get_summaries(repo_id:str, query:str)->List[dict]:
    logger.info(f"Tool call: get  summaries (repo_id: ${repo_id[:8]}, query: ${query})")
    with SessionLocal() as db:
        try:
            stmnt = select(FileMetaData.file_path,FileMetaData.summary).where(FileMetaData.repo_id == UUID(repo_id),FileMetaData.summary.ilike(f"%{query}%")).limit(10)
            result = db.execute(stmnt).all()
            if not result:
                logger.info("No match found")
                return []
            metadata = [
                dict(data._mapping) for data in result
            ]
            logger.debug(metadata)
            return metadata
        except Exception as e:
            raise Exception(f"ERROR in tool call (get  summmaries) : {str(e).lower()}")





if __name__ == "__main__":
    get_summaries(repo_id="9d87b3c0-c72f-4a69-994c-620d0fbdd447", query="auth")