import asyncio
from src.core.logger import get_logger
from src.core.redis import redis_manager, GROUP_PROCESS,STREAM_FILE_PROCESS, STREAM_FILE_STORE
from src.models.db import Repo,Job
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.ingestion.processor import process_file
from src.schemas.file import FileUpload
from src.utils.progress import flush_to_db,increment_processed,get_progress
from src.services.file_metadata import update_file_and_repo_chunks
import uuid
logger = get_logger(__name__)
CONSUMER_NAME = "process-worker-1"

MAX_RETRIES = 3



async def process_files_message(message_id:str, file_payload: dict):
    logger.info(f"Starting process for message: {message_id}") 
    try:
        payload      = FileUpload(**file_payload)   # ← likely failing here
        logger.info(f"Payload parsed: {payload.file_path}")
    except Exception as e:
        logger.error(f"Failed to parse payload: {e}")
        await redis_manager.ack(STREAM_FILE_PROCESS, GROUP_PROCESS, message_id)
        return
    repo_id = payload.repo_id
    job_id  = payload.job_id
    file_path = payload.file_path

    repo_url = payload.repo_url
    retries  = int(payload.retries)

    async with AsyncSessionLocal() as db:
        try:
            logger.debug("Reached here")
            result = await db.execute(select(Repo).where(Repo.id == uuid.UUID(repo_id)))
            repo = result.scalar_one_or_none()
            
            job_result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
            job = job_result.scalar_one_or_none()

            if not repo or not job:
                logger.error(f"Repo or Job not found in DB for Repo: {payload.repo_url}")
                await redis_manager.ack(STREAM_FILE_PROCESS, GROUP_PROCESS, CONSUMER_NAME, message_id)
                return

            
            


            logger.info(f"Processing job: {job_id} | repo_id: {repo_id}")
            repo.status = "processing"
            job.status  = "processing"
            repo.error_message = ""
            job.error_message=""
            await db.commit()
            file_data = await process_file(db,repo,job,payload)
            if file_data is None:
    # file skipped — still counts as processed
                
                await db.commit()
                await redis_manager.ack(STREAM_FILE_PROCESS, GROUP_PROCESS,CONSUMER_NAME, message_id)
                logger.info(f"File skipped: {file_path}")
                return


            # logger.info(f"Successfully Processed file: {file_path}")
            await increment_processed(job_id)
            progress = await get_progress(job_id=job_id)
            if progress.get("processed",0) >= job.total_files :
                await flush_to_db(db,job,repo)
            await update_file_and_repo_chunks(db,repo_id,file_path,file_data.get("chunks_indexed",0) )
            await db.commit()
            await redis_manager.ack(STREAM_FILE_PROCESS,GROUP_PROCESS , CONSUMER_NAME, message_id=message_id)
            # fix
            logger.debug(f"File processed: {file_path} chunks={file_data.get('chunks_indexed', 0)}")
            await redis_manager.publish(STREAM_FILE_STORE, payload=file_data)


            

        except Exception as e:
            await db.rollback() # Revert any unsaved DB changes
            error_msg = str(e).lower()
            logger.error(f"ERROR processing {repo_url}| file: {file_path}: {error_msg}")
            
            try:
                if repo and job:
                    repo.status = "failed"
                    job.status = "failed"
                    repo.error_message = error_msg[:200]
                    job.error_message = error_msg[:200]
                    await db.commit()
            except Exception as db_err:
                logger.error(f"Failed to save db status : {str(db_err).lower()} ")
            
            if "quota" in error_msg or "rate" in error_msg:
                logger.warning(f"Quota hit for repo_url : {repo_url} | file: {file_path} | try: {payload.retries} -- DEAD LETTER")
                await redis_manager.dead_letter(STREAM_FILE_PROCESS, file_payload,error=error_msg[:200],reason="quota_hit")
                logger.info(f"DEAD LETTER SENT | repo_url : {repo_url} | file_path : {file_path}")
                await redis_manager.ack(STREAM_FILE_PROCESS,GROUP_PROCESS,CONSUMER_NAME,message_id)
                logger.info(f"ACK repo_url: {repo_url} | file: {file_path}")
            
            elif retries < MAX_RETRIES :
                logger.warning(f"Retrying {repo_url} | file : {file_path} |attempt {retries + 1 }/{MAX_RETRIES}")
                await redis_manager.republish_with_retry(STREAM_FILE_PROCESS, file_payload,
                retries= retries+1)
                await redis_manager.ack(STREAM_FILE_PROCESS,GROUP_PROCESS,CONSUMER_NAME,message_id)
            else:
                logger.warning(f"Max retries exceeded : {repo_url}| file : {file_path} | DEAD LETTER")
                await redis_manager.dead_letter(STREAM_FILE_PROCESS, file_payload, error_msg,reason="Max retries reached")
                logger.info(f"DEAD LETTER SENT: {repo_url} | file : {file_path}")
                await redis_manager.ack(STREAM_FILE_PROCESS, GROUP_PROCESS,CONSUMER_NAME, message_id)




async def start_worker():

    await redis_manager.init_redis()
    await redis_manager._init_consumer_groups()

    api_bouncer = asyncio.Semaphore(1)
    async def bounded_process(msg_id, payload):
        async with api_bouncer:
            await process_files_message(msg_id, payload)
            await asyncio.sleep(3)


    claimed_messages = await redis_manager.reclaim_abandoned(STREAM_FILE_PROCESS, GROUP_PROCESS,CONSUMER_NAME)
    if claimed_messages:
        logger.info(f"Processing {len(claimed_messages)} reclaimed messages...")
        await asyncio.gather(*[
            process_files_message(msg_id, payload)
            for msg_id, payload in claimed_messages
        ],return_exceptions=True)

    logger.info(f"Worker {GROUP_PROCESS} listening on {STREAM_FILE_PROCESS}")

    while True:
        try:
            results = await redis_manager.consume(STREAM_FILE_PROCESS,GROUP_PROCESS,CONSUMER_NAME) 

            if not results:
                continue
            for stream_name, messages in results:
                if not messages:
                    continue
                # process all 5 concurrently
                await asyncio.gather(*[
                    bounded_process(msg_id, payload)
                    for msg_id, payload in messages
                ],return_exceptions=True)
            
    

        except Exception as e:
            await asyncio.sleep(2)
            logger.warning(f"Fetch Worker Loop Error: {e}")

if __name__ == "__main__":
    
    asyncio.run(start_worker())




    