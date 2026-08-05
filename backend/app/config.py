from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "VidInsight"
    app_env: str = "development"
    app_secret_key: str = "dev-only-change-me"
    token_encryption_key: str = "dev-only-change-me-too"
    database_url: str = "sqlite+aiosqlite:///./vidinsight.db"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origins: str = "http://localhost:5173,http://localhost"
    admin_email: str = "admin@vidinsight.local"
    admin_password: str = "ChangeMe123!"
    export_dir: Path = Path("exports")
    enable_computer_use: bool = False
    enable_controlled_crawler: bool = False
    crawler_allowed_domains: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    return settings

