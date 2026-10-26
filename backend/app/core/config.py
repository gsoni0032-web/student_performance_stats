"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_SECRET_PREFIX = "change-me"


class Settings(BaseSettings):
    """Runtime configuration. Every value can be overridden by an environment variable."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    secret_key: str = Field(min_length=32)
    database_url: str = "sqlite:///./pathway.db"
    cors_origins: str = "http://localhost:5173"
    access_token_minutes: int = Field(default=15, ge=1, le=240)
    refresh_token_days: int = Field(default=7, ge=1, le=90)
    max_failed_logins: int = Field(default=5, ge=3, le=20)
    lockout_minutes: int = Field(default=15, ge=1, le=1440)
    login_rate_limit: int = Field(default=10, ge=1)
    login_rate_window_seconds: int = Field(default=60, ge=1)
    dashboard_cache_seconds: int = Field(default=60, ge=0)
    model_dir: Path = Path("./model_store")
    log_level: str = "INFO"
    log_json: bool = True
    enable_docs: bool = True
    force_https: bool = False
    ml_candidates: str = "logreg,random_forest,xgboost"
    training_search_iterations: int = Field(default=12, ge=1, le=100)

    @field_validator("database_url")
    @classmethod
    def normalise_database_url(cls, value: str) -> str:
        """Accept the `postgres://` and `postgresql://` URLs that hosting platforms hand out."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def reject_placeholder_secret_in_production(self) -> Settings:
        """Refuse to start in production with the example secret from .env.example."""
        if self.app_env == "production" and self.secret_key.startswith(PLACEHOLDER_SECRET_PREFIX):
            raise ValueError("SECRET_KEY must be replaced with a random value in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list, ignoring blanks."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ml_candidate_list(self) -> list[str]:
        """Model families to compare during training."""
        return [name.strip() for name in self.ml_candidates.split(",") if name.strip()]

    @property
    def is_production(self) -> bool:
        """True when running with APP_ENV=production."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()  # type: ignore[call-arg]
