import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace

import pytest

from music_synchronizer.models import TrackInfo
from music_synchronizer.yandex_client import YandexMusicClient


class _FakeTrackShort:
    def __init__(self, track: object) -> None:
        self._track = track

    def fetch_track(self) -> object:
        return self._track


def test_fetch_liked_tracks_normalizes_response(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("yandex_music")

    full_track = SimpleNamespace(
        id=321,
        title="My Song",
        artists=[SimpleNamespace(name="First"), SimpleNamespace(name="Second")],
        albums=[
            SimpleNamespace(
                id=77,
                title="Best Album",
                year=2020,
                cover_uri="avatars.yandex.net/get-music-content/12345/cover%%.jpg",
            )
        ],
        meta_data=SimpleNamespace(genre="indie"),
        year=2024,
        duration_ms=245000,
    )

    likes_payload = [
        _FakeTrackShort(full_track),
    ]

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def users_likes_tracks(self) -> list[_FakeTrackShort]:
            return likes_payload

        def music_history(self) -> SimpleNamespace:
            return SimpleNamespace(history_tabs=[])

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    assert client.fetch_liked_tracks() == [
        TrackInfo(
            track_id="321",
            title="My Song",
            artists=["First", "Second"],
            album="Best Album",
            tags=["indie"],
            year=2024,
            cover_url="https://avatars.yandex.net/get-music-content/12345/cover1000x1000.jpg",
            duration_seconds=245,
            source_position=1,
            yandex_url="https://music.yandex.ru/album/77/track/321",
        )
    ]


def test_fetch_liked_tracks_normalizes_missing_or_duplicate_genre_tags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")

    full_track = SimpleNamespace(
        id=654,
        title="Genre Song",
        artists=[SimpleNamespace(name="Artist")],
        albums=[
            SimpleNamespace(
                id=88,
                title="Album",
                genre="electronic",
                year=2019,
                cover_uri="https://avatars.yandex.net/get-music-content/99999/cover1000x1000.jpg",
            )
        ],
        meta_data=SimpleNamespace(genre="electronic"),
        duration_ms=180000,
    )

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def users_likes_tracks(self) -> list[_FakeTrackShort]:
            return [_FakeTrackShort(full_track)]

        def music_history(self) -> SimpleNamespace:
            return SimpleNamespace(history_tabs=[])

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    assert client.fetch_liked_tracks()[0].tags == ["electronic"]


def test_fetch_liked_tracks_falls_back_to_album_year_and_handles_missing_cover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")

    full_track = SimpleNamespace(
        id=777,
        title="Fallback Song",
        artists=[SimpleNamespace(name="Artist")],
        albums=[SimpleNamespace(id=55, title="Album", year=2017)],
        meta_data=SimpleNamespace(genre="ambient"),
        duration_ms=61000,
    )

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def users_likes_tracks(self) -> list[_FakeTrackShort]:
            return [_FakeTrackShort(full_track)]

        def music_history(self) -> SimpleNamespace:
            return SimpleNamespace(history_tabs=[])

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    assert client.fetch_liked_tracks()[0] == TrackInfo(
        track_id="777",
        title="Fallback Song",
        artists=["Artist"],
        album="Album",
        tags=["ambient"],
        year=2017,
        cover_url="",
        duration_seconds=61,
        source_position=1,
        yandex_url="https://music.yandex.ru/album/55/track/777",
    )


def test_fetch_liked_tracks_raises_clear_error_when_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "music_synchronizer.yandex_client.import_module",
        lambda _: (_ for _ in ()).throw(ImportError("missing dependency")),
    )

    client = YandexMusicClient(token="token")

    with pytest.raises(RuntimeError, match="Install the 'yandex-music' package"):
        client.fetch_liked_tracks()


def test_fetch_liked_tracks_populates_monthly_listens_from_recent_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")
    now = datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc)

    liked_track = SimpleNamespace(
        id=321,
        title="History Song",
        artists=[SimpleNamespace(name="Artist")],
        albums=[SimpleNamespace(id=77, title="Best Album", year=2020)],
        meta_data=SimpleNamespace(genre="indie"),
        year=2024,
        duration_ms=245000,
    )

    second_track = SimpleNamespace(
        id=654,
        title="Second Song",
        artists=[SimpleNamespace(name="Other Artist")],
        albums=[SimpleNamespace(id=88, title="Second Album", year=2019)],
        meta_data=SimpleNamespace(genre="electronic"),
        year=2023,
        duration_ms=180000,
    )

    recent_day = SimpleNamespace(
        date="2026-05-07",
        items=[
            SimpleNamespace(
                tracks=[
                    SimpleNamespace(
                        type="track",
                        data=SimpleNamespace(item_id=SimpleNamespace(track_id="321")),
                    ),
                    SimpleNamespace(
                        type="track",
                        data=SimpleNamespace(item_id=SimpleNamespace(track_id="321")),
                    ),
                    SimpleNamespace(
                        type="track",
                        data=SimpleNamespace(item_id=SimpleNamespace(track_id="654")),
                    ),
                ]
            )
        ],
    )
    old_day = SimpleNamespace(
        date="2026-04-01",
        items=[
            SimpleNamespace(
                tracks=[
                    SimpleNamespace(
                        type="track",
                        data=SimpleNamespace(item_id=SimpleNamespace(track_id="321")),
                    )
                ]
            )
        ],
    )
    mixed_day = SimpleNamespace(
        date="2026-05-08",
        items=[
            SimpleNamespace(
                tracks=[
                    SimpleNamespace(
                        type="album",
                        data=SimpleNamespace(item_id=SimpleNamespace(id="album-1")),
                    ),
                    SimpleNamespace(
                        type="track",
                        data=SimpleNamespace(item_id=SimpleNamespace(track_id="321")),
                    ),
                ]
            )
        ],
    )

    history = SimpleNamespace(history_tabs=[recent_day, old_day, mixed_day])

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def users_likes_tracks(self) -> list[_FakeTrackShort]:
            return [_FakeTrackShort(liked_track), _FakeTrackShort(second_track)]

        def music_history(self) -> SimpleNamespace:
            return history

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    tracks = client.fetch_liked_tracks(reference_time=now)

    assert tracks[0].monthly_listens == 3
    assert tracks[1].monthly_listens == 1


def test_fetch_liked_tracks_raises_clear_error_when_history_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")

    full_track = SimpleNamespace(
        id=321,
        title="My Song",
        artists=[SimpleNamespace(name="First")],
        albums=[SimpleNamespace(id=77, title="Best Album", year=2020)],
        meta_data=SimpleNamespace(genre="indie"),
        year=2024,
        duration_ms=245000,
    )

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def users_likes_tracks(self) -> list[_FakeTrackShort]:
            return [_FakeTrackShort(full_track)]

        def music_history(self) -> None:
            raise RuntimeError("history unavailable")

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    with pytest.raises(RuntimeError, match="Unable to compute 30-day listen counts"):
        client.fetch_liked_tracks(reference_time=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc))


def test_fetch_liked_tracks_raises_clear_error_when_history_shape_is_unusable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")

    full_track = SimpleNamespace(
        id=321,
        title="My Song",
        artists=[SimpleNamespace(name="First")],
        albums=[SimpleNamespace(id=77, title="Best Album", year=2020)],
        meta_data=SimpleNamespace(genre="indie"),
        year=2024,
        duration_ms=245000,
    )

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def users_likes_tracks(self) -> list[_FakeTrackShort]:
            return [_FakeTrackShort(full_track)]

        def music_history(self) -> SimpleNamespace:
            return SimpleNamespace(history_tabs=[SimpleNamespace(date="not-a-date", items=[])])

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    with pytest.raises(RuntimeError, match="Unable to compute 30-day listen counts"):
        client.fetch_liked_tracks(reference_time=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc))


def test_fetch_recent_liked_track_ids_returns_latest_unique_liked_tracks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")
    history = SimpleNamespace(
        history_tabs=[
            SimpleNamespace(
                date="2026-05-08",
                items=[
                    SimpleNamespace(
                        tracks=[
                            SimpleNamespace(
                                type="track",
                                data=SimpleNamespace(item_id=SimpleNamespace(track_id="2")),
                            ),
                            SimpleNamespace(
                                type="track",
                                data=SimpleNamespace(item_id=SimpleNamespace(track_id="1")),
                            ),
                        ]
                    )
                ],
            ),
            SimpleNamespace(
                date="2026-05-07",
                items=[
                    SimpleNamespace(
                        tracks=[
                            SimpleNamespace(
                                type="track",
                                data=SimpleNamespace(item_id=SimpleNamespace(track_id="2")),
                            ),
                            SimpleNamespace(
                                type="track",
                                data=SimpleNamespace(item_id=SimpleNamespace(track_id="3")),
                            ),
                        ]
                    )
                ],
            ),
        ]
    )

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def music_history(self) -> SimpleNamespace:
            return history

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    track_ids = client.fetch_recent_liked_track_ids(
        liked_track_ids={"1", "2", "9"},
        reference_time=datetime(2026, 5, 8, 12, 0, tzinfo=timezone.utc),
        limit=2,
    )

    assert track_ids == ["2", "1"]


def test_fetch_popular_tracks_for_artist_seeds_filters_liked_and_broken_tracks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")

    def make_track(track_id: int, title: str) -> SimpleNamespace:
        return SimpleNamespace(
            id=track_id,
            title=title,
            artists=[SimpleNamespace(name="Artist A")],
            albums=[SimpleNamespace(id=77, title="Album", year=2020)],
            meta_data=SimpleNamespace(genre="indie"),
            year=2024,
            duration_ms=245000,
        )

    artist_track = make_track(10, "Popular One")
    liked_track = make_track(1, "Already Liked")

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def artists_tracks(self, artist_id: str) -> SimpleNamespace:
            assert artist_id == "artist-1"
            return SimpleNamespace(tracks=[liked_track, artist_track, SimpleNamespace(id=None)])

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")
    client._seed_artists_by_track_id = {"1": [SimpleNamespace(id="artist-1", name="Artist A")]}  # type: ignore[attr-defined]

    tracks = client.fetch_popular_tracks_for_artist_seeds(["1"], exclude_track_ids={"1"})

    assert [track.track_id for track in tracks] == ["10"]
    assert tracks[0].discovery_sources == ["artist-popular"]


def test_fetch_similar_tracks_merges_duplicate_sources_and_skips_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("yandex_music")

    similar_track = SimpleNamespace(
        id=20,
        title="Similar One",
        artists=[SimpleNamespace(name="Artist B")],
        albums=[SimpleNamespace(id=88, title="Album", year=2021)],
        meta_data=SimpleNamespace(genre="ambient"),
        year=2025,
        duration_ms=180000,
    )

    class FakeClient:
        def __init__(self, token: str) -> None:
            self.token = token

        def init(self) -> "FakeClient":
            return self

        def tracks_similar(self, track_id: str) -> SimpleNamespace:
            assert track_id == "1"
            return SimpleNamespace(similar_tracks=[similar_track, SimpleNamespace(id=None), similar_track])

    fake_module.Client = FakeClient
    monkeypatch.setitem(sys.modules, "yandex_music", fake_module)

    client = YandexMusicClient(token="token")

    tracks = client.fetch_similar_tracks(["1"], exclude_track_ids={"1"})

    assert [track.track_id for track in tracks] == ["20"]
    assert tracks[0].discovery_sources == ["similar"]
