from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    GITHUB_TOKEN: str
    DATABASE_URL: str
    VOYAGE_API_KEY: str
    GEMINI_API_KEY: str
    ENVIRONMENT: str = "development"
    EMBEDDING_PROVIDER: str   
    REDIS_URL: str
    LLM_PROVIDER: str="groq"
    GROQ_MODEL: str="llama-3.3-70b-versatile"
    GROQ_API_KEY: str
    QDRANT_URL: str
    QDRANT_API_KEY: str

    JWT_SECRET_KEY:     str
    JWT_ALGORITHM:      str ="HS256"
    JWT_EXPIRE_MINUTES: int = 30


    class Config:
        env_file = ".env"

settings = Settings()