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
        albums=[SimpleNamespace(id=77, title="Best Album")],
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
            duration_seconds=245,
            source_position=1,
            yandex_url="https://music.yandex.ru/album/77/track/321",
        )
    ]


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
