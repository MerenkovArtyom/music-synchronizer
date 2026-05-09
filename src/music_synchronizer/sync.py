from __future__ import annotations

from datetime import datetime, timezone

from music_synchronizer.config import Settings
from music_synchronizer.models import MonthlyTopEntry, SavedTrackInfo, TrackInfo, SyncSummary
from music_synchronizer.obsidian import ObsidianExporter
from music_synchronizer.yandex_client import YandexMusicClient

MONTHLY_TOP_LIMIT = 10


class SyncService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = YandexMusicClient(token=settings.yandex_music_token)
        self.exporter = ObsidianExporter(settings.obsidian_vault_path)

    def run(self) -> SyncSummary:
        synced_at = datetime.now(timezone.utc)
        tracks = self.client.fetch_liked_tracks(reference_time=synced_at)
        return self.exporter.sync(tracks, synced_at=synced_at)

    def top_listen_entries(self, *, most: bool) -> list[MonthlyTopEntry]:
        tracks = self.exporter.top_listen_tracks()
        return self._build_top_listen_entries(tracks, most=most)

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
