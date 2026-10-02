"""
Application configuration using Pydantic Settings.

All environment variables are loaded from .env and validated at startup.
"""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "AI Career Intelligence"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # --- Security ---
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_career_db"
    DATABASE_ECHO: bool = False

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- ChromaDB ---
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_DIR: str = "./data/chromadb"

    # --- Google Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- HuggingFace ---
    HF_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- File Storage ---
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # --- Admin ---
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "admin-password-change-me"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure SECRET_KEY is secure."""
        if not v or len(v.strip()) < 16:
            raise ValueError("SECRET_KEY must be at least 16 characters long.")
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from comma-separated string or JSON list."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Strict security validations when deployed in production."""
        if self.is_production:
            if self.DEBUG:
                raise ValueError("DEBUG must be set to False in production environment.")
            insecure_defaults = {
                "change-me-in-production",
                "your-super-secret-key-change-in-production",
                "your-secret-key",
                "secret",
            }
            if self.SECRET_KEY.lower().strip() in insecure_defaults or len(self.SECRET_KEY.strip()) < 32:
                raise ValueError(
                    "In production, SECRET_KEY must be a cryptographically secure random string of at least 32 characters."
                )
            if any(origin.strip() == "*" for origin in self.CORS_ORIGINS):
                raise ValueError(
                    "Wildcard '*' CORS origins are forbidden in production with authenticated credentials."
                )
            if self.ADMIN_PASSWORD in ("admin-password-change-me", "admin", "password", "123456"):
                raise ValueError("ADMIN_PASSWORD must be changed to a secure password in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
