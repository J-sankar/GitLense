from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.logger import get_logger
from src.models.db import Job,FileMetaData, Repo
from src.services.embedder import embed_batch
from src.utils.crypto import get_file_hash,get_deterministic_id
from src.services.summarizer import Summarizer
from src.parser.parser_manager import ParserManager
from src.schemas.file import FileUpload
import asyncio
import json


     

logger = get_logger(__name__)
MAX_ATTEMPTS  = 3
WAIT_TIME = 10
summarizer = Summarizer()

async def process_file(db:AsyncSession, repo:Repo, job:Job, file:FileUpload ) :

    
        
        await db.refresh(repo)
        await db.refresh(job)

        if repo.status == "completed":
            logger.info("Repo ingestion complete, exiting...")
            return 

        if not job:
            logger.error(f"CRITICAL: Job {str(job.id)} not found. Ingestion aborted.")
            return
    
        logger.info(f"starting processor for job: {str(job.id)[:8]} | file: {file.file_path} ")

        
        content = file.content
        file_hash = get_file_hash(content)
        file_path = file.file_path
        language = file.language
        file_summary = ""
            
        existingFile_result = await db.execute(select(FileMetaData).where(FileMetaData.file_path == file_path, FileMetaData.repo_id == repo.id))
        existingFile = existingFile_result.scalar_one_or_none()

        if existingFile and existingFile.file_hash == file_hash and existingFile.status == "completed":
            logger.info(f"Skipping file : {file_path} | already processed")
            return None
            

        logger.info(f"Processing file: {file_path}")

        

        try:
                parser = ParserManager()
                loop = asyncio.get_event_loop()
                file_data = await loop.run_in_executor(None, parser.extract_chunks, file_path,content,language)
                

                chunks = file_data["chunks"]
                if not chunks:
                    logger.warning(f"No chunks found for {file_path}")
                    return None 
                metadata = file_data.get("metadata", {})
                

                if metadata: 
                    file_summary = await _generate_summary(metadata=metadata)

                
                if chunks:
                    for chunk in chunks:
                        chunk["point_id"] = get_deterministic_id(filename=file_path,code=chunk["code"])
    
        

                logger.info(f"obtained {len(chunks)} chunks from file")

                embedded_chunks  = await embed_batch(chunks=chunks)
                logger.info(f"embedded {len(embedded_chunks)} chunks from file")
             
                file_metadata = {
                     **metadata,
                     "file_path": file_path,
                     "file_hash": file_hash,
                     "summary" : file_summary
                }
               
                payload = {
                     "repo_id": str(repo.id),
                     "job_id" : str(job.id),
                     "file_path": file_path,
                     "chunks_indexed":len(chunks),
                     "embedded_chunks": json.dumps(embedded_chunks),
                      "file_metadata": json.dumps(file_metadata),
                     "retries": "0"

                }
                return payload

        except Exception as e:
                error_msg = f"Failed to process {file_path}: {str(e)}"
                logger.error(error_msg)
                
                
                raise Exception(error_msg)



async def _generate_summary(metadata:dict):
    
    try:
        summary = await summarizer.summarize_file(metadata=metadata)
        return summary
    except Exception as e :
        logger.error(f"Failed to generate summary for {metadata.get('path')}: {str(e).lower()}")
        return "Summary unavailable"





