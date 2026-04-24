from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    yandex_music_token: str = Field(alias="YANDEX_MUSIC_TOKEN")
    obsidian_vault_path: Path = Field(
        default=Path("/Users/artem/Documents/my_music"),
        alias="OBSIDIAN_VAULT_PATH",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

