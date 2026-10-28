"""
Application configuration — loads from environment variables via pydantic-settings.
All settings can be overridden by a .env file placed in the backend/ directory.
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "AI Multi-Agent Workflow Automation Platform"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = "postgresql://postgres:changeme@localhost:5432/ai_workflow_db"

    @field_validator("database_url", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        """Ensure standard postgresql:// URL uses psycopg2 dialect."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # ── Gemini AI ────────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_timeout_seconds: int = 30

    @property
    def is_gemini_configured(self) -> bool:
        """Check if a non-placeholder Gemini API key is configured."""
        key = self.gemini_api_key.strip()
        return bool(key and key != "your_gemini_api_key_here")

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── Security ─────────────────────────────────────────────────────────────
    secret_key: str = "change_this_to_a_random_secret_key_in_production"

    @property
    def cors_origins(self) -> List[str]:
        """Parse the comma-separated ALLOWED_ORIGINS string into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
