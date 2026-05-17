from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from importlib import import_module
from typing import Any

from music_synchronizer.models import DiscoveryTrackInfo, TrackInfo


@dataclass(frozen=True, slots=True)
class _PlaylistTrackEntry:
    track_id: str
    album_id: str | None
    index: int


@dataclass(frozen=True, slots=True)
class _PlaylistReference:
    playlist: Any
    kind: Any
    owner_uid: Any


class YandexMusicClient:
    def __init__(self, token: str) -> None:
        self.token = token
        self._seed_artists_by_track_id: dict[str, list[Any]] = {}

    def fetch_liked_tracks(self, reference_time: datetime | None = None) -> list[TrackInfo]:
        client = self._create_client()
        if reference_time is None:
            reference_time = datetime.now().astimezone()

        likes = client.users_likes_tracks()
        monthly_listens = self._fetch_monthly_listens(client, reference_time)

        raw_tracks = getattr(likes, "tracks", likes)
        tracks: list[TrackInfo] = []

        for index, track_short in enumerate(raw_tracks, start=1):
            full_track = track_short.fetch_track() if hasattr(track_short, "fetch_track") else track_short
            track_id = str(getattr(full_track, "id"))
            self._seed_artists_by_track_id[track_id] = list(getattr(full_track, "artists", []) or [])
            tracks.append(
                self._normalize_track(
                    full_track,
                    position=index,
                    monthly_listens=monthly_listens.get(track_id),
                )
            )

        return tracks

    def fetch_recent_liked_track_ids(
        self,
        *,
        liked_track_ids: set[str],
        reference_time: datetime | None = None,
        limit: int,
    ) -> list[str]:
        if limit <= 0:
            return []

        client = self._create_client()
        if reference_time is None:
            reference_time = datetime.now().astimezone()

        history_tabs = self._history_tabs(client)
        seen: set[str] = set()
        recent_track_ids: list[str] = []
        for tab in self._sorted_history_tabs(history_tabs):
            tab_date = self._parse_history_date(getattr(tab, "date", None))
            if tab_date is None or tab_date > reference_time.date():
                continue

            for track_id in self._history_track_ids(getattr(tab, "items", []) or []):
                if track_id not in liked_track_ids or track_id in seen:
                    continue
                recent_track_ids.append(track_id)
                seen.add(track_id)
                if len(recent_track_ids) >= limit:
                    return recent_track_ids

        return recent_track_ids

    def fetch_popular_tracks_for_artist_seeds(
        self,
        seed_track_ids: list[str],
        exclude_track_ids: set[str],
    ) -> list[DiscoveryTrackInfo]:
        client = self._create_client()
        candidates: list[DiscoveryTrackInfo] = []
        seen: set[str] = set()

        for track_id in seed_track_ids:
            for artist in self._seed_artists_by_track_id.get(track_id, []):
                artist_id = getattr(artist, "id", None)
                if artist_id is None:
                    continue

                for track in self._artist_tracks(client, str(artist_id)):
                    normalized = self._normalize_discovery_track(
                        track,
                        source="artist-popular",
                        exclude_track_ids=exclude_track_ids,
                    )
                    if normalized is None or normalized.track_id in seen:
                        continue
                    candidates.append(normalized)
                    seen.add(normalized.track_id)

        return candidates

    def fetch_similar_tracks(
        self,
        seed_track_ids: list[str],
        exclude_track_ids: set[str],
    ) -> list[DiscoveryTrackInfo]:
        client = self._create_client()
        candidates: list[DiscoveryTrackInfo] = []
        seen: set[str] = set()

        for track_id in seed_track_ids:
            if not hasattr(client, "tracks_similar"):
                continue

            try:
                response = client.tracks_similar(track_id)
            except Exception:
                continue

            for track in self._extract_track_candidates(response):
                normalized = self._normalize_discovery_track(
                    track,
                    source="similar",
                    exclude_track_ids=exclude_track_ids,
                )
                if normalized is None or normalized.track_id in seen:
                    continue
                candidates.append(normalized)
                seen.add(normalized.track_id)

        return candidates

    def sync_discovery_playlist(
        self,
        playlist_name: str,
        tracks: list[DiscoveryTrackInfo],
    ) -> None:
        desired_pairs = self._playlist_track_pairs(tracks)
        if not desired_pairs:
            return

        playlist = self._get_or_create_playlist(playlist_name)
        existing_track_ids = {entry.track_id for entry in self._playlist_entries(playlist)}
        api_client = None

        for track_id, album_id in desired_pairs:
            if track_id in existing_track_ids:
                continue

            resolved_album_id = album_id
            if resolved_album_id is None:
                if api_client is None:
                    api_client = self._create_client()
                resolved_album_id = self._resolve_album_id_for_track(api_client, track_id)

            if resolved_album_id is None:
                continue

            updated_playlist = playlist.insert_track(
                int(track_id),
                int(resolved_album_id),
                at=playlist.track_count or 0,
            )
            if updated_playlist is not None:
                playlist = updated_playlist
            existing_track_ids.add(track_id)

    def remove_tracks_from_playlist(self, playlist_name: str, track_ids: set[str]) -> None:
        if not track_ids:
            return

        playlist = self._find_playlist(playlist_name)
        if playlist is None:
            return

        positions = [
            entry.index
            for entry in self._playlist_entries(playlist)
            if entry.track_id in track_ids
        ]
        for position in sorted(positions, reverse=True):
            updated_playlist = playlist.delete_tracks(position, position)
            if updated_playlist is not None:
                playlist = updated_playlist

    def clear_playlist(self, playlist_name: str) -> None:
        client = self._create_client()
        reference = self._find_playlist_reference(client, playlist_name)
        if reference is None:
            return

        if reference.kind is not None and reference.owner_uid is not None and hasattr(client, "users_playlists_delete"):
            client.users_playlists_delete(reference.kind, user_id=reference.owner_uid)
            return

        playlist = reference.playlist
        if reference.kind is not None and reference.owner_uid is not None and hasattr(client, "users_playlists"):
            playlist = client.users_playlists(reference.kind, reference.owner_uid)

        entries = self._playlist_entries(playlist)
        for position in sorted((entry.index for entry in entries), reverse=True):
            updated_playlist = playlist.delete_tracks(position, position)
            if updated_playlist is not None:
                playlist = updated_playlist

    def _create_client(self) -> Any:
        client_class = self._load_client_class()
        raw_client = client_class(self.token)
        return raw_client.init() if hasattr(raw_client, "init") else raw_client

    def _load_client_class(self) -> Any:
        try:
            module = import_module("yandex_music")
        except ImportError as error:
            raise RuntimeError(
                "Install the 'yandex-music' package to use the sync command."
            ) from error

        return module.Client

    def _normalize_track(self, track: Any, position: int, monthly_listens: int | None = None) -> TrackInfo:
        track_id = str(track.id)
        artists = [artist.name for artist in getattr(track, "artists", []) if getattr(artist, "name", None)]
        albums = getattr(track, "albums", [])
        primary_album = albums[0] if albums else None
        album_title = getattr(primary_album, "title", "")
        tags = self._extract_tags(track, primary_album)
        album_id = getattr(primary_album, "id", None)
        duration_ms = int(getattr(track, "duration_ms", 0) or 0)
        year = self._extract_year(track, primary_album)
        cover_url = self._extract_cover_url(primary_album)

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
            year=year,
            cover_url=cover_url,
            duration_seconds=duration_ms // 1000,
            source_position=position,
            yandex_url=yandex_url,
            monthly_listens=monthly_listens,
        )

    def _fetch_monthly_listens(self, client: Any, reference_time: datetime) -> dict[str, int]:
        history_tabs = self._history_tabs(client)

        window_start = reference_time.date() - timedelta(days=29)
        window_end = reference_time.date()
        monthly_listens: dict[str, int] = {}

        for tab in history_tabs:
            tab_date = self._parse_history_date(getattr(tab, "date", None))
            if tab_date is None:
                raise RuntimeError(
                    "Unable to compute 30-day listen counts: Yandex Music history contains an invalid date."
                )
            if tab_date < window_start or tab_date > window_end:
                continue

            for track_id in self._history_track_ids(getattr(tab, "items", []) or []):
                monthly_listens[track_id] = monthly_listens.get(track_id, 0) + 1

        return monthly_listens

    def _history_tabs(self, client: Any) -> list[Any]:
        if not hasattr(client, "music_history"):
            raise RuntimeError(
                "Unable to compute 30-day listen counts: Yandex Music client does not expose listening history."
            )

        try:
            history = client.music_history()
        except Exception as error:
            raise RuntimeError(
                "Unable to compute 30-day listen counts from Yandex Music listening history."
            ) from error

        history_tabs = getattr(history, "history_tabs", None)
        if history_tabs is None:
            raise RuntimeError(
                "Unable to compute 30-day listen counts: Yandex Music listening history is unavailable."
            )
        if not isinstance(history_tabs, list):
            return list(history_tabs)
        return history_tabs

    def _sorted_history_tabs(self, history_tabs: list[Any]) -> list[Any]:
        sortable_tabs: list[tuple[datetime.date, Any]] = []
        for tab in history_tabs:
            tab_date = self._parse_history_date(getattr(tab, "date", None))
            if tab_date is None:
                continue
            sortable_tabs.append((tab_date, tab))
        sortable_tabs.sort(key=lambda item: item[0], reverse=True)
        return [tab for _, tab in sortable_tabs]

    def _parse_history_date(self, raw_date: Any) -> datetime.date | None:
        if not isinstance(raw_date, str):
            return None
        try:
            return datetime.fromisoformat(raw_date).date()
        except ValueError:
            return None

    def _history_track_ids(self, groups: list[Any]) -> list[str]:
        track_ids: list[str] = []
        for group in groups:
            for track_item in getattr(group, "tracks", []) or []:
                if getattr(track_item, "type", None) != "track":
                    continue

                data = getattr(track_item, "data", None)
                item_id = getattr(data, "item_id", None)
                track_id = getattr(item_id, "track_id", None)
                if not isinstance(track_id, str) or not track_id.strip():
                    continue
                track_ids.append(track_id.strip())
        return track_ids

    def _artist_tracks(self, client: Any, artist_id: str) -> list[Any]:
        if hasattr(client, "artists_tracks"):
            try:
                response = client.artists_tracks(artist_id)
            except Exception:
                return []
            return self._extract_track_candidates(response)
        return []

    def _find_playlist(self, playlist_name: str) -> Any | None:
        client = self._create_client()
        reference = self._find_playlist_reference(client, playlist_name)
        if reference is None:
            return None
        if reference.kind is None or reference.owner_uid is None or not hasattr(client, "users_playlists"):
            return reference.playlist
        return client.users_playlists(reference.kind, reference.owner_uid)

    def _find_playlist_reference(self, client: Any, playlist_name: str) -> _PlaylistReference | None:
        for playlist in client.users_playlists_list():
            if getattr(playlist, "title", None) != playlist_name:
                continue

            kind = getattr(playlist, "kind", None)
            owner = getattr(playlist, "owner", None)
            owner_uid = getattr(owner, "uid", None)
            return _PlaylistReference(playlist=playlist, kind=kind, owner_uid=owner_uid)
        return None

    def _get_or_create_playlist(self, playlist_name: str) -> Any:
        playlist = self._find_playlist(playlist_name)
        if playlist is not None:
            return playlist

        client = self._create_client()
        created = client.users_playlists_create(playlist_name, visibility="private")
        if created is None:
            raise RuntimeError(f"Unable to create Yandex Music playlist: {playlist_name}")
        return created

    def _playlist_entries(self, playlist: Any) -> list[_PlaylistTrackEntry]:
        entries: list[_PlaylistTrackEntry] = []
        for index, track in enumerate(playlist.fetch_tracks()):
            track_id = getattr(track, "id", None)
            if track_id is None:
                continue
            normalized_track_id = str(track_id).strip()
            if not normalized_track_id:
                continue
            album_id = getattr(track, "album_id", None)
            normalized_album_id = None if album_id is None else str(album_id).strip() or None
            entries.append(
                _PlaylistTrackEntry(
                    track_id=normalized_track_id,
                    album_id=normalized_album_id,
                    index=index,
                )
            )
        return entries

    def _playlist_track_pairs(self, tracks: list[DiscoveryTrackInfo]) -> list[tuple[str, str | None]]:
        desired_pairs: list[tuple[str, str | None]] = []
        seen: set[str] = set()
        for track in tracks:
            if track.track_id in seen:
                continue
            desired_pairs.append((track.track_id, track.album_id))
            seen.add(track.track_id)
        return desired_pairs

    def _resolve_album_id_for_track(self, client: Any, track_id: str) -> str | None:
        if not hasattr(client, "tracks"):
            return None

        try:
            response = client.tracks([track_id])
        except Exception:
            return None

        tracks = response if isinstance(response, list) else [response]
        for track in tracks:
            if track is None:
                continue
            normalized = str(getattr(track, "id", "")).strip()
            if normalized and normalized != track_id:
                continue

            albums = getattr(track, "albums", []) or []
            for album in albums:
                album_id = getattr(album, "id", None)
                if album_id is None:
                    continue
                normalized_album_id = str(album_id).strip()
                if normalized_album_id:
                    return normalized_album_id

        return None

    def _extract_track_candidates(self, response: Any) -> list[Any]:
        candidates = [
            getattr(response, "tracks", None),
            getattr(response, "similar_tracks", None),
            getattr(response, "items", None),
        ]
        for candidate in candidates:
            if candidate is None:
                continue
            if isinstance(candidate, list):
                return candidate
            try:
                return list(candidate)
            except TypeError:
                continue
        if isinstance(response, list):
            return response
        return []

    def _normalize_discovery_track(
        self,
        track: Any,
        *,
        source: str,
        exclude_track_ids: set[str],
    ) -> DiscoveryTrackInfo | None:
        track_id = getattr(track, "id", None)
        if track_id is None:
            return None

        normalized_track_id = str(track_id).strip()
        if not normalized_track_id or normalized_track_id in exclude_track_ids:
            return None

        artists = [artist.name for artist in getattr(track, "artists", []) if getattr(artist, "name", None)]
        albums = getattr(track, "albums", [])
        primary_album = albums[0] if albums else None
        duration_ms = int(getattr(track, "duration_ms", 0) or 0)
        album_id = getattr(primary_album, "id", None)
        if album_id is not None:
            yandex_url = f"https://music.yandex.ru/album/{album_id}/track/{normalized_track_id}"
        else:
            yandex_url = f"https://music.yandex.ru/track/{normalized_track_id}"

        return DiscoveryTrackInfo(
            track_id=normalized_track_id,
            title=str(getattr(track, "title", "")),
            artists=artists,
            album=str(getattr(primary_album, "title", "") or ""),
            album_id=None if album_id is None else str(album_id),
            system_tags=self._extract_tags(track, primary_album),
            year=self._extract_year(track, primary_album),
            cover_url=self._extract_cover_url(primary_album),
            duration_seconds=duration_ms // 1000,
            yandex_url=yandex_url,
            monthly_listens=None,
            discovery_sources=[source],
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

    def _extract_year(self, track: Any, primary_album: Any) -> int | None:
        candidates = [
            getattr(track, "year", None),
            getattr(track, "release_year", None),
            getattr(primary_album, "year", None),
            getattr(primary_album, "release_year", None),
        ]

        for raw_year in candidates:
            normalized_year = self._normalize_year(raw_year)
            if normalized_year is not None:
                return normalized_year

        return None

    def _normalize_year(self, raw_year: Any) -> int | None:
        if raw_year is None:
            return None

        if isinstance(raw_year, int):
            return raw_year

        if isinstance(raw_year, str):
            stripped_year = raw_year.strip()
            if stripped_year.isdigit():
                return int(stripped_year)

        return None

    def _extract_cover_url(self, primary_album: Any) -> str:
        raw_cover = getattr(primary_album, "cover_uri", None) or getattr(primary_album, "cover_url", None)
        if not isinstance(raw_cover, str):
            return ""

        cover_url = raw_cover.strip()
        if not cover_url:
            return ""

        if cover_url.startswith("//"):
            return f"https:{cover_url}"

        if cover_url.startswith("http://") or cover_url.startswith("https://"):
            return cover_url

        normalized_cover = cover_url.replace("%%", "1000x1000")
        return f"https://{normalized_cover.lstrip('/')}"
