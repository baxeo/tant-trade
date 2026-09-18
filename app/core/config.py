import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:////tmp/cashew.db" if os.getenv("VERCEL") else "sqlite:///./cashew.db"
    api_url: str = "http://api:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
