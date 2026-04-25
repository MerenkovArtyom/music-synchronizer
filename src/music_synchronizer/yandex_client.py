from __future__ import annotations

from importlib import import_module
from typing import Any

from music_synchronizer.models import TrackInfo


class YandexMusicClient:
    def __init__(self, token: str) -> None:
        self.token = token

    def fetch_liked_tracks(self) -> list[TrackInfo]:
        client_class = self._load_client_class()
        raw_client = client_class(self.token)
        client = raw_client.init() if hasattr(raw_client, "init") else raw_client
        likes = client.users_likes_tracks()

        raw_tracks = getattr(likes, "tracks", likes)
        tracks: list[TrackInfo] = []

        for index, track_short in enumerate(raw_tracks, start=1):
            full_track = track_short.fetch_track() if hasattr(track_short, "fetch_track") else track_short
            tracks.append(self._normalize_track(full_track, position=index))

        return tracks

    def _load_client_class(self) -> Any:
        try:
            module = import_module("yandex_music")
        except ImportError as error:
            raise RuntimeError(
                "Install the 'yandex-music' package to use the sync command."
            ) from error

        return module.Client

    def _normalize_track(self, track: Any, position: int) -> TrackInfo:
        track_id = str(track.id)
        artists = [artist.name for artist in getattr(track, "artists", []) if getattr(artist, "name", None)]
        albums = getattr(track, "albums", [])
        primary_album = albums[0] if albums else None
        album_title = getattr(primary_album, "title", "")
        tags = self._extract_tags(track, primary_album)
        album_id = getattr(primary_album, "id", None)
        duration_ms = int(getattr(track, "duration_ms", 0) or 0)

        if album_id is not None:
            yandex_url = f"https://music.yandex.ru/album/{album_id}/track/{track_id}"
        else:
            yandex_url = f"https://music.yandex.ru/track/{track_id}"

        return TrackInfo(
            track_id=track_id,
            title=str(getattr(track, "title", "")),
            artists=artists,
            album=album_title,
            tags=tags,
            duration_seconds=duration_ms // 1000,
            source_position=position,
            yandex_url=yandex_url,
        )

    def _extract_tags(self, track: Any, primary_album: Any) -> list[str]:
        meta_data = getattr(track, "meta_data", None)
        raw_tags = [
            getattr(meta_data, "genre", None),
            getattr(track, "genre", None),
            getattr(primary_album, "genre", None),
        ]

        tags: list[str] = []
        for raw_tag in raw_tags:
            if not isinstance(raw_tag, str):
                continue

            normalized_tag = raw_tag.strip()
            if normalized_tag and normalized_tag not in tags:
                tags.append(normalized_tag)

        return tags
