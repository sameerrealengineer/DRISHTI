"""Runtime configuration, read from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", REPO_ROOT / ".env"), extra="ignore")

    drishti_mode: str = "demo"  # demo | live
    database_url: str = "postgresql+psycopg://drishti:drishti@localhost:5432/drishti"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me"
    phone_pepper: str = "change-me-pepper"
    phone_enc_key: str = ""  # base64 32-byte AES key; derived from jwt_secret if empty (demo only)

    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "drishti"
    s3_key: str = "minio"
    s3_secret: str = "minio123"

    open_meteo_base: str = "https://api.open-meteo.com/v1/forecast"
    sachet_rss_url: str = ""
    fcm_credentials_json: str = ""
    sms_provider: str = "simulated"
    whatsapp_provider: str = "simulated"
    gee_service_account_json: str = ""
    auto_assign_seconds: int = 300
    default_language: str = "or"

    seed_dir: Path = REPO_ROOT / "seed"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # Demo sim clock: real seconds per simulated hour at 1x speed.
    sim_seconds_per_hour: float = 20.0
    sim_default_scenario: str = "titli"

    @property
    def is_demo(self) -> bool:
        return self.drishti_mode == "demo"

    @property
    def effective_auto_assign_seconds(self) -> int:
        return 6 if self.is_demo else self.auto_assign_seconds


@lru_cache
def get_settings() -> Settings:
    return Settings()
