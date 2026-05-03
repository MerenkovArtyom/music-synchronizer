from __future__ import annotations

from datetime import datetime, timezone

from music_synchronizer.config import Settings
from music_synchronizer.models import SyncSummary
from music_synchronizer.obsidian import ObsidianExporter
from music_synchronizer.yandex_client import YandexMusicClient


class SyncService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = YandexMusicClient(token=settings.yandex_music_token)
        self.exporter = ObsidianExporter(settings.obsidian_vault_path)

    def run(self) -> SyncSummary:
        tracks = self.client.fetch_liked_tracks()
        export_summary = self.exporter.sync(tracks, synced_at=datetime.now(timezone.utc))
        return SyncSummary(
            fetched=len(tracks),
            written=export_summary.written,
            archived=export_summary.archived,
            restored=export_summary.restored,
        )
