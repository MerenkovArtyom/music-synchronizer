import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_VAULT_PATH = Path("~/Documents/my_music").expanduser()


def _resolved_env_file() -> Path:
    explicit_path = os.getenv("MUSIC_SYNC_CONFIG_PATH")
    if explicit_path:
        candidate = Path(explicit_path).expanduser()
        if candidate.exists():
            return candidate
    return DEFAULT_ENV_FILE


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def raw_config_values() -> dict[str, str]:
    explicit_path = os.getenv("MUSIC_SYNC_CONFIG_PATH")
    source_path = Path(explicit_path).expanduser() if explicit_path else DEFAULT_ENV_FILE
    env_values = _parse_env_file(source_path)
    keys = [
        "YANDEX_MUSIC_TOKEN",
        "OBSIDIAN_VAULT_PATH",
        "YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME",
        "LOG_LEVEL",
    ]
    for key in keys:
        if key in os.environ:
            env_values[key] = os.environ[key]
    return env_values


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    yandex_music_token: str = Field(default="", alias="YANDEX_MUSIC_TOKEN")
    obsidian_vault_path: Path = Field(
        default=DEFAULT_VAULT_PATH,
        alias="OBSIDIAN_VAULT_PATH",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    discovery_playlist_name: str = Field(
        default="Рекомендации",
        alias="YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        dotenv_source = DotEnvSettingsSource(
            settings_cls,
            env_file=_resolved_env_file(),
            env_file_encoding="utf-8",
        )
        return (
            init_settings,
            env_settings,
            dotenv_source,
            file_secret_settings,
        )
