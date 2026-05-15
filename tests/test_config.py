from pathlib import Path

import pytest

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
