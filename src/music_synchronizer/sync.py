from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from music_synchronizer.config import Settings
from music_synchronizer.models import (
    DashboardData,
    DiscoverySummary,
    DiscoveryTrackInfo,
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
DISCOVERY_SEED_LIMIT = 8
DISCOVERY_LIMIT = 20
DISCOVERY_PRIMARY_ARTIST_LIMIT = 2
PRIMARY_ARTIST_RECOMMENDATION_LIMIT = 2


@dataclass(frozen=True, slots=True)
class _ScoredRelistenCandidate:
    entry: RelistenRecommendationEntry
    primary_artist_key: str | None
    secondary_artist_keys: tuple[str, ...]
    all_artist_keys: tuple[str, ...]


class SyncService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = YandexMusicClient(token=settings.yandex_music_token)
        self.exporter = ObsidianExporter(settings.obsidian_vault_path)

    def run(self) -> SyncSummary:
        synced_at = datetime.now(timezone.utc)
        tracks = self.client.fetch_liked_tracks(reference_time=synced_at)
        summary = self.exporter.sync(tracks, synced_at=synced_at)
        return summary

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

    def discovery_recommendations(self) -> tuple[list[DiscoveryTrackInfo], DiscoverySummary]:
        reference_time = datetime.now(timezone.utc)
        liked_tracks = self.client.fetch_liked_tracks(reference_time=reference_time)
        liked_track_ids = {track.track_id for track in liked_tracks}
        seed_track_ids = self.client.fetch_recent_liked_track_ids(
            liked_track_ids=liked_track_ids,
            reference_time=reference_time,
            limit=DISCOVERY_SEED_LIMIT,
        )
        if not seed_track_ids:
            summary = DiscoverySummary(added=0, skipped=0, removed_liked=0, cleared=0, total=len(self.exporter.read_discovery_tracks()))
            return [], summary

        existing_tracks = self.exporter.read_discovery_tracks()
        existing_track_ids = {track.track_id for track in existing_tracks}
        exclude_track_ids = liked_track_ids | existing_track_ids
        popular_candidates = self.client.fetch_popular_tracks_for_artist_seeds(seed_track_ids, exclude_track_ids)
        similar_candidates = self.client.fetch_similar_tracks(seed_track_ids, exclude_track_ids)
        recommendations = self._mix_discovery_candidates(popular_candidates, similar_candidates)
        summary = self.exporter.save_discovery_tracks(recommendations)
        self.client.sync_discovery_playlist(
            self.settings.discovery_playlist_name,
            recommendations + existing_tracks,
        )
        return recommendations, summary

    def clear_discovery_recommendations(self) -> DiscoverySummary:
        summary = self.exporter.clear_discovery_tracks()
        self.client.clear_playlist(self.settings.discovery_playlist_name)
        return summary

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
        candidates: list[_ScoredRelistenCandidate] = []

        for track in tracks:
            if track.track_id in recent_track_ids:
                continue

            candidate = self._build_relisten_candidate(
                track,
                active_track_ids=active_track_ids,
                artist_profile=artist_profile,
                genre_profile=genre_profile,
                user_tag_profile=user_tag_profile,
            )
            if candidate is not None:
                candidates.append(candidate)

        return self._select_relisten_recommendations(candidates)

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

    def _build_relisten_candidate(
        self,
        track: SavedTrackInfo,
        *,
        active_track_ids: set[str],
        artist_profile: set[str],
        genre_profile: set[str],
        user_tag_profile: set[str],
    ) -> _ScoredRelistenCandidate | None:
        matched_artists = self._matching_values(track.artists, artist_profile)
        matched_genres = self._matching_values(track.system_tags, genre_profile)
        matched_user_tags = self._matching_values(track.user_tags, user_tag_profile)
        if not matched_artists and not matched_genres and not matched_user_tags:
            return None

        artist_keys = self._normalized_artist_keys(track.artists)
        score = (
            len(matched_artists) * 7
            + len(matched_genres) * 5
            + len(matched_user_tags) * 4
            + self._staleness_bonus(track.monthly_listens)
        )
        return _ScoredRelistenCandidate(
            entry=RelistenRecommendationEntry(
                title=track.title,
                artists=track.artists,
                monthly_listens=track.monthly_listens,
                position=track.source_position,
                archived=track.track_id not in active_track_ids,
                matched_artists=matched_artists,
                matched_genres=matched_genres,
                matched_user_tags=matched_user_tags,
                score=score,
            ),
            primary_artist_key=artist_keys[0] if artist_keys else None,
            secondary_artist_keys=artist_keys[1:],
            all_artist_keys=artist_keys,
        )

    def _select_relisten_recommendations(
        self,
        candidates: list[_ScoredRelistenCandidate],
    ) -> list[RelistenRecommendationEntry]:
        selected: list[_ScoredRelistenCandidate] = []
        selected_artist_keys: set[str] = set()
        primary_artist_counts: dict[str, int] = {}
        remaining = list(candidates)

        while remaining and len(selected) < RECOMMENDATION_LIMIT:
            eligible = [
                candidate
                for candidate in remaining
                if candidate.primary_artist_key is None
                or primary_artist_counts.get(candidate.primary_artist_key, 0) < PRIMARY_ARTIST_RECOMMENDATION_LIMIT
            ]
            if not eligible:
                break

            best_candidate = min(
                eligible,
                key=lambda candidate: self._relisten_selection_key(
                    candidate,
                    selected_artist_keys=selected_artist_keys,
                ),
            )
            selected.append(best_candidate)
            remaining.remove(best_candidate)
            if best_candidate.primary_artist_key is not None:
                primary_artist_counts[best_candidate.primary_artist_key] = (
                    primary_artist_counts.get(best_candidate.primary_artist_key, 0) + 1
                )
            selected_artist_keys.update(best_candidate.all_artist_keys)

        return [candidate.entry for candidate in selected]

    def _relisten_selection_key(
        self,
        candidate: _ScoredRelistenCandidate,
        *,
        selected_artist_keys: set[str],
    ) -> tuple[float, int, int, int, float, float, str]:
        secondary_overlap_count = sum(
            1 for artist_key in candidate.secondary_artist_keys if artist_key in selected_artist_keys
        )
        adjusted_score = candidate.entry.score - secondary_overlap_count
        return (
            -adjusted_score,
            -candidate.entry.score,
            secondary_overlap_count,
            self._artist_overlap_count(candidate.all_artist_keys, selected_artist_keys),
            candidate.entry.monthly_listens if candidate.entry.monthly_listens is not None else -1,
            candidate.entry.position if candidate.entry.position is not None else float("inf"),
            candidate.entry.title.casefold(),
        )

    def _normalized_artist_keys(self, artists: list[str]) -> tuple[str, ...]:
        normalized: list[str] = []
        seen: set[str] = set()
        for artist in artists:
            cleaned = artist.strip().casefold()
            if not cleaned or cleaned in seen:
                continue
            normalized.append(cleaned)
            seen.add(cleaned)
        return tuple(normalized)

    def _discovery_primary_artist_key(self, track: DiscoveryTrackInfo) -> str | None:
        if not track.artists:
            return None
        cleaned = track.artists[0].strip().casefold()
        return cleaned or None

    def _artist_overlap_count(self, artist_keys: tuple[str, ...], selected_artist_keys: set[str]) -> int:
        return sum(1 for artist_key in artist_keys if artist_key in selected_artist_keys)

    def _staleness_bonus(self, monthly_listens: int | None) -> int:
        if monthly_listens is None:
            return 7
        if monthly_listens <= 0:
            return 6
        if monthly_listens == 1:
            return 4
        if monthly_listens <= 3:
            return 2
        return 0

    def _mix_discovery_candidates(
        self,
        popular_candidates: list[DiscoveryTrackInfo],
        similar_candidates: list[DiscoveryTrackInfo],
    ) -> list[DiscoveryTrackInfo]:
        target_per_source = DISCOVERY_LIMIT // 2
        merged_candidates: dict[str, DiscoveryTrackInfo] = {}
        ordered_ids: list[str] = []
        primary_artist_counts: dict[str, int] = {}

        def add_candidate(track: DiscoveryTrackInfo) -> bool:
            existing = merged_candidates.get(track.track_id)
            if existing is None:
                primary_artist_key = self._discovery_primary_artist_key(track)
                if (
                    primary_artist_key is not None
                    and primary_artist_counts.get(primary_artist_key, 0) >= DISCOVERY_PRIMARY_ARTIST_LIMIT
                ):
                    return False
                merged_candidates[track.track_id] = track
                ordered_ids.append(track.track_id)
                if primary_artist_key is not None:
                    primary_artist_counts[primary_artist_key] = primary_artist_counts.get(primary_artist_key, 0) + 1
                return True

            merged_sources = list(existing.discovery_sources)
            for source in track.discovery_sources:
                if source not in merged_sources:
                    merged_sources.append(source)
            merged_candidates[track.track_id] = DiscoveryTrackInfo(
                track_id=existing.track_id,
                title=existing.title,
                artists=existing.artists,
                album=existing.album,
                system_tags=existing.system_tags,
                year=existing.year,
                cover_url=existing.cover_url,
                duration_seconds=existing.duration_seconds,
                yandex_url=existing.yandex_url,
                monthly_listens=existing.monthly_listens,
                discovery_sources=merged_sources,
            )
            return False

        selected_popular = popular_candidates[:target_per_source]
        selected_similar = similar_candidates[:target_per_source]
        popular_index = 0
        similar_index = 0
        popular_added = 0
        similar_added = 0
        prefer_popular = True

        while (
            len(ordered_ids) < DISCOVERY_LIMIT
            and (
                (popular_added < target_per_source and popular_index < len(selected_popular))
                or (similar_added < target_per_source and similar_index < len(selected_similar))
            )
        ):
            added = False
            if prefer_popular and popular_added < target_per_source and popular_index < len(selected_popular):
                if add_candidate(selected_popular[popular_index]):
                    popular_added += 1
                    added = True
                popular_index += 1
            elif (not prefer_popular) and similar_added < target_per_source and similar_index < len(selected_similar):
                if add_candidate(selected_similar[similar_index]):
                    similar_added += 1
                    added = True
                similar_index += 1
            elif popular_added < target_per_source and popular_index < len(selected_popular):
                if add_candidate(selected_popular[popular_index]):
                    popular_added += 1
                    added = True
                popular_index += 1
            elif similar_added < target_per_source and similar_index < len(selected_similar):
                if add_candidate(selected_similar[similar_index]):
                    similar_added += 1
                    added = True
                similar_index += 1
            else:
                break

            if added:
                prefer_popular = not prefer_popular

        if popular_added < target_per_source:
            for track in similar_candidates[target_per_source:]:
                if len(ordered_ids) >= DISCOVERY_LIMIT:
                    break
                add_candidate(track)
        if similar_added < target_per_source:
            for track in popular_candidates[target_per_source:]:
                if len(ordered_ids) >= DISCOVERY_LIMIT:
                    break
                add_candidate(track)

        if len(ordered_ids) < DISCOVERY_LIMIT:
            for track in popular_candidates[target_per_source:] + similar_candidates[target_per_source:]:
                if len(ordered_ids) >= DISCOVERY_LIMIT:
                    break
                add_candidate(track)

        return [merged_candidates[track_id] for track_id in ordered_ids[:DISCOVERY_LIMIT]]
