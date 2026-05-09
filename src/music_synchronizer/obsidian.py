from __future__ import annotations

from ast import literal_eval
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import re

from music_synchronizer.models import SavedTrackInfo, SyncSummary, TrackInfo


@dataclass(frozen=True, slots=True)
class TrackSnapshot:
    title: str
    artists: list[str]
    album: str
    system_tags: list[str]
    year: int | None
    monthly_listens: int | None
    cover_url: str
    duration_seconds: int
    source_position: int
    yandex_url: str


class ObsidianExporter:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path
        self.tracks_dir = vault_path / "tracks"
        self.removed_dir = self.tracks_dir / "_removed"
        self.snapshot_path = vault_path / ".music_sync_snapshot.json"

    def sync(self, tracks: list[TrackInfo], synced_at: datetime) -> SyncSummary:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.tracks_dir.mkdir(parents=True, exist_ok=True)
        self.removed_dir.mkdir(parents=True, exist_ok=True)
        self._remove_legacy_playlist()

        previous_snapshot = self._load_snapshot()
        current_snapshots = {
            track.track_id: self._snapshot_track(track)
            for track in tracks
        }
        active_ids = set(current_snapshots)
        previous_active_ids = set(previous_snapshot)
        managed_files = self._scan_managed_files()
        existing_user_tags = {
            track_id: self._read_user_tags(path)
            for track_id, path in managed_files.items()
        }
        unchanged_ids = {
            track.track_id
            for track in tracks
            if self._is_unchanged_track(
                track_id=track.track_id,
                snapshot=current_snapshots[track.track_id],
                previous_snapshot=previous_snapshot,
                managed_files=managed_files,
            )
        }
        added_ids = {
            track_id
            for track_id in active_ids
            if track_id not in previous_active_ids
        }
        removed_ids = previous_active_ids - active_ids
        write_ids = active_ids - unchanged_ids
        unmanaged_active_names = {
            path.name for path in self.tracks_dir.glob("*.md") if path not in managed_files.values()
        }
        desired_paths = self._build_desired_paths(tracks, unmanaged_active_names)
        staging_dir = self.vault_path / ".sync_staging"

        if staging_dir.exists():
            for staged_file in staging_dir.glob("*.md"):
                staged_file.unlink()
        else:
            staging_dir.mkdir(parents=True, exist_ok=True)

        for track_id, current_path in managed_files.items():
            if track_id in write_ids:
                current_path.replace(staging_dir / f"{track_id}.md")
            elif track_id in removed_ids and current_path.parent == self.tracks_dir:
                current_path.replace(self.removed_dir / current_path.name)

        for track in tracks:
            if track.track_id in unchanged_ids:
                continue

            active_path = desired_paths[track.track_id]
            active_path.write_text(
                self._render_track(
                    track,
                    synced_at,
                    user_tags=existing_user_tags.get(track.track_id, []),
                ),
                encoding="utf-8",
            )

        for staged_file in staging_dir.glob("*.md"):
            staged_file.unlink()
        staging_dir.rmdir()

        self._save_snapshot(current_snapshots)
        return SyncSummary(
            added=len(added_ids),
            unchanged=len(unchanged_ids),
            removed=len(removed_ids),
        )

    def list_tracks_by_tag(self, tag: str) -> list[SavedTrackInfo]:
        normalized_tag = tag.strip().casefold()
        if not normalized_tag:
            return []

        matching_tracks: list[SavedTrackInfo] = []
        if not self.tracks_dir.exists():
            return matching_tracks

        for path in sorted(self.tracks_dir.glob("*.md")):
            track = self._read_saved_track(path)
            if track is None:
                continue

            if any(saved_tag.casefold() == normalized_tag for saved_tag in track.tags):
                matching_tracks.append(track)

        return matching_tracks

    def list_tracks_by_artist(self, artist: str) -> list[SavedTrackInfo]:
        normalized_artist = artist.strip().casefold()
        if not normalized_artist:
            return []

        matching_tracks: list[SavedTrackInfo] = []
        if not self.tracks_dir.exists():
            return matching_tracks

        for path in sorted(self.tracks_dir.glob("*.md")):
            track = self._read_saved_track(path)
            if track is None:
                continue

            if any(saved_artist.casefold() == normalized_artist for saved_artist in track.artists):
                matching_tracks.append(track)

        return matching_tracks

    def top_listen_tracks(self) -> list[SavedTrackInfo]:
        saved_tracks: list[SavedTrackInfo] = []
        if not self.tracks_dir.exists():
            return saved_tracks

        for path in sorted(self.tracks_dir.glob("*.md")):
            track = self._read_saved_track(path)
            if track is not None:
                saved_tracks.append(track)

        return saved_tracks

    def _render_track(self, track: TrackInfo, synced_at: datetime, user_tags: list[str]) -> str:
        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        system_tags = self._normalize_tags(track.tags)
        user_tags = self._normalize_tags(user_tags)
        year_value = str(track.year) if track.year is not None else "null"
        monthly_listens_value = (
            str(track.monthly_listens) if track.monthly_listens is not None else "null"
        )
        monthly_listens_text = str(track.monthly_listens) if track.monthly_listens is not None else "-"
        duration_text = self._format_duration(track.duration_seconds)
        lines = [
            "---",
            f'track_id: "{self._escape_yaml(track.track_id)}"',
            f'title: "{self._escape_yaml(track.title)}"',
            f"artists: [{', '.join(self._quote_yaml(artist) for artist in track.artists)}]",
            f'album: "{self._escape_yaml(track.album)}"',
            f"system_tags: [{', '.join(self._quote_yaml(tag) for tag in system_tags)}]",
            f"user_tags: [{', '.join(self._quote_yaml(tag) for tag in user_tags)}]",
            f"year: {year_value}",
            f"monthly_listens: {monthly_listens_value}",
            f'cover_url: "{self._escape_yaml(track.cover_url)}"',
            f"duration_seconds: {track.duration_seconds}",
            f"position: {track.source_position}",
            'source: "likes"',
            f'yandex_url: "{self._escape_yaml(track.yandex_url)}"',
            f'synced_at: "{synced_at.isoformat()}"',
            "---",
            "",
            f"# {track.title}",
            "",
            f"Artists: {artists}",
            f"Album: {track.album or '-'}",
            f"Year: {track.year if track.year is not None else '-'}",
            f"Monthly listens (30d): {monthly_listens_text}",
            f"Duration: {duration_text}",
            f"Yandex Music: {track.yandex_url}",
            "",
        ]
        if track.cover_url:
            lines.extend(
                [
                    f"![Album cover]({track.cover_url})",
                    "",
                ]
            )
        return "\n".join(lines)

    def _format_duration(self, duration_seconds: int) -> str:
        minutes, seconds = divmod(max(duration_seconds, 0), 60)
        return f"{minutes}:{seconds:02d}"

    def _quote_yaml(self, value: str) -> str:
        return f'"{self._escape_yaml(value)}"'

    def _escape_yaml(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _remove_legacy_playlist(self) -> None:
        playlist_path = self.vault_path / "playlist.md"
        if playlist_path.exists():
            playlist_path.unlink()

    def _scan_managed_files(self) -> dict[str, Path]:
        managed: dict[str, Path] = {}
        for directory in (self.tracks_dir, self.removed_dir):
            for path in directory.glob("*.md"):
                track_id = self._read_track_id(path)
                if track_id is not None:
                    managed[track_id] = path
        return managed

    def _build_desired_paths(
        self,
        tracks: list[TrackInfo],
        reserved_names: set[str],
    ) -> dict[str, Path]:
        desired_paths: dict[str, Path] = {}
        used_names = set(reserved_names)

        for track in tracks:
            filename = self._unique_filename(track, used_names)
            used_names.add(filename)
            desired_paths[track.track_id] = self.tracks_dir / filename

        return desired_paths

    def _unique_filename(self, track: TrackInfo, used_names: set[str]) -> str:
        candidates = [
            self._format_filename(track.title),
            self._format_filename(f"{track.title} - {self._primary_artist(track)}"),
            self._format_filename(f"{track.title} - {self._primary_artist(track)} [{track.track_id}]"),
        ]

        for candidate in candidates:
            if candidate not in used_names:
                return candidate

        return self._format_filename(track.track_id)

    def _format_filename(self, value: str) -> str:
        sanitized = re.sub(r'[<>:"/\\|?*]+', " ", value)
        sanitized = re.sub(r"\s+", " ", sanitized).strip().rstrip(".")
        if not sanitized:
            sanitized = "untitled"
        return f"{sanitized}.md"

    def _primary_artist(self, track: TrackInfo) -> str:
        return track.artists[0] if track.artists else track.track_id

    def _read_track_id(self, path: Path) -> str | None:
        content = path.read_text(encoding="utf-8")
        match = re.search(r'^track_id:\s*"([^"]+)"$', content, re.MULTILINE)
        if match is None:
            return None
        return match.group(1)

    def _read_user_tags(self, path: Path) -> list[str]:
        content = path.read_text(encoding="utf-8")
        user_tags = self._read_optional_frontmatter_list(content, "user_tags")
        if user_tags is not None:
            return self._normalize_tags(user_tags)

        legacy_tags = self._read_frontmatter_list(content, "tags")
        return self._normalize_tags(legacy_tags)

    def _read_saved_track(self, path: Path) -> SavedTrackInfo | None:
        content = path.read_text(encoding="utf-8")
        title = self._read_frontmatter_value(content, "title")
        artists = self._read_frontmatter_list(content, "artists")
        user_tags = self._read_optional_frontmatter_list(content, "user_tags")
        system_tags = self._read_optional_frontmatter_list(content, "system_tags")
        monthly_listens = self._read_optional_frontmatter_int(content, "monthly_listens")
        source_position = self._read_optional_frontmatter_int(content, "position")

        if title is None:
            return None

        tags = self._normalize_tags(user_tags or [], system_tags or [])
        if user_tags is None and system_tags is None:
            tags = self._normalize_tags(self._read_frontmatter_list(content, "tags"))

        return SavedTrackInfo(
            title=title,
            artists=artists,
            tags=tags,
            monthly_listens=monthly_listens,
            source_position=source_position,
        )

    def _read_frontmatter_value(self, content: str, field_name: str) -> str | None:
        match = re.search(rf'^{field_name}:\s*"((?:[^"\\]|\\.)*)"$', content, re.MULTILINE)
        if match is None:
            return None

        return match.group(1).replace('\\"', '"').replace("\\\\", "\\")

    def _read_frontmatter_list(self, content: str, field_name: str) -> list[str]:
        parsed_value = self._read_optional_frontmatter_list(content, field_name)
        return parsed_value or []

    def _read_optional_frontmatter_int(self, content: str, field_name: str) -> int | None:
        match = re.search(rf"^{field_name}:\s*(.+?)$", content, re.MULTILINE)
        if match is None:
            return None

        raw_value = match.group(1).strip()
        if raw_value == "null":
            return None

        try:
            return int(raw_value)
        except ValueError:
            return None

    def _read_optional_frontmatter_list(self, content: str, field_name: str) -> list[str] | None:
        match = re.search(rf"^{field_name}:\s*(\[[^\n]*\])$", content, re.MULTILINE)
        if match is not None:
            try:
                parsed_value = literal_eval(match.group(1))
            except (SyntaxError, ValueError):
                return None

            if not isinstance(parsed_value, list):
                return None

            return [item for item in parsed_value if isinstance(item, str)]

        frontmatter = self._read_frontmatter(content)
        if frontmatter is None:
            return None

        lines = frontmatter.splitlines()
        for index, line in enumerate(lines):
            if line.strip() != f"{field_name}:":
                continue

            parsed_items: list[str] = []
            for nested_line in lines[index + 1 :]:
                if not nested_line.startswith(" "):
                    break

                nested_match = re.match(r'^\s*-\s*(.+?)\s*$', nested_line)
                if nested_match is None:
                    continue

                item_text = nested_match.group(1)
                try:
                    parsed_item = literal_eval(item_text)
                except (SyntaxError, ValueError):
                    parsed_item = item_text.strip().strip('"').strip("'")

                if isinstance(parsed_item, str):
                    parsed_items.append(parsed_item)

            return parsed_items

        return None

    def _read_frontmatter(self, content: str) -> str | None:
        match = re.match(r"^---\n(.*?)\n---(?:\n|$)", content, re.DOTALL)
        if match is None:
            return None

        return match.group(1)

    def _normalize_tags(self, *tag_groups: list[str]) -> list[str]:
        normalized: list[str] = []

        for tag_group in tag_groups:
            for tag in tag_group:
                if not isinstance(tag, str):
                    continue

                cleaned_tag = tag.strip()
                if cleaned_tag and cleaned_tag not in normalized:
                    normalized.append(cleaned_tag)

        return normalized

    def _snapshot_track(self, track: TrackInfo) -> TrackSnapshot:
        return TrackSnapshot(
            title=track.title,
            artists=list(track.artists),
            album=track.album,
            system_tags=self._normalize_tags(track.tags),
            year=track.year,
            monthly_listens=track.monthly_listens,
            cover_url=track.cover_url,
            duration_seconds=track.duration_seconds,
            source_position=track.source_position,
            yandex_url=track.yandex_url,
        )

    def _is_unchanged_track(
        self,
        track_id: str,
        snapshot: TrackSnapshot,
        previous_snapshot: dict[str, TrackSnapshot],
        managed_files: dict[str, Path],
    ) -> bool:
        previous = previous_snapshot.get(track_id)
        current_path = managed_files.get(track_id)
        if previous is None or current_path is None:
            return False
        if current_path.parent != self.tracks_dir or not current_path.exists():
            return False
        if self._requires_note_refresh(current_path):
            return False
        return previous == snapshot

    def _load_snapshot(self) -> dict[str, TrackSnapshot]:
        if not self.snapshot_path.exists():
            return {}

        try:
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

        tracks_payload = payload.get("tracks")
        if not isinstance(tracks_payload, dict):
            return {}

        snapshots: dict[str, TrackSnapshot] = {}
        for track_id, track_data in tracks_payload.items():
            if not isinstance(track_id, str) or not isinstance(track_data, dict):
                continue

            artists = track_data.get("artists")
            system_tags = track_data.get("system_tags")
            year = track_data.get("year")
            monthly_listens = track_data.get("monthly_listens")
            try:
                snapshots[track_id] = TrackSnapshot(
                    title=str(track_data["title"]),
                    artists=[artist for artist in artists if isinstance(artist, str)]
                    if isinstance(artists, list)
                    else [],
                    album=str(track_data["album"]),
                    system_tags=[tag for tag in system_tags if isinstance(tag, str)]
                    if isinstance(system_tags, list)
                    else [],
                    year=year if isinstance(year, int) or year is None else None,
                    monthly_listens=monthly_listens
                    if isinstance(monthly_listens, int) or monthly_listens is None
                    else None,
                    cover_url=str(track_data["cover_url"]),
                    duration_seconds=int(track_data["duration_seconds"]),
                    source_position=int(track_data["source_position"]),
                    yandex_url=str(track_data["yandex_url"]),
                )
            except (KeyError, TypeError, ValueError):
                continue

        return snapshots

    def _save_snapshot(self, snapshots: dict[str, TrackSnapshot]) -> None:
        payload = {
            "tracks": {
                track_id: asdict(snapshot)
                for track_id, snapshot in sorted(snapshots.items())
            }
        }
        temp_path = self.snapshot_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp_path.replace(self.snapshot_path)

    def _requires_note_refresh(self, path: Path) -> bool:
        content = path.read_text(encoding="utf-8")
        if re.search(r"^tags:\s*", content, re.MULTILINE):
            return True
        return re.search(r"^user_tags:\s*$", content, re.MULTILINE) is not None
