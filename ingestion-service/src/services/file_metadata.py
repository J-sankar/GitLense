from sqlalchemy import select, update, func
from src.models.db import FileMetaData, Repo
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from typing import List, Optional
from uuid import UUID
from src.core.logger import get_logger

logger = get_logger(__name__)


async def upsert_file_metadata(
    db: Session,
    repo_id: UUID,
    file_path: str,
    file_hash: str,
    imports: List[str],
    exports: List[str],
    summary: Optional[str] = None,
    skeleton=List[str],
) -> None:
    try:
        stmnt = insert(FileMetaData).values(
            file_path=file_path,
            file_hash=file_hash,
            repo_id=repo_id,
            imports=imports,
            exports=exports,
            summary=summary,
            skeleton=skeleton,
            status="completed",
        )

        update_stmnt = stmnt.on_conflict_do_update(
            index_elements=["repo_id", "file_path"],
            set_={
                "file_hash": file_hash,
                "imports": imports,
                "exports": exports,
                "summary": summary,
                "skeleton": skeleton,
                "status": "completed",
                "updated_at": func.now(),
                },
        )

        await db.execute(update_stmnt)
        await db.commit()
        logger.info("Successfully upserted file metadata")
    except Exception as e:
        await db.rollback()
        error = str(e).lower()
        logger.error(f"Error: {error}")
        raise e



async def update_file_and_repo_chunks(db, repo_uuid, file_path: str, chunk_count: int):
   
    result = await db.execute(
        select(FileMetaData)
        .where(FileMetaData.repo_id == repo_uuid)
        .where(FileMetaData.file_path == file_path)
    )
    file_record = result.scalar_one_or_none()

    if file_record:
        
        file_record.chunks_indexed = chunk_count
    else:
      
        new_file = FileMetaData(
            repo_id=repo_uuid,
            file_path=file_path,
            chunks_indexed=chunk_count
        )
        db.add(new_file)
        
  
    await db.flush()

    sum_query = select(func.coalesce(func.sum(FileMetaData.chunks_indexed), 0)).where(
        FileMetaData.repo_id == repo_uuid
    )
    total_repo_chunks = await db.scalar(sum_query)

    await db.execute(
        update(Repo)
        .where(Repo.id == repo_uuid)
        .values(chunks_indexed=total_repo_chunks)
    )