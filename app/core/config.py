from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    PROJECT_NAME: str
    RELEASE: bool

    DB_PATH: str
    DISCORD_WEBHOOK_URL: str

    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_MINUTES: int
    SCHEDULER_TIMEZONE: str

config = Config() # type: ignore