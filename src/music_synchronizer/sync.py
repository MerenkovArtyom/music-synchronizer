from __future__ import annotations

from datetime import datetime, timezone

from music_synchronizer.config import Settings
from music_synchronizer.models import (
    DashboardData,
    MonthlyTopEntry,
    RelistenRecommendationEntry,
    SavedTrackInfo,
    SyncSummary,
)
from music_synchronizer.obsidian import ObsidianExporter
from music_synchronizer.yandex_client import YandexMusicClient

MONTHLY_TOP_LIMIT = 10
RECENT_PROFILE_LIMIT = 20
RECOMMENDATION_LIMIT = 10


class SyncService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = YandexMusicClient(token=settings.yandex_music_token)
        self.exporter = ObsidianExporter(settings.obsidian_vault_path)

    def run(self) -> SyncSummary:
        synced_at = datetime.now(timezone.utc)
        tracks = self.client.fetch_liked_tracks(reference_time=synced_at)
        return self.exporter.sync(tracks, synced_at=synced_at)

    def dashboard_data(self) -> DashboardData:
        return self.exporter.dashboard_data()

    def refresh_dashboard(self) -> DashboardData:
        return self.exporter.refresh_dashboard()

    def top_listen_entries(self, *, most: bool) -> list[MonthlyTopEntry]:
        tracks = self.exporter.top_listen_tracks()
        return self._build_top_listen_entries(tracks, most=most)

    def relisten_recommendations(self, *, include_archived: bool) -> list[RelistenRecommendationEntry]:
        tracks = self.exporter.recommendation_tracks(include_archived=include_archived)
        return self._build_relisten_recommendations(tracks, include_archived=include_archived)

    def _build_top_listen_entries(
        self,
        tracks: list[SavedTrackInfo],
        *,
        most: bool,
    ) -> list[MonthlyTopEntry]:
        sorted_tracks = sorted(
            tracks,
            key=lambda track: (
                -(track.monthly_listens or 0) if most else (track.monthly_listens or 0),
                track.source_position if track.source_position is not None else float("inf"),
            ),
        )

        return [
            MonthlyTopEntry(
                title=track.title,
                artists=track.artists,
                monthly_listens=track.monthly_listens or 0,
                source_position=track.source_position or 0,
            )
            for track in sorted_tracks[:MONTHLY_TOP_LIMIT]
        ]

    def _build_relisten_recommendations(
        self,
        tracks: list[SavedTrackInfo],
        *,
        include_archived: bool,
    ) -> list[RelistenRecommendationEntry]:
        active_track_ids = self._active_track_ids(tracks, include_archived=include_archived)
        profile_tracks = sorted(
            [
                track
                for track in tracks
                if track.monthly_listens is not None
                and track.monthly_listens > 0
                and track.track_id in active_track_ids
            ],
            key=lambda track: (
                -(track.monthly_listens or 0),
                track.source_position if track.source_position is not None else float("inf"),
                track.title.casefold(),
            ),
        )[:RECENT_PROFILE_LIMIT]
        if not profile_tracks:
            return []

        recent_track_ids = {track.track_id for track in profile_tracks if track.track_id is not None}
        artist_profile = self._normalized_values(
            artist for track in profile_tracks for artist in track.artists
        )
        genre_profile = self._normalized_values(
            genre for track in profile_tracks for genre in track.system_tags
        )
        user_tag_profile = self._normalized_values(
            tag for track in profile_tracks for tag in track.user_tags
        )
        recommendations: list[RelistenRecommendationEntry] = []

        for track in tracks:
            if track.track_id in recent_track_ids:
                continue

            matched_artists = self._matching_values(track.artists, artist_profile)
            matched_genres = self._matching_values(track.system_tags, genre_profile)
            matched_user_tags = self._matching_values(track.user_tags, user_tag_profile)
            if not matched_artists and not matched_genres and not matched_user_tags:
                continue

            score = (
                len(matched_artists) * 10
                + len(matched_genres) * 4
                + len(matched_user_tags) * 2
                + self._staleness_bonus(track.monthly_listens)
            )
            recommendations.append(
                RelistenRecommendationEntry(
                    title=track.title,
                    artists=track.artists,
                    monthly_listens=track.monthly_listens,
                    position=track.source_position,
                    archived=track.track_id not in active_track_ids,
                    matched_artists=matched_artists,
                    matched_genres=matched_genres,
                    matched_user_tags=matched_user_tags,
                    score=score,
                )
            )

        recommendations.sort(
            key=lambda entry: (
                -entry.score,
                entry.monthly_listens if entry.monthly_listens is not None else -1,
                entry.position if entry.position is not None else float("inf"),
                entry.title.casefold(),
            )
        )
        return recommendations[:RECOMMENDATION_LIMIT]

    def _active_track_ids(self, tracks: list[SavedTrackInfo], *, include_archived: bool) -> set[str]:
        if not include_archived:
            return {track.track_id for track in tracks if track.track_id is not None}

        return {
            track.track_id
            for track in self.exporter.top_listen_tracks()
            if track.track_id is not None
        }

    def _normalized_values(self, values: object) -> set[str]:
        normalized: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            cleaned = value.strip().casefold()
            if cleaned:
                normalized.add(cleaned)
        return normalized

    def _matching_values(self, values: list[str], profile: set[str]) -> list[str]:
        matched: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = value.strip()
            key = cleaned.casefold()
            if not cleaned or key not in profile or key in seen:
                continue
            matched.append(cleaned)
            seen.add(key)
        return matched

    def _staleness_bonus(self, monthly_listens: int | None) -> int:
        if monthly_listens is None:
            return 6
        if monthly_listens <= 0:
            return 5
        if monthly_listens == 1:
            return 4
        if monthly_listens <= 3:
            return 2
        return 0
