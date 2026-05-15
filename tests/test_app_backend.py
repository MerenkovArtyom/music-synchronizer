from pathlib import Path

import pytest

from music_synchronizer.app import MusicSyncApp
from music_synchronizer.config import Settings
from music_synchronizer.models import DashboardData, DashboardStatEntry, MonthlyTopEntry, TrackDashboardEntry


def _settings(tmp_path: Path) -> Settings:
    return Settings.model_construct(
        yandex_music_token="token",
        obsidian_vault_path=tmp_path,
        log_level="INFO",
    )


def _dashboard_data() -> DashboardData:
    return DashboardData(
        liked_tracks_count=3,
        removed_tracks_count=1,
        total_tracks_count=4,
        total_duration_seconds=720,
        total_duration_text="12:00",
        monthly_listens_known_count=2,
        monthly_listens_coverage_percent=66.67,
        average_monthly_listens=5.0,
        median_monthly_listens=5.0,
        most_listened_track=TrackDashboardEntry(
            title="First",
            artists=["Artist A"],
            monthly_listens=7,
            duration_seconds=240,
            duration_text="4:00",
        ),
        most_listened_artist=DashboardStatEntry(
            name="Artist A",
            count=2,
            monthly_listens=10,
        ),
        most_used_tag=DashboardStatEntry(name="indie", count=2),
        longest_track=TrackDashboardEntry(
            title="Third",
            artists=["Artist B"],
            monthly_listens=0,
            duration_seconds=300,
            duration_text="5:00",
        ),
        top_tags=[
            DashboardStatEntry(name="indie", count=2),
            DashboardStatEntry(name="focus", count=2),
        ],
        top_artists=[
            DashboardStatEntry(name="Artist A", count=2, monthly_listens=10),
            DashboardStatEntry(name="Artist B", count=1, monthly_listens=0),
        ],
    )


def test_show_config_returns_machine_readable_data(tmp_path: Path) -> None:
    result = MusicSyncApp(settings=_settings(tmp_path)).show_config()

    assert result == {
        "config": {
            "yandexMusicTokenPresent": True,
            "obsidianVaultPath": str(tmp_path),
            "logLevel": "INFO",
        }
    }


def test_dashboard_returns_machine_readable_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = MusicSyncApp(settings=_settings(tmp_path))
    dashboard = _dashboard_data()
    monkeypatch.setattr(app.service, "refresh_dashboard", lambda: dashboard)

    result = app.dashboard()

    assert result == {
        "path": str(tmp_path / "dashboard.md"),
        "summary": {
            "likedTracks": 3,
            "removedTracks": 1,
            "totalTracks": 4,
            "totalDuration": "12:00",
            "monthlyListensKnown": 2,
            "monthlyListensCoveragePercent": 66.67,
            "averageMonthlyListens": 5.0,
            "medianMonthlyListens": 5.0,
            "mostListenedTrack": {
                "title": "First",
                "artists": ["Artist A"],
                "monthlyListens": 7,
            },
            "mostListenedArtist": {
                "name": "Artist A",
                "monthlyListens": 10,
                "tracks": 2,
            },
            "mostUsedTag": {
                "name": "indie",
                "tracks": 2,
            },
            "longestTrack": {
                "title": "Third",
                "artists": ["Artist B"],
                "duration": "5:00",
            },
        },
        "topTags": [
            {"name": "indie", "tracks": 2},
            {"name": "focus", "tracks": 2},
        ],
        "topArtists": [
            {"name": "Artist A", "monthlyListens": 10, "tracks": 2},
            {"name": "Artist B", "monthlyListens": 0, "tracks": 1},
        ],
    }


def test_top_listen_returns_most_or_least_entries(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = MusicSyncApp(settings=_settings(tmp_path))
    entries = [
        MonthlyTopEntry(
            title="Loud Song",
            artists=["Artist", "Guest"],
            monthly_listens=9,
            source_position=2,
        )
    ]
    monkeypatch.setattr(app.service, "top_listen_entries", lambda *, most: entries if most else [])

    assert app.top_listen(mode="most") == {
        "mostPlayed": [
            {
                "title": "Loud Song",
                "artists": ["Artist", "Guest"],
                "monthlyListens": 9,
                "position": 2,
            }
        ],
        "leastPlayed": [],
    }
    assert app.top_listen(mode="least") == {"mostPlayed": [], "leastPlayed": []}


def test_backend_command_runner_wraps_domain_errors(tmp_path: Path) -> None:
    app = MusicSyncApp(settings=_settings(tmp_path))

    def raise_dashboard_error() -> dict[str, object]:
        raise RuntimeError("dashboard unavailable")

    app.dashboard = raise_dashboard_error  # type: ignore[method-assign]

    result = app.run_command("dashboard")

    assert result == {
        "ok": False,
        "command": "dashboard",
        "error": {
            "code": "DASHBOARD_FAILED",
            "message": "dashboard unavailable",
            "details": {},
        },
    }


def test_backend_command_runner_wraps_permission_errors(tmp_path: Path) -> None:
    app = MusicSyncApp(settings=_settings(tmp_path))

    def raise_permission_error() -> dict[str, object]:
        raise PermissionError("[Errno 1] Operation not permitted: '/vault/dashboard.md'")

    app.dashboard = raise_permission_error  # type: ignore[method-assign]

    result = app.run_command("dashboard")

    assert result == {
        "ok": False,
        "command": "dashboard",
        "error": {
            "code": "DASHBOARD_FAILED",
            "message": "[Errno 1] Operation not permitted: '/vault/dashboard.md'",
            "details": {},
        },
    }
