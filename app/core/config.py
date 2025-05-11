from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    JWT_SECRET_KEY: str = "your-super-secret-key-please-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Example of loading from .env file (requires python-dotenv)
    # class Config:
    #     env_file = ".env"
    #     env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
