from pathlib import Path

import pytest

from music_synchronizer.config import Settings


def test_settings_reads_token_and_obsidian_path(tmp_path: Path) -> None:
    settings = Settings.model_validate(
        {
            "YANDEX_MUSIC_TOKEN": "test-token",
            "OBSIDIAN_VAULT_PATH": str(tmp_path),
            "LOG_LEVEL": "DEBUG",
            "YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME": "My Discovery",
        }
    )

    assert settings.yandex_music_token == "test-token"
    assert settings.obsidian_vault_path == tmp_path
    assert settings.log_level == "DEBUG"
    assert settings.discovery_playlist_name == "My Discovery"


def test_settings_use_default_discovery_playlist_name(tmp_path: Path) -> None:
    settings = Settings.model_validate(
        {
            "YANDEX_MUSIC_TOKEN": "test-token",
            "OBSIDIAN_VAULT_PATH": str(tmp_path),
        }
    )

    assert settings.discovery_playlist_name == "Рекомендации"


def test_settings_load_dotenv_relative_to_project_root_when_cwd_differs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(Path("/private/tmp"))
    monkeypatch.delenv("YANDEX_MUSIC_TOKEN", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.yandex_music_token
    assert settings.obsidian_vault_path == Path("/Users/artem/Documents/my_music")
    assert (project_root / ".env").exists()


def test_settings_read_explicit_config_path_from_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "Music Synchronizer" / "config.env"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "\n".join(
            [
                "YANDEX_MUSIC_TOKEN=desktop-token",
                f"OBSIDIAN_VAULT_PATH={tmp_path / 'vault'}",
                "YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME=Desktop Discovery",
                "LOG_LEVEL=DEBUG",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MUSIC_SYNC_CONFIG_PATH", str(config_path))
    monkeypatch.delenv("YANDEX_MUSIC_TOKEN", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.delenv("YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.yandex_music_token == "desktop-token"
    assert settings.obsidian_vault_path == tmp_path / "vault"
    assert settings.discovery_playlist_name == "Desktop Discovery"
    assert settings.log_level == "DEBUG"


def test_settings_fall_back_to_project_dotenv_when_explicit_path_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_path = Path("/private/tmp/does-not-exist/music-sync-config.env")
    monkeypatch.setenv("MUSIC_SYNC_CONFIG_PATH", str(missing_path))
    monkeypatch.delenv("YANDEX_MUSIC_TOKEN", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings()

    assert settings.yandex_music_token
    assert settings.obsidian_vault_path == Path("/Users/artem/Documents/my_music")
