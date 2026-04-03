from sqlalchemy.orm import Session
from typing import List
from app.core.logger import get_logger
from app.models.db import Job,FileMetaData
from app.services.code_parser import parse_files
from app.services.embedder import embed_batch
from app.services.vector import store_embeddings_batch
from app.services.file_metadata import upsert_file_metadata
from app.utils.crypto import get_file_hash,get_deterministic_id
from uuid import UUID
import time

logger = get_logger(__name__)
MAX_ATTEMPTS  = 3
WAIT_TIME = 60

def process_repository(db:Session,repo_id:str, job_id:str, files: List[dict]) :

    total_files = len(files)
    job = db.query(Job).filter(Job.id == UUID(job_id)).first()

    if not job:
        logger.error(f"CRITICAL: Job {job_id} not found. Ingestion aborted.")
        return
    
    logger.info(f"starting processor for job: {job_id[:8]} | total files found : {total_files}")

    for index, file in enumerate(files):
        content = file["content"]
        file_hash = get_file_hash(content)
        file_path = file["path"]
        file_summary = ""

        existingFile = db.query(FileMetaData).filter(FileMetaData.file_path == file_path, FileMetaData.repo_id == UUID(repo_id)).first()

        if existingFile and existingFile.file_hash == file_hash and existingFile.status == "completed":
            logger.info(f"Skipping file : {file_path} | already processed")
            _update_progress(db,job,index,total=total_files)
            continue 

        logger.info(f"Processing file: {file_path}")
        success = False
        for attempt in range(MAX_ATTEMPTS):

            try:
                file_data = parse_files([file])

                chunks = file_data["chunks"]
                metadata_list = file_data.get("metadata", [])
                metadata = metadata_list[0] if metadata_list else {}

                if metadata: 
                    file_summary = _generate_summary(metadata=metadata)

                if chunks:
                    for chunk in chunks:
                        chunk["point_id"] = get_deterministic_id(filename=file_path,code=chunk["code"])
    
        

                logger.info(f"-----obtained {len(chunks)} chunks from file")

                embedded_chunks  = embed_batch(chunks=chunks)
                logger.info(f"-----embedded {len(chunks)} chunks from file")
                stored_embeddings = store_embeddings_batch(repo_id=repo_id,chunks=embedded_chunks)
                logger.info(f"-----stored {stored_embeddings} embeddings from file")

                success = True
                break
            except Exception as e:
                error_msg = str(e).lower()

                if "rate limit" in error_msg or "429" in error_msg or "quota" in error_msg:
                    logger.warning(f"Rate limit hit on {file_path} (Attempt {attempt + 1}/{MAX_ATTEMPTS})")
                    
                    if attempt < MAX_ATTEMPTS - 1:
                        time.sleep(WAIT_TIME)
                        continue
                    else:
                        raise Exception(f"Rate limit exceeded after {MAX_ATTEMPTS} attempts on file: {file_path}")
                else:
                    raise e
        
        if success:
            upsert_file_metadata(db=db,repo_id=UUID(repo_id),file_path=file_path, file_hash=file_hash,imports=metadata.get("imports", []), exports=metadata.get("exports", []), summary=file_summary)
            _update_progress(db,job,index,total_files)
        else:
            raise Exception(f"failed to process {file_path} completely")



def _update_progress(db: Session, job: Job, current_index: int, total: int):
    """Internal helper to keep the UI progress bar moving."""
    if job:
        progress = int(((current_index + 1) / total) * 100)
        if progress > job.progress:
            job.progress = progress
            db.commit()






def _generate_summary(metadata:dict):
    return f"""this is a code with import statements {metadata.get("imports",[])}, and file {metadata["path"]}"""





