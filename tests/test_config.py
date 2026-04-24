from pathlib import Path

from music_synchronizer.config import Settings


def test_settings_reads_token_and_obsidian_path(tmp_path: Path) -> None:
    settings = Settings.model_validate(
        {
            "YANDEX_MUSIC_TOKEN": "test-token",
            "OBSIDIAN_VAULT_PATH": str(tmp_path),
            "LOG_LEVEL": "DEBUG",
        }
    )

    assert settings.yandex_music_token == "test-token"
    assert settings.obsidian_vault_path == tmp_path
    assert settings.log_level == "DEBUG"
