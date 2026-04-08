from google import genai
from google.genai.errors import ClientError
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

def get_gemini_client()->genai.Client:
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Initialized Gemini client")
        return client
    except ClientError as e:
        logger.error(f"Error: {str(e).lower()}")
        raise ClientError(
        status_code=400,
        response_json={"error": {"message": str(e).lower()}},
        response=None
)

gemini_client = get_gemini_client()
