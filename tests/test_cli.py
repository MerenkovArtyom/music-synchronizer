import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from music_synchronizer.cli import app


def test_help_shows_sync_placeholder() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "sync" in result.output
    assert "show-config" in result.output


def test_list_filters_active_tracks_by_tag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Song.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Song"',
                'artists: ["Artist"]',
                'system_tags: ["Rock"]',
                'user_tags: ["live"]',
                "---",
            ]
        ),
        encoding="utf-8",
    )
    (tracks_dir / "Other.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Other"',
                'artists: ["Another Artist"]',
                'system_tags: ["alt-rock"]',
                "user_tags: []",
                "---",
            ]
        ),
        encoding="utf-8",
    )
    removed_dir = tracks_dir / "_removed"
    removed_dir.mkdir(exist_ok=True)
    (removed_dir / "Removed.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Removed"',
                'artists: ["Artist"]',
                'system_tags: ["rock"]',
                "user_tags: []",
                "---",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["list", "--tag", "rock"])

    assert result.exit_code == 0
    assert result.output.strip().splitlines() == ["Song - Artist"]


def test_list_reports_when_no_tracks_match_tag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Song.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Song"',
                'artists: ["Artist"]',
                'system_tags: ["indie"]',
                "user_tags: []",
                "---",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["list", "--tag", "rock"])

    assert result.exit_code == 0
    assert result.output.strip() == 'No active saved tracks found for tag "rock".'


def test_list_filters_active_tracks_by_artist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Song.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Song"',
                'artists: ["ARTIST", "Guest"]',
                'system_tags: ["Rock"]',
                "user_tags: []",
                "---",
            ]
        ),
        encoding="utf-8",
    )
    (tracks_dir / "Other.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Other"',
                'artists: ["Another Artist"]',
                'system_tags: ["Rock"]',
                "user_tags: []",
                "---",
            ]
        ),
        encoding="utf-8",
    )
    removed_dir = tracks_dir / "_removed"
    removed_dir.mkdir(exist_ok=True)
    (removed_dir / "Removed.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Removed"',
                'artists: ["Artist"]',
                'system_tags: ["Rock"]',
                "user_tags: []",
                "---",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["list", "--artist", "artist"])

    assert result.exit_code == 0
    assert result.output.strip().splitlines() == ["Song - ARTIST, Guest"]


def test_list_reports_when_no_tracks_match_artist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Song.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Song"',
                'artists: ["Artist"]',
                'system_tags: ["indie"]',
                "user_tags: []",
                "---",
            ]
        ),
        encoding="utf-8",
    )


def test_list_filters_active_tracks_by_user_tag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Song.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Song"',
                'artists: ["Artist"]',
                "system_tags: []",
                'user_tags: ["Mood"]',
                "---",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["list", "--tag", "mood"])

    assert result.exit_code == 0
    assert result.output.strip().splitlines() == ["Song - Artist"]


def test_list_deduplicates_combined_user_and_system_tags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Song.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Song"',
                'artists: ["Artist"]',
                'system_tags: ["Rock"]',
                'user_tags: ["rock", "live", " live "]',
                "---",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["list", "--tag", "live"])

    assert result.exit_code == 0
    assert result.output.strip().splitlines() == ["Song - Artist"]

    result = CliRunner().invoke(app, ["list", "--artist", "unknown"])

    assert result.exit_code == 0
    assert result.output.strip() == 'No active saved tracks found for artist "unknown".'


def test_list_requires_exactly_one_filter() -> None:
    result = CliRunner().invoke(app, ["list"])

    assert result.exit_code == 2
    assert "Exactly one of --tag or --artist must be provided." in result.output


def test_list_rejects_multiple_filters() -> None:
    result = CliRunner().invoke(app, ["list", "--tag", "rock", "--artist", "artist"])

    assert result.exit_code == 2
    assert "Exactly one of --tag or --artist must be provided." in result.output


def test_list_reports_clear_error_for_extra_filter_value() -> None:
    result = CliRunner().invoke(app, ["list", "--artist", "Artist", "Guest"])

    assert result.exit_code == 2
    assert "Filter values must be passed as a single argument." in result.output
    assert '--artist "Artist Guest"' in result.output


def test_sync_creates_structured_obsidian_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from music_synchronizer import cli
    from music_synchronizer.models import SyncSummary, TrackInfo

    class FakeSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def run(self) -> SyncSummary:
            vault = self.settings.obsidian_vault_path
            (vault / "tracks").mkdir(parents=True, exist_ok=True)
            (vault / "tracks" / "Song.md").write_text(
                TrackInfo(
                    track_id="1",
                    title="Song",
                    artists=["Artist"],
                    album="Album",
                    tags=["rock"],
                    year=2024,
                    cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
                    duration_seconds=180,
                    source_position=1,
                    yandex_url="https://music.yandex.ru/track/1",
                ).title,
                encoding="utf-8",
            )
            return SyncSummary(
                fetched=1,
                written=1,
                archived=0,
                restored=0,
            )

    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(cli, "SyncService", FakeSyncService)

    result = CliRunner().invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "Synchronized 1 tracks." in result.output
    assert not (tmp_path / "playlist.md").exists()
    assert (tmp_path / "tracks" / "Song.md").exists()


def test_sync_does_not_create_partial_files_when_service_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from music_synchronizer import cli

    class FailingSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def run(self) -> int:
            raise RuntimeError("boom")

    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(cli, "SyncService", FailingSyncService)

    result = CliRunner().invoke(app, ["sync"])

    assert result.exit_code == 4
    assert "Sync failed: boom" in result.output
    assert not (tmp_path / "playlist.md").exists()
    assert not (tmp_path / "tracks").exists()


def test_show_config_supports_json_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    result = CliRunner().invoke(app, ["show-config", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "command": "show-config",
        "data": {
            "config": {
                "yandexMusicTokenPresent": True,
                "obsidianVaultPath": str(tmp_path),
                "logLevel": "DEBUG",
            }
        },
    }


def test_list_supports_json_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Song.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Song"',
                'artists: ["Artist", "Guest"]',
                'system_tags: ["Rock"]',
                'user_tags: ["live"]',
                "---",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["list", "--tag", "rock", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "command": "list",
        "data": {
            "filter": {
                "kind": "tag",
                "value": "rock",
            },
            "tracks": [
                {
                    "title": "Song",
                    "artists": ["Artist", "Guest"],
                }
            ],
        },
    }


def test_sync_supports_json_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from music_synchronizer import cli
    from music_synchronizer.models import SyncSummary

    class FakeSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def run(self) -> SyncSummary:
            return SyncSummary(
                fetched=3,
                written=3,
                archived=1,
                restored=2,
            )

    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(cli, "SyncService", FakeSyncService)

    result = CliRunner().invoke(app, ["sync", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "command": "sync",
        "data": {
            "summary": {
                "fetched": 3,
                "written": 3,
                "archived": 1,
                "restored": 2,
                "removed": 1,
            }
        },
    }


def test_show_config_json_uses_structured_config_error_when_settings_are_invalid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from pydantic import BaseModel

    from music_synchronizer import cli

    class _InvalidSettingsModel(BaseModel):
        yandex_music_token: str

    try:
        _InvalidSettingsModel.model_validate({})
    except Exception as error:
        validation_error = error
    else:  # pragma: no cover
        raise AssertionError("Expected settings validation to fail for an empty payload.")

    class InvalidSettings:
        model_fields = cli.Settings.model_fields

        def __init__(self) -> None:
            raise validation_error

    monkeypatch.setattr(cli, "Settings", InvalidSettings)

    result = CliRunner().invoke(app, ["show-config", "--json"])

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload == {
        "ok": False,
        "command": "show-config",
        "error": {
            "code": "CONFIG_MISSING_TOKEN",
            "message": "Missing required setting: YANDEX_MUSIC_TOKEN",
            "details": {
                "fields": ["YANDEX_MUSIC_TOKEN"],
            },
        },
    }


def test_list_json_uses_structured_validation_error_for_invalid_filters() -> None:
    result = CliRunner().invoke(app, ["list", "--json"])

    assert result.exit_code == 2
    payload = json.loads(result.output)
    assert payload == {
        "ok": False,
        "command": "list",
        "error": {
            "code": "INVALID_ARGUMENT",
            "message": "Exactly one of --tag or --artist must be provided.",
            "details": {},
        },
    }


def test_sync_json_uses_structured_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from music_synchronizer import cli

    class FailingSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def run(self) -> object:
            raise RuntimeError("boom")

    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(cli, "SyncService", FailingSyncService)

    result = CliRunner().invoke(app, ["sync", "--json"])

    assert result.exit_code == 4
    payload = json.loads(result.output)
    assert payload == {
        "ok": False,
        "command": "sync",
        "error": {
            "code": "SYNC_FAILED",
            "message": "boom",
            "details": {},
        },
    }


def test_sync_json_uses_internal_error_exit_code_for_unexpected_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from music_synchronizer import cli

    class ExplodingSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def run(self) -> object:
            raise ValueError("unexpected")

    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(cli, "SyncService", ExplodingSyncService)

    result = CliRunner().invoke(app, ["sync", "--json"])

    assert result.exit_code == 5
    payload = json.loads(result.output)
    assert payload == {
        "ok": False,
        "command": "sync",
        "error": {
            "code": "UNEXPECTED_ERROR",
            "message": "unexpected",
            "details": {},
        },
    }
