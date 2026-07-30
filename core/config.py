"""
Central settings. Everything comes from environment variables / .env.
Rule 8: no secrets in code.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres in prod. Replit injects DATABASE_URL automatically.
    database_url: str = "postgresql+psycopg://platform:platform@localhost:5432/platform"

    # Used later (Chapter 2) for token hashing — declared now so .env shape is stable.
    secret_key: str = "change-me-in-.env"

    # WhatsApp Cloud API (Chapter 5)
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_app_secret: str
    whatsapp_verify_token: str

    @field_validator("database_url")
    @classmethod
    def force_psycopg_driver(cls, v: str) -> str:
        """Normalize any bare 'postgresql://' URL to use the psycopg3 driver."""
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v


settings = Settings()
