from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    JWT_SECRET_KEY: str = "your-super-secret-key-please-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@db:5432/appdb"
    MONGO_URL: str = ""

    GEMINI_API_KEY: str = "AIzaSyBLXXAQPrZETV-R1xU37UaD4esoc_BikyU"
    GEMINI_SYSTEM_PROMPT: str = (
        "You are a helpful AI assistant that answers questions based on the provided document."
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
