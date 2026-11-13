from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://fulfillment:fulfillment@localhost:5432/fulfillment"
    generator_seed: int = 20261022
    google_client_id: str = ""
    google_client_secret: str = ""
    session_secret: str = "change-this-in-production"
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )


def load_rules(path: str = "config/business_rules.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


settings = Settings()
