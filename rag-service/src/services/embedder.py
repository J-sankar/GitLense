from src.core.config import settings
from src.core.logger import get_logger
from tenacity import retry, retry_if_exception_type,after_log,wait_exponential_jitter,stop_after_attempt
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

    def _embed_query(text: str) -> list[float]:
        result = _client.embed([text], model="voyage-code-2", input_type="query")
        return result.embeddings[0]

elif settings.EMBEDDING_PROVIDER == "gemini":
    from src.core.gemini import gemini_client as client
    from google.genai.errors import ServerError,APIError

    @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=20, max=60),
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
    
    
    async def _embed_query(text: str) -> list[float]:
        try:
            response = await client.aio.models.embed_content(
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






async def embed_query(text: str) -> list[float]:
    result = await _embed_query(text)
    logger.debug(f"Embedded query: {text[:50]}...")
    return result
