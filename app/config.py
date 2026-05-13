"""Configuration for the research prototype."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the FastAPI application."""

    app_name: str = "Vendor-Agnostic Industrial Orchestrator"
    environment: str = "research"
    version: str = "0.1.0"

    model_config = SettingsConfigDict(env_prefix="ORCHESTRATOR_")


settings = Settings()
