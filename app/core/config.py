from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    GITHUB_TOKEN: str
    DATABASE_URL: str
    VOYAGE_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()