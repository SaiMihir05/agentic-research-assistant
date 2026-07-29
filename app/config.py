from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Database URL – default points to a local PostgreSQL container
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/postgres"

    # Redis URL – used later for caching/memory
    redis_url: str = "redis://redis:6379/0"

    # Qdrant URL
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333

    # Gemini API key – will be set in .env for Phase 2
    gemini_api_key: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Load settings instance – import this where needed
settings = Settings()
