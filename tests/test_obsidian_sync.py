from datetime import datetime, timezone
from pathlib import Path

from music_synchronizer.models import TrackInfo
from music_synchronizer.obsidian import ObsidianExporter


def _track(track_id: str, position: int, title: str = "Song") -> TrackInfo:
    return TrackInfo(
        track_id=track_id,
        title=title,
        artists=["Artist"],
        album="Album",
        tags=["indie"],
        duration_seconds=180,
        source_position=position,
        yandex_url=f"https://music.yandex.ru/track/{track_id}",
    )


def test_export_writes_playlist_and_track_notes(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First"), _track("102", 2, "Second")], synced_at=synced_at)

    track_note = (tmp_path / "tracks" / "First.md").read_text(encoding="utf-8")

    assert not (tmp_path / "playlist.md").exists()
    assert 'track_id: "101"' in track_note
    assert 'system_tags: ["indie"]' in track_note
    assert "user_tags: []" in track_note
    assert "\ntags:" not in track_note
    assert 'source: "likes"' in track_note
    assert 'synced_at: "2026-04-24T12:00:00+00:00"' in track_note
    assert "# First" in track_note
    assert "https://music.yandex.ru/track/101" in track_note


def test_export_moves_removed_tracks_to_archive(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1), _track("102", 2)], synced_at=synced_at)
    exporter.sync([_track("101", 1)], synced_at=synced_at)

    assert (tmp_path / "tracks" / "Song.md").exists()
    assert not (tmp_path / "tracks" / "Song - Artist.md").exists()
    assert (tmp_path / "tracks" / "_removed" / "Song - Artist.md").exists()


def test_export_restores_archived_track_when_it_returns(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1), _track("102", 2)], synced_at=synced_at)
    exporter.sync([_track("101", 1)], synced_at=synced_at)
    exporter.sync([_track("101", 1), _track("102", 2)], synced_at=synced_at)

    assert (tmp_path / "tracks" / "Song - Artist.md").exists()
    assert not (tmp_path / "tracks" / "_removed" / "Song - Artist.md").exists()


def test_export_uses_title_and_artist_when_titles_conflict(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync(
        [
            _track("101", 1, "Same"),
            TrackInfo(
                track_id="102",
                title="Same",
                artists=["Other Artist"],
                album="Album",
                tags=["synthpop"],
                duration_seconds=180,
                source_position=2,
                yandex_url="https://music.yandex.ru/track/102",
            ),
        ],
        synced_at=synced_at,
    )

    assert (tmp_path / "tracks" / "Same.md").exists()
    assert (tmp_path / "tracks" / "Same - Other Artist.md").exists()


def test_export_removes_legacy_playlist_file(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    (tmp_path / "playlist.md").write_text("legacy", encoding="utf-8")

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    assert not (tmp_path / "playlist.md").exists()


def test_export_preserves_manual_tags_on_resync(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    note_path = tmp_path / "tracks" / "First.md"
    note_path.write_text(
        note_path.read_text(encoding="utf-8").replace(
            "user_tags: []",
            'user_tags: ["manual-tag"]',
        ),
        encoding="utf-8",
    )

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    track_note = note_path.read_text(encoding="utf-8")
    assert 'system_tags: ["indie"]' in track_note
    assert 'user_tags: ["manual-tag"]' in track_note


def test_export_updates_system_tags_without_overwriting_user_tags(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    note_path = tmp_path / "tracks" / "First.md"
    note_path.write_text(
        note_path.read_text(encoding="utf-8").replace(
            "user_tags: []",
            'user_tags: ["manual-tag"]',
        ),
        encoding="utf-8",
    )

    exporter.sync(
        [
            TrackInfo(
                track_id="101",
                title="First",
                artists=["Artist"],
                album="Album",
                tags=["dream-pop"],
                duration_seconds=180,
                source_position=1,
                yandex_url="https://music.yandex.ru/track/101",
            )
        ],
        synced_at=synced_at,
    )

    track_note = note_path.read_text(encoding="utf-8")
    assert 'system_tags: ["dream-pop"]' in track_note
    assert 'user_tags: ["manual-tag"]' in track_note


def test_export_deduplicates_user_and_system_tags_independently(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    note_path = tmp_path / "tracks" / "First.md"
    note_path.write_text(
        note_path.read_text(encoding="utf-8").replace(
            "user_tags: []",
            'user_tags: ["manual-tag", "manual-tag", " manual-tag ", ""]',
        ),
        encoding="utf-8",
    )

    exporter.sync(
        [
            TrackInfo(
                track_id="101",
                title="First",
                artists=["Artist"],
                album="Album",
                tags=["dream-pop", " dream-pop ", "", "indie"],
                duration_seconds=180,
                source_position=1,
                yandex_url="https://music.yandex.ru/track/101",
            )
        ],
        synced_at=synced_at,
    )

    track_note = note_path.read_text(encoding="utf-8")
    assert 'system_tags: ["dream-pop", "indie"]' in track_note
    assert 'user_tags: ["manual-tag"]' in track_note


def test_export_migrates_legacy_tags_to_user_tags(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    note_path = tracks_dir / "First.md"
    note_path.write_text(
        "\n".join(
            [
                "---",
                'track_id: "101"',
                'title: "First"',
                'artists: ["Artist"]',
                'album: "Album"',
                'tags: ["legacy-tag", " legacy-tag ", ""]',
                "duration_seconds: 180",
                "position: 1",
                'source: "likes"',
                'yandex_url: "https://music.yandex.ru/track/101"',
                'synced_at: "2026-04-24T12:00:00+00:00"',
                "---",
                "",
                "# First",
                "",
            ]
        ),
        encoding="utf-8",
    )

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    track_note = note_path.read_text(encoding="utf-8")
    assert 'system_tags: ["indie"]' in track_note
    assert 'user_tags: ["legacy-tag"]' in track_note
    assert "\ntags:" not in track_note


def test_export_preserves_multiline_user_tags_on_resync(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    note_path = tmp_path / "tracks" / "First.md"
    note_path.write_text(
        "\n".join(
            [
                "---",
                'track_id: "101"',
                'title: "First"',
                'artists: ["Artist"]',
                'album: "Album"',
                'system_tags: ["indie"]',
                "user_tags:",
                '  - "manual-tag"',
                '  - "manual-tag-2"',
                "duration_seconds: 180",
                "position: 1",
                'source: "likes"',
                'yandex_url: "https://music.yandex.ru/track/101"',
                'synced_at: "2026-04-24T12:00:00+00:00"',
                "---",
                "",
                "# First",
                "",
            ]
        ),
        encoding="utf-8",
    )

    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)

    track_note = note_path.read_text(encoding="utf-8")
    assert 'user_tags: ["manual-tag", "manual-tag-2"]' in track_note
