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


def test_backend_cli_recommend_passes_archived_flag(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    class FakeApp:
        def run_command(self, command: str, **kwargs: object) -> dict[str, object]:
            assert command == "recommend"
            assert kwargs == {"include_archived": True}
            return {
                "ok": True,
                "command": "recommend",
                "data": {
                    "includeArchived": True,
                    "recommendations": [],
                },
            }

    monkeypatch.setattr("music_synchronizer.backend_cli.MusicSyncApp", FakeApp)

    exit_code = main(["recommend", "--archived"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "recommend"
    assert payload["data"]["includeArchived"] is True


def test_backend_cli_discovery_passes_clear_flag(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    class FakeApp:
        def run_command(self, command: str, **kwargs: object) -> dict[str, object]:
            assert command == "discovery"
            assert kwargs == {"clear": True}
            return {
                "ok": True,
                "command": "discovery",
                "data": {
                    "summary": {
                        "added": 0,
                        "skipped": 0,
                        "removedLiked": 0,
                        "cleared": 2,
                        "total": 0,
                    },
                    "recommendations": [],
                },
            }

    monkeypatch.setattr("music_synchronizer.backend_cli.MusicSyncApp", FakeApp)

    exit_code = main(["discovery", "--clear"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "discovery"
    assert payload["data"]["summary"]["cleared"] == 2
