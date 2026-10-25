from src.core.config import settings
from src.core.logger import get_logger
import math
from src.utils.text import build_embed_text

# from tenacity.asyncio import retry
from tenacity import (
    retry,
    retry_if_exception_type,
    after_log,
    wait_exponential_jitter,
    stop_after_attempt
)
import logging
logger = get_logger(__name__)

MAX_ATTEMPTS = 3
WAIT_TIME = 60

        


if settings.EMBEDDING_PROVIDER == "voyage":
    import voyageai # type: ignore
    _client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)

    def _embed_documents(texts: list[str]) -> list[list[float]]:
        logger.debug("Embedding with voyageai")
        result = _client.embed(texts, model="voyage-code-2", input_type="document")
        return result.embeddings


elif settings.EMBEDDING_PROVIDER == "gemini":
    # import google.generativeai as genai
    from src.core.gemini import gemini_client as client
    from google.genai.errors import ServerError,APIError

    @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=20, max=60),
            retry=retry_if_exception_type((APIError, ServerError)),
            after=after_log(logger=logger, log_level=logging.WARNING),
            reraise=True
    )
    async def _embed_documents(texts: list[str]) -> list[list[float]]:
    
        response = await client.aio.models.embed_content(
        model="gemini-embedding-001",
        contents=texts,
        config={
          "task_type":"RETRIEVAL_DOCUMENT"
          })
        return [item.values for item in response.embeddings]
    
    

else:
    raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")






async def embed_batch(chunks: list[dict]) -> list[dict]:
    embedded_chunks = []
    BATCH_SIZE = 100
    total_batches = math.ceil(len(chunks)/BATCH_SIZE)
    logger.info(f"Embedding batch count: {total_batches} ")
    for i in range (0, len(chunks), BATCH_SIZE) :
        current_batch = (i // BATCH_SIZE) + 1
        batch = chunks[i:i+BATCH_SIZE]
        texts  = [build_embed_text(chunk) for chunk in batch]
        try:
            vectors = await _embed_documents(texts)
            for j, chunk in enumerate(batch):
                embedded_chunks.append({
                                **chunk,
                                "vector": vectors[j]
                            })
            logger.info(f"Embedded batch: {current_batch}/{total_batches}")
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                logger.warning(f"Rate limit hit on batch {current_batch}")
                raise   # tenacity on _embed_documents already handles retry
            logger.error(f"Failed to embed batch: {error_msg}")
            raise
    return embedded_chunks



