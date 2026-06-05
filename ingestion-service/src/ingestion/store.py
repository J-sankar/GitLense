from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.file import Payload
from src.models.db import Job, Repo
from src.core.logger import get_logger
from src.services.vector import store_embeddings_batch
from src.services.file_metadata import upsert_file_metadata

import uuid
logger = get_logger(__name__)




async def store_filedata(db:AsyncSession, repo:Repo, job:Job, file:Payload) -> tuple[int, bool]:
    await db.refresh(repo)
    await db.refresh(job)

    if repo.status == "completed":
        logger.info("Repo ingestion complete, exiting...")
        return 0,True

   
    
    logger.info(f"starting file store for job: {str(job.id)[:8]} | repo: {repo.repo_url} | file: {file.file_path} ")

    try:
        result = await store_embeddings_batch(file.repo_id, file.embedded_chunks)
        logger.info(f"Stored {result} vectors for repo:{repo.repo_url}| file: {file.file_path}")
        metadata = file.file_metadata

        await upsert_file_metadata(db,repo_id=uuid.UUID(file.repo_id),file_path=metadata.file_path,file_hash=metadata.file_hash,
                                imports=metadata.imports,exports=metadata.exports,summary=metadata.summary,
                                skeleton=metadata.skeleton)
        logger.info(f"Stored metadata for repo: {repo.repo_url} | file: {file.file_path}")
        
        
        return result,True
    except Exception as e:
        logger.error(f"Failed to store file {file.file_path}: {str(e).lower()}")
        raise
