from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    path: str = "./storage/db/nepremicninko.sqlite"
    auto_flush: bool = True


class DiscordConfig(BaseModel):
    webhook_url: str


class SchedulerConfig(BaseModel):
    enabled: bool = True
    interval_minutes: int = 3
    timezone: str = "Europe/Ljubljana"


class Config(BaseModel):
    database: DatabaseConfig
    discord: DiscordConfig
    scheduler: SchedulerConfig
    urls: list[str] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path = "config.yaml") -> "Config":
        config_path = Path(path)

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return cls(**data)

# Load the configuration
config = Config.from_yaml()