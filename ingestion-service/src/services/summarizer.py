from src.core.gemini import gemini_client as client
from google.genai.errors import APIError, ServerError
from src.core.logger import get_logger
import logging

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    after_log,
    retry_if_exception_type,
)

logger = get_logger(__name__)


class Summarizer:
    def __init__(self, model_id: str = "gemini-2.5-flash-lite"):
        self.client = client
        self.model_id = model_id

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=10),
        retry=retry_if_exception_type((APIError, ServerError)),
        after=after_log(logger=logger, log_level=logging.WARNING),
        reraise=True,
    )
    async def summarize_file(self, metadata: dict) -> str:

        skeleton = "\n".join(line for line in metadata.get("skeleton", []))
        prompt = f"""
    You are an expert code summarizer. You will be provided a file name of a codebase and its header statements like import, export and a skeleton of the file. The skeleton contains the function or class declarations in the file along with type.
    Task: Based on the file metadata create a high level summary for the file. It should be understandable.
    Constraints: Maximum sentences to be used - 4. always give meaningfull sentences. 

    file_name: {metadata.get("path", [])}
    import statements: {metadata.get("imports", [])}
    export statements: {metadata.get("exports", [])}
    file skeleton : {skeleton}

    """

        response = await self.client.aio.models.generate_content(
            model=self.model_id,
            contents=prompt,
        )
        logger.debug(f"Obtained summary: {response.text}")
        return response.text
