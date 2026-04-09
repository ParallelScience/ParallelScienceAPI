"""Application settings via pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # GCS
    gcs_db_url: str = "https://storage.googleapis.com/parallel-arxiv-pdfs/papers.db"
    db_path: str = "/tmp/papers.db"
    db_refresh_interval_minutes: int = 30

    # Admin
    admin_api_key: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # API
    api_v1_prefix: str = "/api/v1"

    model_config = {"env_prefix": "PX_API_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
