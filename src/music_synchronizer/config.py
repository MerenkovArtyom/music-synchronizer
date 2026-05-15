from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    yandex_music_token: str = Field(alias="YANDEX_MUSIC_TOKEN")
    obsidian_vault_path: Path = Field(
        default=Path("~/Documents/my_music").expanduser(),
        alias="OBSIDIAN_VAULT_PATH",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
