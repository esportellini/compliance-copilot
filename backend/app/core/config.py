from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Compliance Copilot"
    environment: Literal["local", "staging", "production"] = "local"

    # database — never hardcoded, always from env
    database_url: str = "postgresql+psycopg://compliance:compliance@db:5432/compliance"

    # auth
    secret_key: str = "CHANGE-ME-generate-with-python-secrets-token-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # ai provider
    ai_provider: Literal["mock", "openai"] = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

    # cors — comma-separated list
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
