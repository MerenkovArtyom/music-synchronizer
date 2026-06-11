from __future__ import annotations

from dataclasses import asdict, is_dataclass
import os
from pathlib import Path
import tempfile
from typing import Any, Literal

from music_synchronizer.backend_contracts import (
    BackendCommand,
    ListFilterKind,
    TopListenMode,
    build_error_envelope,
    build_success_envelope,
)
from music_synchronizer.config import Settings, raw_config_values
from music_synchronizer.models import (
    DashboardData,
    DashboardStatEntry,
    DiscoverySummary,
    DiscoveryTrackInfo,
    MonthlyTopEntry,
    RelistenRecommendationEntry,
    SavedTrackInfo,
    TrackDashboardEntry,
    VaultData,
)
from music_synchronizer.sync import SyncService
from music_synchronizer.yandex_client import YandexMusicAuthError, YandexMusicClient, YandexMusicUnavailableError


class BackendCommandError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


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


def _recommendation_entry_payload(entry: RelistenRecommendationEntry) -> dict[str, Any]:
    return {
        "title": entry.title,
        "artists": entry.artists,
        "monthlyListens": entry.monthly_listens,
        "position": entry.position,
        "archived": entry.archived,
        "matchedArtists": entry.matched_artists,
        "matchedGenres": entry.matched_genres,
        "matchedUserTags": entry.matched_user_tags,
        "score": entry.score,
        "explain": entry.explain,
    }


def _discovery_summary_payload(summary: DiscoverySummary) -> dict[str, Any]:
    return {
        "added": summary.added,
        "skipped": summary.skipped,
        "removedLiked": summary.removed_liked,
        "cleared": summary.cleared,
        "total": summary.total,
    }


def _discovery_track_payload(entry: DiscoveryTrackInfo) -> dict[str, Any]:
    return {
        "trackId": entry.track_id,
        "title": entry.title,
        "artists": entry.artists,
        "album": entry.album,
        "systemTags": entry.system_tags,
        "year": entry.year,
        "coverUrl": entry.cover_url,
        "durationSeconds": entry.duration_seconds,
        "yandexUrl": entry.yandex_url,
        "monthlyListens": entry.monthly_listens,
        "discoverySources": entry.discovery_sources,
        "explain": entry.explain,
    }


def _config_payload(settings: Settings) -> dict[str, Any]:
    return {
        "yandexMusicToken": settings.yandex_music_token,
        "yandexMusicTokenPresent": bool(settings.yandex_music_token),
        "obsidianVaultPath": str(settings.obsidian_vault_path),
        "discoveryPlaylistName": settings.discovery_playlist_name,
        "logLevel": settings.log_level,
    }


def _serialize_env_value(value: str) -> str:
    if value == "" or any(character in value for character in (' ', "\n", "\r", "\t", "#", '"', "'")):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _config_target_path() -> Path:
    explicit_path = os.getenv("MUSIC_SYNC_CONFIG_PATH")
    if not explicit_path:
        raise ValueError("MUSIC_SYNC_CONFIG_PATH is not configured.")
    return Path(explicit_path).expanduser()


def _write_config_file(target_path: Path, settings: Settings) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            f"YANDEX_MUSIC_TOKEN={_serialize_env_value(settings.yandex_music_token)}",
            f"OBSIDIAN_VAULT_PATH={_serialize_env_value(str(settings.obsidian_vault_path))}",
            "YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME="
            f"{_serialize_env_value(settings.discovery_playlist_name)}",
            f"LOG_LEVEL={_serialize_env_value(settings.log_level)}",
            "",
        ]
    )
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_file.write(content)
        temp_path = Path(temporary_file.name)
    temp_path.replace(target_path)


class MusicSyncApp:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.service = SyncService(self.settings)

    def show_config(self) -> dict[str, Any]:
        if not os.getenv("MUSIC_SYNC_CONFIG_PATH"):
            return {"config": _config_payload(self.settings)}

        raw_values = raw_config_values()
        return {
            "config": {
                "yandexMusicToken": raw_values.get("YANDEX_MUSIC_TOKEN", ""),
                "yandexMusicTokenPresent": bool(raw_values.get("YANDEX_MUSIC_TOKEN", "").strip()),
                "obsidianVaultPath": raw_values.get("OBSIDIAN_VAULT_PATH", ""),
                "discoveryPlaylistName": raw_values.get(
                    "YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME",
                    self.settings.discovery_playlist_name,
                ),
                "logLevel": raw_values.get("LOG_LEVEL", self.settings.log_level),
            }
        }

    def save_config(
        self,
        *,
        yandex_music_token: str,
        obsidian_vault_path: str,
        discovery_playlist_name: str,
        log_level: str,
    ) -> dict[str, Any]:
        if not yandex_music_token.strip():
            raise BackendCommandError(
                "SETUP_MISSING_TOKEN",
                "Добавьте токен Яндекс Музыки, чтобы сохранить настройки.",
            )
        if not obsidian_vault_path.strip():
            raise BackendCommandError(
                "SETUP_MISSING_VAULT",
                "Выберите папку Obsidian vault, чтобы сохранить настройки.",
            )
        validated_settings = Settings.model_validate(
            {
                "YANDEX_MUSIC_TOKEN": yandex_music_token,
                "OBSIDIAN_VAULT_PATH": obsidian_vault_path,
                "YANDEX_MUSIC_DISCOVERY_PLAYLIST_NAME": discovery_playlist_name,
                "LOG_LEVEL": log_level,
            }
        )
        target_path = _config_target_path()
        self._validate_yandex_token(yandex_music_token)
        _write_config_file(target_path, validated_settings)
        self.settings = validated_settings
        self.service = SyncService(self.settings)
        return {"config": _config_payload(self.settings)}

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

    def recommend(self, *, include_archived: bool) -> dict[str, Any]:
        entries = self.service.relisten_recommendations(include_archived=include_archived)
        return {
            "includeArchived": include_archived,
            "recommendations": [_recommendation_entry_payload(entry) for entry in entries],
        }

    def discovery(self, *, clear: bool) -> dict[str, Any]:
        if clear:
            summary = self.service.clear_discovery_recommendations()
            return {
                "summary": _discovery_summary_payload(summary),
                "recommendations": [],
            }

        entries, summary = self.service.discovery_recommendations()
        return {
            "summary": _discovery_summary_payload(summary),
            "recommendations": [_discovery_track_payload(entry) for entry in entries],
        }

    def vault(self, *, selected_path: str | None) -> dict[str, Any]:
        payload = self.service.exporter.vault_view(selected_path=selected_path)
        return _camelize_structure(payload)

    def run_command(self, command: BackendCommand, **kwargs: Any) -> dict[str, Any]:
        try:
            data = self._dispatch(command, **kwargs)
        except BackendCommandError as error:
            return build_error_envelope(command, error.code, str(error), error.details)
        except Exception as error:
            mapped_error = _map_runtime_error(command, error)
            if mapped_error is not None:
                return build_error_envelope(
                    command,
                    mapped_error.code,
                    str(mapped_error),
                    mapped_error.details,
                )
            return build_error_envelope(command, _error_code(command), str(error), {})

        return build_success_envelope(command, _camelize_structure(data))

    def _dispatch(self, command: BackendCommand, **kwargs: Any) -> dict[str, Any]:
        if command == "show-config":
            return self.show_config()
        if command == "save-config":
            return self.save_config(
                yandex_music_token=kwargs["yandex_music_token"],
                obsidian_vault_path=kwargs["obsidian_vault_path"],
                discovery_playlist_name=kwargs["discovery_playlist_name"],
                log_level=kwargs["log_level"],
            )
        if command == "sync":
            return self.sync()
        if command == "dashboard":
            return self.dashboard()
        if command == "list":
            return self.list_tracks(kind=kwargs["kind"], value=kwargs["value"])
        if command == "recommend":
            return self.recommend(include_archived=kwargs["include_archived"])
        if command == "discovery":
            return self.discovery(clear=kwargs["clear"])
        if command == "vault":
            return self.vault(selected_path=kwargs.get("selected_path"))
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

    def _validate_yandex_token(self, token: str) -> None:
        try:
            YandexMusicClient(token=token).validate_token()
        except YandexMusicAuthError as error:
            raise BackendCommandError(
                "YANDEX_AUTH_INVALID",
                "Токен Яндекс Музыки не подошёл. Проверьте токен и попробуйте сохранить настройки снова.",
            ) from error
        except YandexMusicUnavailableError as error:
            raise BackendCommandError(
                "YANDEX_API_UNAVAILABLE",
                "Не удалось связаться с Яндекс Музыкой. Проверьте подключение и попробуйте ещё раз позже.",
            ) from error


def _error_code(command: BackendCommand) -> str:
    if command == "show-config":
        return "SHOW_CONFIG_FAILED"
    if command == "save-config":
        return "SAVE_CONFIG_FAILED"
    if command == "sync":
        return "SYNC_FAILED"
    if command == "dashboard":
        return "DASHBOARD_FAILED"
    if command == "list":
        return "LIST_FAILED"
    if command == "recommend":
        return "RECOMMEND_FAILED"
    if command == "discovery":
        return "DISCOVERY_FAILED"
    if command == "vault":
        return "VAULT_FAILED"
    return "TOP_LISTEN_FAILED"


def _map_runtime_error(command: BackendCommand, error: Exception) -> BackendCommandError | None:
    if isinstance(error, YandexMusicAuthError):
        return BackendCommandError(
            "YANDEX_AUTH_INVALID",
            "Токен Яндекс Музыки не подошёл. Проверьте токен и попробуйте сохранить настройки снова.",
        )
    if isinstance(error, YandexMusicUnavailableError):
        return BackendCommandError(
            "YANDEX_API_UNAVAILABLE",
            "Не удалось связаться с Яндекс Музыкой. Проверьте подключение и попробуйте ещё раз позже.",
        )
    return None
