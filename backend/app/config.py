from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AegisPR"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: str = "http://localhost:3000"
    github_token: str | None = Field(default=None, repr=False)
    nebius_api_key: str | None = Field(default=None, repr=False)
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1/"
    nebius_model: str = "nvidia/nemotron-3-ultra-550b-a55b"
    gpu_worker_url: str | None = None
    gpu_worker_token: str | None = Field(default=None, repr=False)
    enable_sandbox: bool = False
    sandbox_timeout_seconds: int = 300
    sandbox_memory: str = "2g"
    sandbox_cpus: float = 2.0
    max_changed_files: int = 100
    max_diff_characters: int = 120_000
    workspace_root: Path = Path("/tmp/aegispr-runs")
    data_path: Path = Path("data/aegispr.sqlite3")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

