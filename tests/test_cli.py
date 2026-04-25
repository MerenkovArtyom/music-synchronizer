from pathlib import Path

import pytest
from typer.testing import CliRunner

from music_synchronizer.cli import app


def test_help_shows_sync_placeholder() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "sync" in result.output
    assert "show-config" in result.output


def test_sync_creates_structured_obsidian_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from music_synchronizer import cli
    from music_synchronizer.models import TrackInfo

    class FakeSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def run(self) -> int:
            vault = self.settings.obsidian_vault_path
            (vault / "tracks").mkdir(parents=True, exist_ok=True)
            (vault / "tracks" / "Song.md").write_text(
                TrackInfo(
                    track_id="1",
                    title="Song",
                    artists=["Artist"],
                    album="Album",
                    tags=["rock"],
                    duration_seconds=180,
                    source_position=1,
                    yandex_url="https://music.yandex.ru/track/1",
                ).title,
                encoding="utf-8",
            )
            return 1

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

    assert result.exit_code == 1
    assert "Sync failed: boom" in result.output
    assert not (tmp_path / "playlist.md").exists()
    assert not (tmp_path / "tracks").exists()
