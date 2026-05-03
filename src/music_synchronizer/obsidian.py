from __future__ import annotations

from ast import literal_eval
from datetime import datetime
from pathlib import Path
import re

from music_synchronizer.models import ExporterSyncSummary, SavedTrackInfo, TrackInfo


class ObsidianExporter:
    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path
        self.tracks_dir = vault_path / "tracks"
        self.removed_dir = self.tracks_dir / "_removed"

    def sync(self, tracks: list[TrackInfo], synced_at: datetime) -> ExporterSyncSummary:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.tracks_dir.mkdir(parents=True, exist_ok=True)
        self.removed_dir.mkdir(parents=True, exist_ok=True)
        self._remove_legacy_playlist()

        active_ids = {track.track_id for track in tracks}
        managed_files = self._scan_managed_files()
        restored_count = sum(
            1
            for track_id, path in managed_files.items()
            if track_id in active_ids and path.parent == self.removed_dir
        )
        archived_count = sum(
            1
            for track_id, path in managed_files.items()
            if track_id not in active_ids and path.parent == self.tracks_dir
        )
        existing_user_tags = {
            track_id: self._read_user_tags(path)
            for track_id, path in managed_files.items()
        }
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
            if track_id in active_ids:
                current_path.replace(staging_dir / f"{track_id}.md")
            elif current_path.parent == self.tracks_dir:
                current_path.replace(self.removed_dir / current_path.name)

        for track in tracks:
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

        return ExporterSyncSummary(
            written=len(tracks),
            archived=archived_count,
            restored=restored_count,
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

    def _render_track(self, track: TrackInfo, synced_at: datetime, user_tags: list[str]) -> str:
        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        system_tags = self._normalize_tags(track.tags)
        user_tags = self._normalize_tags(user_tags)
        year_value = str(track.year) if track.year is not None else "null"
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

        if title is None:
            return None

        tags = self._normalize_tags(user_tags or [], system_tags or [])
        if user_tags is None and system_tags is None:
            tags = self._normalize_tags(self._read_frontmatter_list(content, "tags"))

        return SavedTrackInfo(
            title=title,
            artists=artists,
            tags=tags,
        )

    def _read_frontmatter_value(self, content: str, field_name: str) -> str | None:
        match = re.search(rf'^{field_name}:\s*"((?:[^"\\]|\\.)*)"$', content, re.MULTILINE)
        if match is None:
            return None

        return match.group(1).replace('\\"', '"').replace("\\\\", "\\")

    def _read_frontmatter_list(self, content: str, field_name: str) -> list[str]:
        parsed_value = self._read_optional_frontmatter_list(content, field_name)
        return parsed_value or []

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
