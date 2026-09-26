"""Application configuration loaded from environment variables."""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings

    class Settings(BaseSettings):
        """Application settings with environment variable bindings."""

        app_name: str = "ARGUS Backend 1"
        app_env: str = "development"
        debug: bool = True
        host: str = "0.0.0.0"
        port: int = 8000

        # MongoDB settings
        mongodb_uri: str = "mongodb://localhost:27017"
        mongodb_db_name: str = "argus_db"

        class Config:
            env_file = ".env"
            extra = "ignore"

except ImportError:
    # Fallback placeholder when pydantic-settings is not yet installed
    class Settings:  # type: ignore[no-redef]
        """Fallback settings reading directly from os.environ."""

        def __init__(self) -> None:
            self.app_name: str = os.getenv("APP_NAME", "ARGUS Backend 1")
            self.app_env: str = os.getenv("APP_ENV", "development")
            self.debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1")
            self.host: str = os.getenv("HOST", "0.0.0.0")
            self.port: int = int(os.getenv("PORT", "8000"))
            self.mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            self.mongodb_db_name: str = os.getenv("MONGODB_DB_NAME", "argus_db")


settings = Settings()
