"""Application configuration via environment variables."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Micro SaaS"
    database_url: str = "sqlite:///./app.db"
    debug: bool = False
    secret_key: str = "change-me-in-production"

    class Config:
        env_prefix = "APP_"


settings = Settings()
