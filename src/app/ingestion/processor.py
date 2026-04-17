from sqlalchemy.orm import Session
from typing import List
from app.core.logger import get_logger
from app.models.db import Job,FileMetaData, Repo
from app.services.code_parser import parse_files
from app.services.embedder import embed_batch
from app.services.vector import store_embeddings_batch
from app.services.file_metadata import upsert_file_metadata
from app.utils.crypto import get_file_hash,get_deterministic_id
from app.services.summarizer import Summarizer
from app.parser.parser_manager import ParserManager
import time

logger = get_logger(__name__)
MAX_ATTEMPTS  = 3
WAIT_TIME = 10
summarizer = Summarizer()

async def process_repository(db:Session, repo:Repo, job:Job, files: List[dict]) :

    total_files = len(files)

    db.refresh(repo)
    db.refresh(job)

    if repo.status == "completed":
        logger.info("Repo ingestion complete, exiting...")
        return 

    if not job:
        logger.error(f"CRITICAL: Job {str(job.id)} not found. Ingestion aborted.")
        return
    
    logger.info(f"starting processor for job: {str(job.id)[:8]} | total files found : {total_files}")

    for index, file in enumerate(files):
        content = file["content"]
        file_hash = get_file_hash(content)
        file_path = file["path"]
        language = file["language"]
        file_summary = ""

        existingFile = db.query(FileMetaData).filter(FileMetaData.file_path == file_path, FileMetaData.repo_id == repo.id).first()

        if existingFile and existingFile.file_hash == file_hash and existingFile.status == "completed":
            logger.info(f"Skipping file : {file_path} | already processed")
            _update_progress(db,job,index,total=total_files)
            continue 

        logger.info(f"Processing file: {file_path}")

        

        try:
                parser = ParserManager()

                file_data =parser.extract_chunks(file_path=file_path,content=content,language=language)
                

                chunks = file_data["chunks"]
                metadata = file_data.get("metadata", [])
                

                if metadata: 
                    file_summary = await _generate_summary(metadata=metadata)

                if chunks:
                    for chunk in chunks:
                        chunk["point_id"] = get_deterministic_id(filename=file_path,code=chunk["code"])
    
        

                logger.info(f"obtained {len(chunks)} chunks from file")

                embedded_chunks  = embed_batch(chunks=chunks)
                logger.info(f"embedded {len(chunks)} chunks from file")
                stored_embeddings = store_embeddings_batch(repo_id=str(repo.id),chunks=embedded_chunks)
            
                logger.info(f"stored {stored_embeddings} embeddings from file")

                upsert_file_metadata(db=db,repo_id=repo.id,file_path=file_path, file_hash=file_hash,imports=metadata.get("imports", []), exports=metadata.get("exports", []), summary=file_summary,skeleton=metadata.get("skeleton",[]))
                repo.chunks_indexed += stored_embeddings
                db.commit()
                db.refresh(repo)
                _update_progress(db,job,index,total_files)

        except Exception as e:
            # If we are here, it means the modular retries (MAX_ATTEMPTS) failed.
                error_msg = f"Failed to process {file_path}: {str(e)}"
                logger.error(error_msg)
                
                # Update job status so the UI knows it 
                job.error_message = error_msg
                db.commit()
                raise Exception(error_msg)




def _update_progress(db: Session, job: Job, current_index: int, total: int):
    """Internal helper to keep the UI progress bar moving."""
    if job:
        progress = int(((current_index + 1) / total) * 100)
        if progress > job.progress:
            job.progress = progress
            db.commit()
            db.refresh(job)






async def _generate_summary(metadata:dict):
    
    try:
        summary = await summarizer.summarize_file(metadata=metadata)
        return summary
    except Exception as e :
        logger.error(f"Failed to generate summary for {metadata.get('path')}: {str(e).lower()}")
        return "Summary unavailable"





