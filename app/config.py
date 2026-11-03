"""Environment-backed runtime configuration."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated process and API settings."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    api_key: SecretStr = Field(min_length=16)
    browser_engine: Literal["lightpanda", "chromium"] = "lightpanda"
    lightpanda_path: str = "/usr/local/bin/lightpanda"
    lightpanda_host: Literal["127.0.0.1"] = "127.0.0.1"
    lightpanda_port: int = Field(default=9222, ge=1024, le=65535)
    browser_start_timeout: float = Field(default=30, gt=0)
    page_timeout_ms: int = Field(default=30000, gt=0)
    request_timeout: float = Field(default=180, gt=0)
    max_concurrent_sessions: int = Field(default=1, ge=1, le=8)
    allowed_origins: list[str] = []
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
