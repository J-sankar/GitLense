from app.core.config import settings
from app.core.logger import get_logger
from app.core.redis import redis_conn
import math
from app.utils.text import build_embed_text
import time
import json
from tenacity import retry, retry_if_exception_type,after_log,wait_exponential_jitter,stop_after_attempt
import logging
logger = get_logger(__name__)

MAX_ATTEMPTS = 3
WAIT_TIME = 60

def save_progress(job_id:str, embeddded_chunks : list[dict], remaining_chunks: list[dict]):
    try:
        redis_conn.setex(
        f"embedd_progress:{job_id}",
        3600,
        json.dumps({
            "embedded": embeddded_chunks,
            "remaining": remaining_chunks
            })
            ) 
        logger.info(f"Progress saved: {len(embeddded_chunks)} , remaining: {len(remaining_chunks)} ")  
    except Exception as e:
        logger.error(f"Failed to cache: {str(e)}")
        

        
def load_progress(job_id:str) -> dict | None :
    
    cached  = redis_conn.get(f"embedd_progress:{job_id}")
    if cached:
        logger.info("Resuming from saved progress")
        return json.loads(cached)
    return None
        


if settings.EMBEDDING_PROVIDER == "voyage":
    import voyageai
    _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)

    def _embed_documents(texts: list[str]) -> list[list[float]]:
        logger.debug("Embedding with voyageai")
        result = _client.embed(texts, model="voyage-code-2", input_type="document")
        return result.embeddings

    def _embed_query(text: str) -> list[float]:
        result = _client.embed([text], model="voyage-code-2", input_type="query")
        return result.embeddings[0]

elif settings.EMBEDDING_PROVIDER == "gemini":
    # import google.generativeai as genai
    from app.core.gemini import gemini_client as client
    from google.genai.errors import ServerError,APIError

    @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1, max=10),
            retry=retry_if_exception_type((APIError, ServerError)),
            after=after_log(logger=logger, log_level=logging.WARNING),
            reraise=True
    )
    def _embed_documents(texts: list[str]) -> list[list[float]]:
    
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=texts,
                config={
                  "task_type":"RETRIEVAL_DOCUMENT"
                })
            return [item.values for item in response.embeddings]
    
    
    def _embed_query(text: str) -> list[float]:
        try:
            response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config={
                "task_type": "RETRIEVAL_QUERY"
            }
        )
        # Access the first (and only) embedding result
            return response.embeddings[0].values
        except Exception as e:
            logger.error(str(e))
            raise Exception(f"Error: {str(e)}")

else:
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")




def embed_chunks(chunks: list[dict], job_id :str = None) -> list[dict]:
    embedded_chunks = []
    batch_size = 10
    batch_count = math.floor(len(chunks)/batch_size)

    if job_id:
        saved = load_progress(job_id)
        if saved:
            embedded_chunks = saved["embedded"]
            chunks = saved["remaining"]

    batch_length =  math.ceil(len(chunks)/batch_size) 
    for i in range(0, len(chunks), batch_size):
        batch  = chunks[i:i + batch_size]
        texts  = [build_embed_text(chunk) for chunk in batch]
        for attempt in range(MAX_ATTEMPTS):
            
            logger.info(f"Embedding started for batch: {batch_count} / {batch_length} , Attempts : {attempt + 1}")
            try:
                vectors = _embed_documents(texts)

                for j, chunk in enumerate(batch):
                    embedded_chunks.append({
                        **chunk,
                        "vector": vectors[j]
                    })

                logger.info(f"Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")
                batch_count = batch_count + 1 
                break
            except Exception as e:
                error_msg = str(e).lower()

                if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                    logger.warning(f"Rate limit hit on batch {batch_count}! waiting {WAIT_TIME}s...")
                    if job_id:
                        save_progress(
                            job_id=job_id,
                            embeddded_chunks=embedded_chunks,
                            remaining_chunks=chunks[i:]
                        )
                    if attempt < MAX_ATTEMPTS -1   :
                        time.sleep(WAIT_TIME)
                        logger.info(f"Continuing Inegestion for batch: {batch_count}")
                        continue
                    else:
                        logger.error(f"Max Retries Reached: {attempt+1}/{MAX_ATTEMPTS}")
                        raise Exception(
                        f"Embedding failed after {MAX_ATTEMPTS} attempts on batch {batch_count}. "
                        f"Rate limit/quota exhausted. "
                        f"Progress saved: {len(embedded_chunks)} chunks embedded."
                    )
                else :
                    logger.error(f"Embedding Failed: {str(e)} ")
                    raise

    if job_id:
        clear_progress(job_id)

    logger.info(f"Embedding complete: {len(embedded_chunks)} chunks")     
    return embedded_chunks

def embed_batch(chunks: list[dict]) -> list[dict]:
    embedded_chunks = []
    BATCH_SIZE = 100
    total_batches = math.ceil(len(chunks)/BATCH_SIZE)
    logger.info(f"Embedding batch count: {total_batches} ")
    for i in range (0, len(chunks), BATCH_SIZE) :
        current_batch = (i // BATCH_SIZE) + 1
        batch = chunks[i:i+BATCH_SIZE]
        texts  = [build_embed_text(chunk) for chunk in batch]
        try:
            vectors = _embed_documents(texts)
            for j, chunk in enumerate(batch):
                embedded_chunks.append({
                                **chunk,
                                "vector": vectors[j]
                            })
            logger.info(f"Embedded batch: {current_batch}/{total_batches}")
        except Exception as e:
            logger.error(f"Failed to embed batch: {str(e).lower()} ")
            raise e
    return embedded_chunks


def embed_query(text: str) -> list[float]:
    result = _embed_query(text)
    logger.debug(f"Embedded query: {text[:50]}...")
    return result


def clear_progress(job_id):
    try:
        redis_conn.delete(f"embedd_progress:{job_id}")
        logger.info(f"Job {job_id} : progress cleared from cache")
    except Exception as e:
        logger.error(f"Job {job_id}: failed to clear progress :{str(e)}")