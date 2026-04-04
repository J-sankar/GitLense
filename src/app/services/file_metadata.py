from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from typing import List,Optional
from uuid import UUID
from app.models.db import FileMetaData
from sqlalchemy.sql import func
from app.core.logger import get_logger

logger = get_logger(__name__)


def upsert_file_metadata(db: Session, repo_id: UUID, file_path: str, file_hash: str, imports: List[str], exports:List[str], summary: Optional[str] = None,skeleton=List[str]) ->None:
    try:
        stmnt = insert(FileMetaData).values(
            file_path = file_path,
            file_hash = file_hash,
            repo_id = repo_id,
            imports = imports,
            exports = exports,
            summary = summary,
            skeleton = skeleton,
            status = "completed"
        )

        update_stmnt = stmnt.on_conflict_do_update(
            index_elements=["repo_id","file_path"],
            set_= {
                "file_hash" : file_hash,
                "imports": imports,
                "exports": exports,
                "summary": summary,
                "skeleton":skeleton,
                "status": "completed",
                "updated_at": func.now()

            }
        )

        db.execute(update_stmnt)
        db.commit()
        logger.info("Successfully upserted file metadata")
    except Exception as e :
        db.rollback()
        error = str(e).lower()
        logger.error(f"Error: {error}")
        raise e 
    