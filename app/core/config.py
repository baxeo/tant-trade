from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./cashew.db"
    api_url: str = "http://api:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
