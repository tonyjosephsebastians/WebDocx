from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Word Workspace API"
    app_env: str = "development"
    api_prefix: str = "/api"
    secret_key: str = "development-secret"
    access_token_expire_minutes: int = 60 * 24 * 7
    public_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./word_workspace.db"
    storage_root: Path = Field(default_factory=lambda: Path("storage"))
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    onlyoffice_document_server_url: str = "http://localhost:8080"
    onlyoffice_browser_secret: str = "onlyoffice-secret"
    onlyoffice_inbox_secret: str = "onlyoffice-secret"
    onlyoffice_outbox_secret: str = "onlyoffice-secret"

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_storage_root(self) -> Path:
        return Path(self.storage_root).resolve()

    @property
    def trimmed_public_url(self) -> str:
        return self.public_url.rstrip("/")

    @property
    def trimmed_document_server_url(self) -> str:
        return self.onlyoffice_document_server_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
