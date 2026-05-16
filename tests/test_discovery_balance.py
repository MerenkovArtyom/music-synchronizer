from music_synchronizer.config import Settings
from music_synchronizer.models import DiscoveryTrackInfo
from music_synchronizer.sync import SyncService


def _candidate(track_id: str, title: str, artist: str, source: str) -> DiscoveryTrackInfo:
    return DiscoveryTrackInfo(
        track_id=track_id,
        title=title,
        artists=[artist],
        album="Album",
        system_tags=["indie"],
        year=2024,
        cover_url="",
        duration_seconds=180,
        yandex_url=f"https://music.yandex.ru/track/{track_id}",
        monthly_listens=None,
        discovery_sources=[source],
    )


def test_discovery_recommendations_limit_primary_artist_to_two_entries_per_artist() -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    popular_candidates = [
        _candidate("10", "Eminem Popular 1", "Eminem", "artist-popular"),
        _candidate("11", "Eminem Popular 2", "Eminem", "artist-popular"),
        _candidate("12", "Eminem Popular 3", "Eminem", "artist-popular"),
        _candidate("13", "Other Popular", "Nas", "artist-popular"),
    ]
    similar_candidates = [
        _candidate("20", "Eminem Similar 1", "Eminem", "similar"),
        _candidate("21", "Eminem Similar 2", "Eminem", "similar"),
        _candidate("22", "Other Similar", "Jay-Z", "similar"),
    ]

    recommendations = service._mix_discovery_candidates(popular_candidates, similar_candidates)

    assert sum(1 for track in recommendations if track.artists and track.artists[0] == "Eminem") == 2
