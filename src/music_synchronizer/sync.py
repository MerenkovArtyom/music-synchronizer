from __future__ import annotations

from datetime import datetime, timezone

from music_synchronizer.config import Settings
from music_synchronizer.obsidian import ObsidianExporter
from music_synchronizer.yandex_client import YandexMusicClient


class SyncService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = YandexMusicClient(token=settings.yandex_music_token)
        self.exporter = ObsidianExporter(settings.obsidian_vault_path)

    def run(self) -> int:
        synced_at = datetime.now(timezone.utc)
        tracks = self.client.fetch_liked_tracks(reference_time=synced_at)
        self.exporter.sync(tracks, synced_at=synced_at)
        return len(tracks)
