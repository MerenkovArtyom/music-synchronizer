from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Literal

from music_synchronizer.config import Settings
from music_synchronizer.models import DashboardData, DashboardStatEntry, MonthlyTopEntry, SavedTrackInfo, TrackDashboardEntry
from music_synchronizer.sync import SyncService

BackendCommand = Literal["show-config", "sync", "dashboard", "list", "top-listen"]
TopListenMode = Literal["most", "least"]
ListFilterKind = Literal["tag", "artist"]


def _camelize(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


def _camelize_structure(value: Any) -> Any:
    if is_dataclass(value):
        return _camelize_structure(asdict(value))
    if isinstance(value, dict):
        return {_camelize(key): _camelize_structure(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_camelize_structure(item) for item in value]
    return value


def _most_listened_track_payload(entry: TrackDashboardEntry | None) -> dict[str, Any] | None:
    if entry is None:
        return None

    return {
        "title": entry.title,
        "artists": entry.artists,
        "monthlyListens": entry.monthly_listens,
    }


def _dashboard_stat_payload(
    entry: DashboardStatEntry | None,
    *,
    include_monthly_listens: bool,
) -> dict[str, Any] | None:
    if entry is None:
        return None

    payload: dict[str, Any] = {
        "name": entry.name,
        "tracks": entry.count,
    }
    if include_monthly_listens:
        payload["monthlyListens"] = entry.monthly_listens if entry.monthly_listens is not None else 0
    return payload


def _saved_track_payload(track: SavedTrackInfo) -> dict[str, Any]:
    return {
        "title": track.title,
        "artists": track.artists,
    }


def _top_listen_entry_payload(entry: MonthlyTopEntry) -> dict[str, Any]:
    return {
        "title": entry.title,
        "artists": entry.artists,
        "monthlyListens": entry.monthly_listens,
        "position": entry.source_position,
    }


class MusicSyncApp:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.service = SyncService(self.settings)

    def show_config(self) -> dict[str, Any]:
        return {
            "config": {
                "yandexMusicTokenPresent": bool(self.settings.yandex_music_token),
                "obsidianVaultPath": str(self.settings.obsidian_vault_path),
                "logLevel": self.settings.log_level,
            }
        }

    def sync(self) -> dict[str, Any]:
        summary = self.service.run()
        return {
            "summary": {
                "added": summary.added,
                "unchanged": summary.unchanged,
                "archived": summary.removed,
                "removed": summary.removed,
            }
        }

    def dashboard(self) -> dict[str, Any]:
        dashboard = self.service.refresh_dashboard()
        return {
            "path": str(self.settings.obsidian_vault_path / "dashboard.md"),
            "summary": self._dashboard_summary_payload(dashboard),
            "topTags": [
                _dashboard_stat_payload(entry, include_monthly_listens=False) for entry in dashboard.top_tags
            ],
            "topArtists": [
                _dashboard_stat_payload(entry, include_monthly_listens=True)
                for entry in dashboard.top_artists
            ],
        }

    def list_tracks(self, *, kind: ListFilterKind, value: str) -> dict[str, Any]:
        exporter = self.service.exporter
        if kind == "tag":
            tracks = exporter.list_tracks_by_tag(value)
        else:
            tracks = exporter.list_tracks_by_artist(value)

        return {
            "filter": {
                "kind": kind,
                "value": value,
            },
            "tracks": [_saved_track_payload(track) for track in tracks],
        }

    def top_listen(self, *, mode: TopListenMode) -> dict[str, Any]:
        entries = self.service.top_listen_entries(most=mode == "most")
        payload = [_top_listen_entry_payload(entry) for entry in entries]
        return {
            "mostPlayed": payload if mode == "most" else [],
            "leastPlayed": payload if mode == "least" else [],
        }

    def run_command(self, command: BackendCommand, **kwargs: Any) -> dict[str, Any]:
        try:
            data = self._dispatch(command, **kwargs)
        except Exception as error:
            return {
                "ok": False,
                "command": command,
                "error": {
                    "code": _error_code(command),
                    "message": str(error),
                    "details": {},
                },
            }

        return {
            "ok": True,
            "command": command,
            "data": _camelize_structure(data),
        }

    def _dispatch(self, command: BackendCommand, **kwargs: Any) -> dict[str, Any]:
        if command == "show-config":
            return self.show_config()
        if command == "sync":
            return self.sync()
        if command == "dashboard":
            return self.dashboard()
        if command == "list":
            return self.list_tracks(kind=kwargs["kind"], value=kwargs["value"])
        return self.top_listen(mode=kwargs["mode"])

    def _dashboard_summary_payload(self, dashboard: DashboardData) -> dict[str, Any]:
        return {
            "likedTracks": dashboard.liked_tracks_count,
            "removedTracks": dashboard.removed_tracks_count,
            "totalTracks": dashboard.total_tracks_count,
            "totalDuration": dashboard.total_duration_text,
            "monthlyListensKnown": dashboard.monthly_listens_known_count,
            "monthlyListensCoveragePercent": dashboard.monthly_listens_coverage_percent,
            "averageMonthlyListens": dashboard.average_monthly_listens,
            "medianMonthlyListens": dashboard.median_monthly_listens,
            "mostListenedTrack": _most_listened_track_payload(dashboard.most_listened_track),
            "mostListenedArtist": _dashboard_stat_payload(
                dashboard.most_listened_artist,
                include_monthly_listens=True,
            ),
            "mostUsedTag": _dashboard_stat_payload(
                dashboard.most_used_tag,
                include_monthly_listens=False,
            ),
            "longestTrack": (
                None
                if dashboard.longest_track is None
                else {
                    "title": dashboard.longest_track.title,
                    "artists": dashboard.longest_track.artists,
                    "duration": dashboard.longest_track.duration_text,
                }
            ),
        }


def _error_code(command: BackendCommand) -> str:
    if command == "show-config":
        return "SHOW_CONFIG_FAILED"
    if command == "sync":
        return "SYNC_FAILED"
    if command == "dashboard":
        return "DASHBOARD_FAILED"
    if command == "list":
        return "LIST_FAILED"
    return "TOP_LISTEN_FAILED"
