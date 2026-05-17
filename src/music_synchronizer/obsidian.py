from __future__ import annotations

from ast import literal_eval
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import re
from statistics import mean, median

from music_synchronizer.models import (
    DashboardData,
    DashboardStatEntry,
    DiscoverySummary,
    DiscoveryTrackInfo,
    RelistenRecommendationEntry,
    SavedTrackInfo,
    SyncSummary,
    TrackDashboardEntry,
    TrackInfo,
)


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
        self.recommendations_dir = vault_path / "recommendations"
        self.tracks_dir = vault_path / "tracks"
        self.removed_dir = self.tracks_dir / "_removed"
        self.snapshot_path = vault_path / ".music_sync_snapshot.json"
        self.dashboard_path = vault_path / "dashboard.md"

    def sync(self, tracks: list[TrackInfo], synced_at: datetime) -> SyncSummary:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.recommendations_dir.mkdir(parents=True, exist_ok=True)
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
        self.refresh_dashboard()
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
        return self._read_saved_tracks(self.tracks_dir)

    def recommendation_tracks(self, *, include_archived: bool = False) -> list[SavedTrackInfo]:
        tracks = self._read_saved_tracks(self.tracks_dir)
        if include_archived:
            tracks.extend(self._read_saved_tracks(self.removed_dir))
        return tracks

    def dashboard_data(self) -> DashboardData:
        active_tracks = self._read_saved_tracks(self.tracks_dir)
        removed_tracks = self._read_saved_tracks(self.removed_dir)
        discovery_tracks = self.read_discovery_tracks()
        monthly_listens_values = [
            track.monthly_listens for track in active_tracks if track.monthly_listens is not None
        ]
        total_duration_seconds = sum(track.duration_seconds for track in active_tracks)
        monthly_coverage = (
            round((len(monthly_listens_values) / len(active_tracks)) * 100, 2) if active_tracks else 0.0
        )
        top_tags = self._build_top_tag_entries(active_tracks)
        top_artists = self._build_top_artist_entries(active_tracks)
        most_listened_artist = self._most_listened_artist(active_tracks)
        most_listened_track = self._most_listened_track(active_tracks)
        longest_track = self._longest_track(active_tracks)

        return DashboardData(
            liked_tracks_count=len(active_tracks),
            removed_tracks_count=len(removed_tracks),
            total_tracks_count=len(active_tracks) + len(removed_tracks),
            total_duration_seconds=total_duration_seconds,
            total_duration_text=self._format_duration(total_duration_seconds),
            monthly_listens_known_count=len(monthly_listens_values),
            monthly_listens_coverage_percent=monthly_coverage,
            average_monthly_listens=mean(monthly_listens_values) if monthly_listens_values else None,
            median_monthly_listens=median(monthly_listens_values) if monthly_listens_values else None,
            most_listened_track=most_listened_track,
            most_listened_artist=most_listened_artist,
            most_used_tag=top_tags[0] if top_tags else None,
            longest_track=longest_track,
            top_tags=top_tags,
            top_artists=top_artists,
            discovery_recommendations=discovery_tracks,
            relisten_recommendations=self._build_dashboard_recommendations(active_tracks),
        )

    def refresh_dashboard(self) -> DashboardData:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        dashboard = self.dashboard_data()
        self.dashboard_path.write_text(self._render_dashboard(dashboard), encoding="utf-8")
        return dashboard

    def read_discovery_tracks(self) -> list[DiscoveryTrackInfo]:
        tracks: list[DiscoveryTrackInfo] = []
        if not self.recommendations_dir.exists():
            return tracks

        for path in sorted(self.recommendations_dir.glob("*.md")):
            track = self._read_discovery_track(path)
            if track is not None:
                tracks.append(track)
        return tracks

    def save_discovery_tracks(self, tracks: list[DiscoveryTrackInfo]) -> DiscoverySummary:
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.recommendations_dir.mkdir(parents=True, exist_ok=True)

        managed_files = self._scan_discovery_files()
        existing_track_ids = set(managed_files)
        unmanaged_names = {
            path.name for path in self.recommendations_dir.glob("*.md") if path not in managed_files.values()
        }
        desired_paths = self._build_discovery_paths(tracks, unmanaged_names, managed_files)

        for track in tracks:
            desired_paths[track.track_id].write_text(self._render_discovery_track(track), encoding="utf-8")

        total = len(list(self.recommendations_dir.glob("*.md")))
        added = sum(1 for track in tracks if track.track_id not in existing_track_ids)
        skipped = len(tracks) - added
        self.refresh_dashboard()
        return DiscoverySummary(
            added=added,
            skipped=skipped,
            removed_liked=0,
            cleared=0,
            total=total,
        )

    def remove_discovery_tracks_by_ids(self, track_ids: set[str]) -> int:
        if not track_ids or not self.recommendations_dir.exists():
            return 0

        removed = 0
        for path in self.recommendations_dir.glob("*.md"):
            track_id = self._read_track_id(path)
            if track_id is None or track_id not in track_ids:
                continue
            path.unlink()
            removed += 1

        if removed > 0:
            self.refresh_dashboard()
        return removed

    def clear_discovery_tracks(self) -> DiscoverySummary:
        cleared = 0
        if self.recommendations_dir.exists():
            for path in self.recommendations_dir.glob("*.md"):
                path.unlink()
                cleared += 1
        self.refresh_dashboard()
        return DiscoverySummary(
            added=0,
            skipped=0,
            removed_liked=0,
            cleared=cleared,
            total=0,
        )

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

    def _read_saved_tracks(self, directory: Path) -> list[SavedTrackInfo]:
        saved_tracks: list[SavedTrackInfo] = []
        if not directory.exists():
            return saved_tracks

        for path in sorted(directory.glob("*.md")):
            track = self._read_saved_track(path)
            if track is not None:
                saved_tracks.append(track)

        return saved_tracks

    def _scan_managed_files(self) -> dict[str, Path]:
        managed: dict[str, Path] = {}
        for directory in (self.tracks_dir, self.removed_dir):
            for path in directory.glob("*.md"):
                track_id = self._read_track_id(path)
                if track_id is not None:
                    managed[track_id] = path
        return managed

    def _build_discovery_paths(
        self,
        tracks: list[DiscoveryTrackInfo],
        reserved_names: set[str],
        managed_files: dict[str, Path],
    ) -> dict[str, Path]:
        desired_paths: dict[str, Path] = {}
        used_names = set(reserved_names)

        for track in tracks:
            current_path = managed_files.get(track.track_id)
            if current_path is not None:
                desired_paths[track.track_id] = current_path
                used_names.add(current_path.name)
                continue
            filename = self._unique_filename(track, used_names)
            used_names.add(filename)
            desired_paths[track.track_id] = self.recommendations_dir / filename

        return desired_paths

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

    def _unique_filename(self, track: TrackInfo | DiscoveryTrackInfo, used_names: set[str]) -> str:
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

    def _primary_artist(self, track: TrackInfo | DiscoveryTrackInfo) -> str:
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
        duration_seconds = self._read_optional_frontmatter_int(content, "duration_seconds") or 0
        source_position = self._read_optional_frontmatter_int(content, "position")
        track_id = self._read_frontmatter_value(content, "track_id")

        if title is None:
            return None

        normalized_system_tags = self._normalize_tags(system_tags or [])
        normalized_user_tags = self._normalize_tags(user_tags or [])
        tags = self._normalize_tags(normalized_system_tags, normalized_user_tags)
        if user_tags is None and system_tags is None:
            tags = self._normalize_tags(self._read_frontmatter_list(content, "tags"))
            normalized_system_tags = []
            normalized_user_tags = list(tags)

        return SavedTrackInfo(
            track_id=track_id,
            title=title,
            artists=artists,
            tags=tags,
            system_tags=normalized_system_tags,
            user_tags=normalized_user_tags,
            duration_seconds=duration_seconds,
            monthly_listens=monthly_listens,
            source_position=source_position,
        )

    def _scan_discovery_files(self) -> dict[str, Path]:
        managed: dict[str, Path] = {}
        if not self.recommendations_dir.exists():
            return managed
        for path in self.recommendations_dir.glob("*.md"):
            track_id = self._read_track_id(path)
            if track_id is not None:
                managed[track_id] = path
        return managed

    def _read_discovery_track(self, path: Path) -> DiscoveryTrackInfo | None:
        content = path.read_text(encoding="utf-8")
        track_id = self._read_frontmatter_value(content, "track_id")
        title = self._read_frontmatter_value(content, "title")
        if track_id is None or title is None:
            return None

        return DiscoveryTrackInfo(
            track_id=track_id,
            title=title,
            artists=self._read_frontmatter_list(content, "artists"),
            album=self._read_frontmatter_value(content, "album") or "",
            album_id=None,
            system_tags=self._read_frontmatter_list(content, "system_tags"),
            year=self._read_optional_frontmatter_int(content, "year"),
            cover_url=self._read_frontmatter_value(content, "cover_url") or "",
            duration_seconds=self._read_optional_frontmatter_int(content, "duration_seconds") or 0,
            yandex_url=self._read_frontmatter_value(content, "yandex_url") or "",
            monthly_listens=self._read_optional_frontmatter_int(content, "monthly_listens"),
            discovery_sources=self._read_frontmatter_list(content, "discovery_sources"),
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

    def _render_discovery_track(self, track: DiscoveryTrackInfo) -> str:
        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        system_tags = self._normalize_tags(track.system_tags)
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
            f"discovery_sources: [{', '.join(self._quote_yaml(source) for source in track.discovery_sources)}]",
            f"year: {year_value}",
            f"monthly_listens: {monthly_listens_value}",
            f'cover_url: "{self._escape_yaml(track.cover_url)}"',
            f"duration_seconds: {track.duration_seconds}",
            'source: "discovery"',
            f'yandex_url: "{self._escape_yaml(track.yandex_url)}"',
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
            f"Discovery sources: {track.explain or '-'}",
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

    def _build_top_tag_entries(self, tracks: list[SavedTrackInfo]) -> list[DashboardStatEntry]:
        counts: dict[str, int] = {}
        names: dict[str, str] = {}
        order: dict[str, int] = {}
        source_priority: dict[str, int] = {}
        next_index = 0
        for track in tracks:
            ordered_tags = self._normalize_tags(track.system_tags, track.user_tags)
            for tag in ordered_tags:
                key = tag.casefold()
                counts[key] = counts.get(key, 0) + 1
                names.setdefault(key, tag)
                if key not in order:
                    order[key] = next_index
                    next_index += 1
                    source_priority[key] = 0 if tag in track.system_tags else 1
                elif key in track.system_tags:
                    source_priority[key] = 0

        ordered_keys = sorted(counts, key=lambda key: (-counts[key], source_priority[key], order[key]))
        return [
            DashboardStatEntry(name=names[key], count=counts[key])
            for key in ordered_keys[:5]
        ]

    def _build_top_artist_entries(
        self,
        tracks: list[SavedTrackInfo],
    ) -> list[DashboardStatEntry]:
        counts: dict[str, int] = {}
        listens: dict[str, int] = {}
        names: dict[str, str] = {}
        order: dict[str, int] = {}
        primary_priority: dict[str, int] = {}
        next_index = 0

        for track in tracks:
            for artist_index, artist in enumerate(track.artists):
                key = artist.casefold()
                counts[key] = counts.get(key, 0) + 1
                listens[key] = listens.get(key, 0) + (track.monthly_listens or 0)
                names.setdefault(key, artist)
                if key not in order:
                    order[key] = next_index
                    next_index += 1
                    primary_priority[key] = 0 if artist_index == 0 else 1
                elif artist_index == 0:
                    primary_priority[key] = 0

        ordered_keys = sorted(
            counts,
            key=lambda key: (
                -counts[key],
                primary_priority[key],
                order[key],
            ),
        )
        return [
            DashboardStatEntry(
                name=names[key],
                count=counts[key],
                monthly_listens=listens[key],
            )
            for key in ordered_keys[:5]
        ]

    def _most_listened_artist(self, tracks: list[SavedTrackInfo]) -> DashboardStatEntry | None:
        counts: dict[str, int] = {}
        listens: dict[str, int] = {}
        names: dict[str, str] = {}
        order: dict[str, int] = {}
        primary_priority: dict[str, int] = {}
        next_index = 0

        for track in tracks:
            for artist_index, artist in enumerate(track.artists):
                key = artist.casefold()
                counts[key] = counts.get(key, 0) + 1
                listens[key] = listens.get(key, 0) + (track.monthly_listens or 0)
                names.setdefault(key, artist)
                if key not in order:
                    order[key] = next_index
                    next_index += 1
                    primary_priority[key] = 0 if artist_index == 0 else 1
                elif artist_index == 0:
                    primary_priority[key] = 0

        if not counts:
            return None

        best_key = min(
            counts,
            key=lambda key: (
                -listens[key],
                -counts[key],
                primary_priority[key],
                order[key],
            ),
        )
        return DashboardStatEntry(
            name=names[best_key],
            count=counts[best_key],
            monthly_listens=listens[best_key],
        )

    def _most_listened_track(self, tracks: list[SavedTrackInfo]) -> TrackDashboardEntry | None:
        ranked_tracks = [track for track in tracks if track.monthly_listens is not None]
        if not ranked_tracks:
            return None

        track = min(
            ranked_tracks,
            key=lambda item: (
                -(item.monthly_listens or 0),
                item.source_position if item.source_position is not None else float("inf"),
                item.title.casefold(),
                ",".join(artist.casefold() for artist in item.artists),
            ),
        )
        return self._to_track_dashboard_entry(track)

    def _longest_track(self, tracks: list[SavedTrackInfo]) -> TrackDashboardEntry | None:
        if not tracks:
            return None

        track = min(
            tracks,
            key=lambda item: (
                -item.duration_seconds,
                item.source_position if item.source_position is not None else float("inf"),
                item.title.casefold(),
            ),
        )
        return self._to_track_dashboard_entry(track)

    def _to_track_dashboard_entry(self, track: SavedTrackInfo) -> TrackDashboardEntry:
        return TrackDashboardEntry(
            title=track.title,
            artists=track.artists,
            monthly_listens=track.monthly_listens,
            duration_seconds=track.duration_seconds,
            duration_text=self._format_duration(track.duration_seconds),
        )

    def _build_dashboard_recommendations(
        self,
        tracks: list[SavedTrackInfo],
    ) -> list[RelistenRecommendationEntry]:
        profile_tracks = sorted(
            [track for track in tracks if track.monthly_listens is not None and track.monthly_listens > 0],
            key=lambda track: (
                -(track.monthly_listens or 0),
                track.source_position if track.source_position is not None else float("inf"),
                track.title.casefold(),
            ),
        )[:20]
        if not profile_tracks:
            return []

        recent_track_ids = {track.track_id for track in profile_tracks if track.track_id is not None}
        artist_profile = self._normalized_name_set(
            artist for track in profile_tracks for artist in track.artists
        )
        genre_profile = self._normalized_name_set(
            tag for track in profile_tracks for tag in track.system_tags
        )
        user_tag_profile = self._normalized_name_set(
            tag for track in profile_tracks for tag in track.user_tags
        )
        recommendations: list[RelistenRecommendationEntry] = []

        for track in tracks:
            if track.track_id in recent_track_ids:
                continue

            matched_artists = self._matching_values(track.artists, artist_profile)
            matched_genres = self._matching_values(track.system_tags, genre_profile)
            matched_user_tags = self._matching_values(track.user_tags, user_tag_profile)
            if not matched_artists and not matched_genres and not matched_user_tags:
                continue

            score = (
                len(matched_artists) * 10
                + len(matched_genres) * 4
                + len(matched_user_tags) * 2
                + self._staleness_bonus(track.monthly_listens)
            )
            recommendations.append(
                RelistenRecommendationEntry(
                    title=track.title,
                    artists=track.artists,
                    monthly_listens=track.monthly_listens,
                    position=track.source_position,
                    archived=False,
                    matched_artists=matched_artists,
                    matched_genres=matched_genres,
                    matched_user_tags=matched_user_tags,
                    score=score,
                )
            )

        recommendations.sort(
            key=lambda entry: (
                -entry.score,
                entry.monthly_listens if entry.monthly_listens is not None else -1,
                entry.position if entry.position is not None else float("inf"),
                entry.title.casefold(),
            )
        )
        return recommendations[:10]

    def _render_dashboard(self, dashboard: DashboardData) -> str:
        lines = [
            "# Music Dashboard",
            "",
            "## Overview",
            f"- Liked tracks: {dashboard.liked_tracks_count}",
            f"- Removed tracks: {dashboard.removed_tracks_count}",
            f"- Total tracks known: {dashboard.total_tracks_count}",
            f"- Most listened track: {self._render_track_summary(dashboard.most_listened_track)}",
            f"- Most listened artist: {self._render_artist_summary(dashboard.most_listened_artist)}",
            f"- Most used tag: {self._render_tag_summary(dashboard.most_used_tag)}",
            f"- Total duration: {dashboard.total_duration_text}",
            (
                f"- Average monthly listens: {dashboard.average_monthly_listens:.2f}"
                if dashboard.average_monthly_listens is not None
                else "- Average monthly listens: -"
            ),
            (
                f"- Median monthly listens: {dashboard.median_monthly_listens:.2f}"
                if dashboard.median_monthly_listens is not None
                else "- Median monthly listens: -"
            ),
            (
                f"- Monthly listens coverage: {dashboard.monthly_listens_known_count}/"
                f"{dashboard.liked_tracks_count} ({dashboard.monthly_listens_coverage_percent:.2f}%)"
            ),
            "",
            "## Top Tags",
        ]

        if dashboard.top_tags:
            lines.extend(
                [
                    f"{index}. {entry.name} ({entry.count} track{'' if entry.count == 1 else 's'})"
                    for index, entry in enumerate(dashboard.top_tags, start=1)
                ]
            )
        else:
            lines.append("- None")

        lines.extend(["", "## Top Artists"])
        if dashboard.top_artists:
            lines.extend(
                [
                    f"{index}. {entry.name} ({entry.count} track{'' if entry.count == 1 else 's'})"
                    for index, entry in enumerate(dashboard.top_artists, start=1)
                ]
            )
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## Longest Track",
                self._render_longest_track_summary(dashboard.longest_track),
                "",
                "## Discovery Recommendations",
            ]
        )
        if dashboard.discovery_recommendations:
            lines.extend(
                [
                    (
                        f"{index}. {entry.title} - "
                        f"{', '.join(entry.artists) if entry.artists else 'Unknown Artist'} "
                        f"({entry.explain})"
                    )
                    for index, entry in enumerate(dashboard.discovery_recommendations, start=1)
                ]
            )
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## Re-listen Recommendations",
            ]
        )
        if dashboard.relisten_recommendations:
            lines.extend(
                [
                    (
                        f"{index}. {entry.title} - "
                        f"{', '.join(entry.artists) if entry.artists else 'Unknown Artist'} "
                        f"({entry.explain})"
                    )
                    for index, entry in enumerate(dashboard.relisten_recommendations, start=1)
                ]
            )
        else:
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)

    def _render_track_summary(self, track: TrackDashboardEntry | None) -> str:
        if track is None:
            return "-"

        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        listens = track.monthly_listens if track.monthly_listens is not None else 0
        return f"{track.title} - {artists} ({listens} listens)"

    def _render_artist_summary(self, artist: DashboardStatEntry | None) -> str:
        if artist is None:
            return "-"

        listens = artist.monthly_listens if artist.monthly_listens is not None else 0
        label = "track" if artist.count == 1 else "tracks"
        return f"{artist.name} ({listens} listens across {artist.count} {label})"

    def _normalized_name_set(self, values: object) -> set[str]:
        normalized: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                continue
            cleaned = value.strip().casefold()
            if cleaned:
                normalized.add(cleaned)
        return normalized

    def _matching_values(self, values: list[str], profile: set[str]) -> list[str]:
        matched: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = value.strip()
            key = cleaned.casefold()
            if not cleaned or key not in profile or key in seen:
                continue
            matched.append(cleaned)
            seen.add(key)
        return matched

    def _staleness_bonus(self, monthly_listens: int | None) -> int:
        if monthly_listens is None:
            return 6
        if monthly_listens <= 0:
            return 5
        if monthly_listens == 1:
            return 4
        if monthly_listens <= 3:
            return 2
        return 0

    def _render_tag_summary(self, tag: DashboardStatEntry | None) -> str:
        if tag is None:
            return "-"

        label = "track" if tag.count == 1 else "tracks"
        return f"{tag.name} ({tag.count} {label})"

    def _render_longest_track_summary(self, track: TrackDashboardEntry | None) -> str:
        if track is None:
            return "-"

        artists = ", ".join(track.artists) if track.artists else "Unknown Artist"
        return f"{track.title} - {artists} ({track.duration_text})"
