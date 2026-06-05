from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from dotenv import load_dotenv

load_dotenv()
class Settings(BaseSettings):

    ENVIRONMENT: str = "development"    
    DATABASE_URL: str
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    # Security
    JWT_SECRET_KEY: str = "supersecret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()