from functools import lru_cache

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    groq_api_key: str = ""

    groq_model: str = (
        "openai/gpt-oss-20b"
    )

    groq_base_url: str = (
        "https://api.groq.com/openai/v1"
    )

    storage_backend: str = "local"
    local_data_dir: str = "data"

    aws_region: str = "ap-south-1"
    s3_bucket: str = ""

    self_consistency_runs: int = Field(
        default=3,
        ge=3,
        le=5,
    )

    self_consistency_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
    )

    max_tool_steps: int = Field(
        default=6,
        ge=1,
        le=12,
    )

    max_upload_mb: int = Field(
        default=10,
        ge=1,
        le=50,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
