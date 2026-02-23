"""
WOMS Configuration Module

Centralized configuration management using Pydantic Settings.
Supports environment variables and .env file loading.
"""

import secrets
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from pydantic import field_validator, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from the project root regardless of CWD.
# __file__ = backend/app/config.py → .parent.parent.parent = project root
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"


def generate_secret_key() -> str:
    """Generate a secure 256-bit secret key."""
    return secrets.token_hex(32)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes are automatically loaded from:
    1. Environment variables
    2. .env file in project root
    """
    
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ==========================================================================
    # Application Settings
    # ==========================================================================
    app_name: str = "WOMS API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # ==========================================================================
    # API Configuration
    # ==========================================================================
    api_v1_prefix: str = "/api/v1"
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "woms_db"
    database_user: str = "postgres"
    database_password: str = ""
    
    # Computed database URLs
    database_url: Optional[str] = None
    database_url_sync: Optional[str] = None

    # ==========================================================================
    # ML Staging Database Configuration
    # ==========================================================================
    ml_database_host: str = "localhost"
    ml_database_port: int = 5432
    ml_database_name: str = "ml_woms_db"
    ml_database_user: str = "postgres"
    ml_database_password: str = ""

    # Override with a full URL (e.g. via ML_DATABASE_URL env var)
    ml_database_url: Optional[str] = None
    
    @property
    def async_database_url(self) -> str:
        """Get async database URL for SQLAlchemy/SQLModel."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )
    
    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic migrations."""
        if self.database_url_sync:
            return self.database_url_sync
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def async_ml_database_url(self) -> str:
        """Get async database URL for the ML staging database."""
        if self.ml_database_url:
            return self.ml_database_url
        return (
            f"postgresql+asyncpg://{self.ml_database_user}:{self.ml_database_password}"
            f"@{self.ml_database_host}:{self.ml_database_port}/{self.ml_database_name}"
        )
    
    # ==========================================================================
    # Security & Authentication
    # ==========================================================================
    secret_key: str = None  # Auto-generated if not provided
    
    @field_validator("secret_key", mode="before")
    @classmethod
    def generate_secret_key_if_missing(cls, v):
        """Auto-generate a secure secret key if not provided."""
        if v is None or v == "" or v.startswith("change-this") or v.startswith("your_super_secret"):
            return generate_secret_key()
        return v
    
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # ==========================================================================
    # Server Configuration
    # ==========================================================================
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = True
    
    # ==========================================================================
    # Logging
    # ==========================================================================
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # ==========================================================================
    # Validators
    # ==========================================================================
    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_list(cls, v):
        """Parse comma-separated string or JSON list into Python list."""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [item.strip() for item in v.split(",")]
        return v


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()


# Export settings instance for easy import
settings = get_settings()
