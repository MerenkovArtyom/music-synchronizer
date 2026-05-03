from pathlib import Path

from music_synchronizer.config import Settings
from music_synchronizer.models import ExporterSyncSummary, TrackInfo
from music_synchronizer.sync import SyncService


class _FakeClient:
    def __init__(self, tracks: list[TrackInfo]) -> None:
        self._tracks = tracks

    def fetch_liked_tracks(self) -> list[TrackInfo]:
        return self._tracks


class _FakeExporter:
    def __init__(self, summary: ExporterSyncSummary) -> None:
        self.summary = summary

    def sync(self, tracks: list[TrackInfo], synced_at: object) -> ExporterSyncSummary:
        return self.summary


def test_sync_service_returns_typed_summary(tmp_path: Path) -> None:
    tracks = [
        TrackInfo(
            track_id="101",
            title="Song",
            artists=["Artist"],
            album="Album",
            tags=["indie"],
            year=2024,
            cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
            duration_seconds=180,
            source_position=1,
            yandex_url="https://music.yandex.ru/track/101",
        )
    ]
    settings = Settings.model_validate(
        {
            "YANDEX_MUSIC_TOKEN": "test-token",
            "OBSIDIAN_VAULT_PATH": str(tmp_path),
        }
    )
    service = SyncService(settings)
    service.client = _FakeClient(tracks)
    service.exporter = _FakeExporter(
        ExporterSyncSummary(
            written=1,
            archived=2,
            restored=3,
        )
    )

    summary = service.run()

    assert summary.fetched == 1
    assert summary.written == 1
    assert summary.archived == 2
    assert summary.restored == 3
