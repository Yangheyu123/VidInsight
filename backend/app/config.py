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
    data_source_url: str | None = None
    data_source_token: str | None = None
    computer_use_source_url: str | None = None
    computer_use_source_token: str | None = None
    computer_use_ingest_token: str | None = None
    computer_use_default_account_id: str | None = None
    controlled_crawler_source_url: str | None = None
    controlled_crawler_source_token: str | None = None
    data_source_timeout_seconds: int = 20
    frontend_app_url: str = "http://localhost"
    douyin_client_key: str | None = None
    douyin_client_secret: str | None = None
    douyin_redirect_uri: str | None = None
    douyin_scopes: str = "user_info,video.list"
    douyin_business_access_token: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def douyin_scope_list(self) -> list[str]:
        return [scope.strip() for scope in self.douyin_scopes.split(",") if scope.strip()]

    @property
    def crawler_domain_list(self) -> list[str]:
        return [domain.strip().lower() for domain in self.crawler_allowed_domains.split(",") if domain.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    return settings
