from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dotenv import load_dotenv

load_dotenv()
class Settings(BaseSettings):

    ENVIRONMENT: str = "development"
    GITHUB_TOKEN: str = "placeholder_token"
    
    
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/db"
    
    
    EMBEDDING_PROVIDER: str = "gemini" 
    GEMINI_API_KEY: str = "placeholder_key"
    GROQ_API_KEY: str = "placeholder_key"
    LLM_PROVIDER: str = "groq"
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = "placeholder_key"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    JWT_SECRET_KEY: str = "supersecret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()