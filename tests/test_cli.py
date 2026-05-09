from pathlib import Path

import pytest
from typer.testing import CliRunner

from music_synchronizer.cli import app
from music_synchronizer.models import MonthlyTopEntry


def test_help_shows_sync_placeholder() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "list" in result.output
    assert "monthly-top" not in result.output
    assert "sync" in result.output
    assert "show-config" in result.output
    assert "top-listen" in result.output


def test_top_listen_most_prints_most_played_section(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    entries = [
        MonthlyTopEntry(
            title="Loud Song",
            artists=["Artist", "Guest"],
            monthly_listens=9,
            source_position=2,
        )
    ]

    class FakeSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def top_listen_entries(self, *, most: bool) -> list[MonthlyTopEntry]:
            assert most is True
            return entries

    monkeypatch.setattr("music_synchronizer.cli.SyncService", FakeSyncService)

    result = CliRunner().invoke(app, ["top-listen", "--most"])

    assert result.exit_code == 0
    assert result.output.strip().splitlines() == [
        "Most Played:",
        "1. Loud Song - Artist, Guest | monthly_listens=9 | position=2",
    ]


def test_top_listen_least_prints_least_played_section(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    entries = [
        MonthlyTopEntry(
            title="Quiet Song",
            artists=["Solo"],
            monthly_listens=1,
            source_position=7,
        )
    ]

    class FakeSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def top_listen_entries(self, *, most: bool) -> list[MonthlyTopEntry]:
            assert most is False
            return entries

    monkeypatch.setattr("music_synchronizer.cli.SyncService", FakeSyncService)

    result = CliRunner().invoke(app, ["top-listen", "--least"])

    assert result.exit_code == 0
    assert result.output.strip().splitlines() == [
        "Least Played:",
        "1. Quiet Song - Solo | monthly_listens=1 | position=7",
    ]


def test_top_listen_reports_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    class FakeSyncService:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def top_listen_entries(self, *, most: bool) -> list[MonthlyTopEntry]:
            raise RuntimeError("history unavailable")

    monkeypatch.setattr("music_synchronizer.cli.SyncService", FakeSyncService)

    result = CliRunner().invoke(app, ["top-listen", "--most"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr.strip() == "Top listen failed: history unavailable"


def test_top_listen_requires_exactly_one_flag() -> None:
    result = CliRunner().invoke(app, ["top-listen"])

    assert result.exit_code == 2
    assert "Exactly one of --most or --least must be provided." in result.output


def test_top_listen_rejects_both_flags() -> None:
    result = CliRunner().invoke(app, ["top-listen", "--most", "--least"])

    assert result.exit_code == 2
    assert "Exactly one of --most or --least must be provided." in result.output


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
            return SyncSummary(added=1, unchanged=2, removed=3)

    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(cli, "SyncService", FakeSyncService)

    result = CliRunner().invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "Added: 1, unchanged: 2, removed: 3." in result.output
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

        def run(self) -> object:
            raise RuntimeError("boom")

    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "token")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    monkeypatch.setattr(cli, "SyncService", FailingSyncService)

    result = CliRunner().invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "Sync failed: boom" in result.output
    assert not (tmp_path / "playlist.md").exists()
    assert not (tmp_path / "tracks").exists()
