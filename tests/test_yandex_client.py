import sys
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
