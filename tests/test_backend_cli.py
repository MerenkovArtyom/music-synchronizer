import json
from pathlib import Path

import pytest

from music_synchronizer.backend_cli import main


def test_backend_cli_prints_json_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    exit_code = main(["show-config"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "ok": True,
        "command": "show-config",
        "data": {
            "config": {
                "yandexMusicTokenPresent": True,
                "obsidianVaultPath": str(tmp_path),
                "logLevel": "INFO",
            }
        },
    }


def test_backend_cli_prints_json_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    class FakeApp:
        def run_command(self, command: str, **kwargs: object) -> dict[str, object]:
            assert command == "dashboard"
            assert kwargs == {}
            return {
                "ok": False,
                "command": "dashboard",
                "error": {
                    "code": "DASHBOARD_FAILED",
                    "message": "dashboard unavailable",
                    "details": {},
                },
            }

    monkeypatch.setattr("music_synchronizer.backend_cli.MusicSyncApp", FakeApp)

    exit_code = main(["dashboard"])

    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "DASHBOARD_FAILED"
