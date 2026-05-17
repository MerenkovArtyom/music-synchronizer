from datetime import datetime, timezone
from pathlib import Path

import pytest

from music_synchronizer.models import DiscoveryTrackInfo, TrackInfo
from music_synchronizer.obsidian import ObsidianExporter


def _track(track_id: str, position: int, title: str = "Song", monthly_listens: int | None = None) -> TrackInfo:
    return TrackInfo(
        track_id=track_id,
        title=title,
        artists=["Artist"],
        album="Album",
        tags=["indie"],
        year=2024,
        cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
        duration_seconds=180,
        source_position=position,
        yandex_url=f"https://music.yandex.ru/track/{track_id}",
        monthly_listens=monthly_listens,
    )


def _discovery_track(
    track_id: str,
    title: str,
    *,
    sources: list[str] | None = None,
    monthly_listens: int | None = None,
) -> DiscoveryTrackInfo:
    return DiscoveryTrackInfo(
        track_id=track_id,
        title=title,
        artists=["Artist"],
        album="Album",
        system_tags=["indie"],
        year=2024,
        cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
        duration_seconds=180,
        yandex_url=f"https://music.yandex.ru/track/{track_id}",
        monthly_listens=monthly_listens,
        discovery_sources=sources or ["artist-popular"],
    )


def test_export_writes_playlist_and_track_notes(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    summary = exporter.sync([_track("101", 1, "First"), _track("102", 2, "Second")], synced_at=synced_at)

    track_note = (tmp_path / "tracks" / "First.md").read_text(encoding="utf-8")

    assert not (tmp_path / "playlist.md").exists()
    assert 'track_id: "101"' in track_note
    assert 'system_tags: ["indie"]' in track_note
    assert "user_tags: []" in track_note
    assert "\ntags:" not in track_note
    assert "year: 2024" in track_note
    assert "monthly_listens: null" in track_note
    assert 'cover_url: "https://avatars.yandex.net/get-music-content/cover.jpg"' in track_note
    assert 'source: "likes"' in track_note
    assert 'synced_at: "2026-04-24T12:00:00+00:00"' in track_note
    assert "# First" in track_note
    assert "Year: 2024" in track_note
    assert "Monthly listens (30d): -" in track_note
    assert "Duration: 3:00" in track_note
    assert "![Album cover](https://avatars.yandex.net/get-music-content/cover.jpg)" in track_note
    assert "https://music.yandex.ru/track/101" in track_note
    assert summary.added == 2
    assert summary.unchanged == 0
    assert summary.removed == 0


def test_export_writes_discovery_notes_to_recommendations(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)

    summary = exporter.save_discovery_tracks([
        _discovery_track("201", "Discovery Song", sources=["artist-popular", "similar"], monthly_listens=4)
    ])

    note_path = tmp_path / "recommendations" / "Discovery Song.md"
    note = note_path.read_text(encoding="utf-8")

    assert note_path.exists()
    assert 'track_id: "201"' in note
    assert 'source: "discovery"' in note
    assert 'discovery_sources: ["artist-popular", "similar"]' in note
    assert "Monthly listens (30d): 4" in note
    assert summary.added == 1
    assert summary.total == 1


def test_clear_discovery_tracks_only_removes_recommendations(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "Liked")], synced_at=synced_at)
    exporter.save_discovery_tracks([
        _discovery_track("201", "Discovery Song"),
        _discovery_track("202", "Another Discovery"),
    ])

    summary = exporter.clear_discovery_tracks()

    assert summary.cleared == 2
    assert (tmp_path / "tracks" / "Liked.md").exists()
    assert not (tmp_path / "recommendations" / "Discovery Song.md").exists()
    assert not (tmp_path / "recommendations" / "Another Discovery.md").exists()


def test_remove_discovery_tracks_by_ids_removes_only_matching_notes(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    exporter.save_discovery_tracks([
        _discovery_track("201", "Discovery Song"),
        _discovery_track("202", "Another Discovery"),
    ])

    removed = exporter.remove_discovery_tracks_by_ids({"201"})

    assert removed == 1
    assert not (tmp_path / "recommendations" / "Discovery Song.md").exists()
    assert (tmp_path / "recommendations" / "Another Discovery.md").exists()


def test_vault_view_lists_managed_music_directories_and_root_markdown(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    (tmp_path / "artists").mkdir()
    (tmp_path / "tags").mkdir()
    (tmp_path / "tracks").mkdir()
    (tmp_path / "tracks" / "_removed").mkdir(parents=True)
    (tmp_path / "recommendations").mkdir()
    (tmp_path / "artists" / "Artist.md").write_text("# Artist\n", encoding="utf-8")
    (tmp_path / "tags" / "Rock.md").write_text("# Rock\n", encoding="utf-8")
    (tmp_path / "tracks" / "Liked.md").write_text("# Liked\n", encoding="utf-8")
    (tmp_path / "tracks" / "_removed" / "Archived.md").write_text("# Archived\n", encoding="utf-8")
    (tmp_path / "recommendations" / "Discovery.md").write_text("# Discovery\n", encoding="utf-8")
    (tmp_path / "dashboard.md").write_text("# Dashboard\n", encoding="utf-8")
    (tmp_path / ".music_sync_snapshot.json").write_text("{}", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("skip", encoding="utf-8")

    payload = exporter.vault_view()

    assert payload.vault_path == str(tmp_path)
    assert payload.selected_path is None
    assert payload.selected_note is None
    assert [node.path for node in payload.tree] == [
        "dashboard.md",
        "artists",
        "recommendations",
        "tags",
        "tracks",
    ]
    assert payload.tree[1].children is not None
    assert [node.path for node in payload.tree[1].children] == ["artists/Artist.md"]
    assert payload.tree[2].children is not None
    assert [node.path for node in payload.tree[2].children] == ["recommendations/Discovery.md"]
    assert payload.tree[3].children is not None
    assert [node.path for node in payload.tree[3].children] == ["tags/Rock.md"]
    assert payload.tree[4].children is not None
    assert [node.path for node in payload.tree[4].children] == [
        "tracks/_removed",
        "tracks/Liked.md",
    ]


def test_vault_view_reads_selected_note_without_frontmatter(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    note_path = tmp_path / "tracks" / "Liked.md"
    note_path.parent.mkdir(parents=True)
    note_path.write_text(
        "---\n"
        'title: "Liked"\n'
        "---\n"
        "\n"
        "# Liked\n"
        "\n"
        "Body text.\n",
        encoding="utf-8",
    )

    payload = exporter.vault_view(selected_path="tracks/Liked.md")

    assert payload.selected_path == "tracks/Liked.md"
    assert payload.selected_note is not None
    assert payload.selected_note.name == "Liked.md"
    assert payload.selected_note.path == "tracks/Liked.md"
    assert payload.selected_note.content == "# Liked\n\nBody text.\n"


def test_vault_view_rejects_paths_outside_vault(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)

    with pytest.raises(ValueError, match="outside the configured vault"):
        exporter.vault_view(selected_path="../secrets.md")


def test_vault_view_fails_for_missing_selected_note(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)

    with pytest.raises(FileNotFoundError, match="Note not found"):
        exporter.vault_view(selected_path="tracks/Missing.md")


def test_dashboard_omits_discovery_and_relisten_recommendation_sections(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "Liked", monthly_listens=3)], synced_at=synced_at)
    exporter.save_discovery_tracks([_discovery_track("201", "Discovery Song", sources=["similar"])])
    dashboard = (tmp_path / "dashboard.md").read_text(encoding="utf-8")

    assert "## Discovery Recommendations" not in dashboard
    assert "## Re-listen Recommendations" not in dashboard
    assert "Discovery Song - Artist (similar)" not in dashboard


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
                year=2025,
                cover_url="https://avatars.yandex.net/get-music-content/other-cover.jpg",
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
                year=2024,
                cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
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
                year=2024,
                cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
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
                "year: 2024",
                'cover_url: "https://avatars.yandex.net/get-music-content/cover.jpg"',
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
                "year: 2024",
                'cover_url: "https://avatars.yandex.net/get-music-content/cover.jpg"',
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


def test_export_skips_cover_image_and_uses_fallback_values_when_metadata_missing(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync(
        [
            TrackInfo(
                track_id="101",
                title="First",
                artists=["Artist"],
                album="Album",
                tags=["indie"],
                year=None,
                cover_url="",
                duration_seconds=65,
                source_position=1,
                yandex_url="https://music.yandex.ru/track/101",
            )
        ],
        synced_at=synced_at,
    )

    track_note = (tmp_path / "tracks" / "First.md").read_text(encoding="utf-8")
    assert "year: null" in track_note
    assert 'cover_url: ""' in track_note
    assert "Year: -" in track_note
    assert "Monthly listens (30d): -" in track_note
    assert "Duration: 1:05" in track_note
    assert "![Album cover]" not in track_note


def test_export_writes_monthly_listens_when_available(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First", monthly_listens=7)], synced_at=synced_at)

    track_note = (tmp_path / "tracks" / "First.md").read_text(encoding="utf-8")

    assert "monthly_listens: 7" in track_note
    assert "Monthly listens (30d): 7" in track_note


def test_export_reuses_snapshot_and_skips_unchanged_rewrite(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    first_synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    second_synced_at = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)

    first_summary = exporter.sync([_track("101", 1, "First")], synced_at=first_synced_at)
    second_summary = exporter.sync([_track("101", 1, "First")], synced_at=second_synced_at)

    track_note = (tmp_path / "tracks" / "First.md").read_text(encoding="utf-8")
    snapshot = (tmp_path / ".music_sync_snapshot.json").read_text(encoding="utf-8")

    assert first_summary.added == 1
    assert first_summary.unchanged == 0
    assert first_summary.removed == 0
    assert second_summary.added == 0
    assert second_summary.unchanged == 1
    assert second_summary.removed == 0
    assert 'synced_at: "2026-04-24T12:00:00+00:00"' in track_note
    assert '"101"' in snapshot


def test_export_counts_new_removed_and_changed_tracks_from_snapshot(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    first_synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
    second_synced_at = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First"), _track("102", 2, "Second")], synced_at=first_synced_at)
    summary = exporter.sync(
        [
            TrackInfo(
                track_id="101",
                title="First",
                artists=["Artist"],
                album="Album Deluxe",
                tags=["indie"],
                year=2024,
                cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
                duration_seconds=180,
                source_position=1,
                yandex_url="https://music.yandex.ru/track/101",
            ),
            _track("103", 2, "Third"),
        ],
        synced_at=second_synced_at,
    )

    changed_note = (tmp_path / "tracks" / "First.md").read_text(encoding="utf-8")

    assert summary.added == 1
    assert summary.unchanged == 0
    assert summary.removed == 1
    assert "Album: Album Deluxe" in changed_note
    assert not (tmp_path / "tracks" / "Second.md").exists()
    assert (tmp_path / "tracks" / "_removed" / "Second.md").exists()


def test_export_restores_removed_track_as_added(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync([_track("101", 1, "First"), _track("102", 2, "Second")], synced_at=synced_at)
    exporter.sync([_track("101", 1, "First")], synced_at=synced_at)
    summary = exporter.sync([_track("101", 1, "First"), _track("102", 2, "Second")], synced_at=synced_at)

    assert summary.added == 1
    assert summary.unchanged == 1
    assert summary.removed == 0
    assert (tmp_path / "tracks" / "Second.md").exists()
    assert not (tmp_path / "tracks" / "_removed" / "Second.md").exists()


def test_top_listen_tracks_reads_only_active_notes(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    tracks_dir = tmp_path / "tracks"
    removed_dir = tracks_dir / "_removed"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    removed_dir.mkdir(parents=True, exist_ok=True)

    (tracks_dir / "First.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "101"',
                'title: "First"',
                'artists: ["Artist A"]',
                "monthly_listens: 7",
                "position: 2",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tracks_dir / "Second.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "102"',
                'title: "Second"',
                'artists: ["Artist B"]',
                "monthly_listens: null",
                "position: 5",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tracks_dir / "Broken.md").write_text(
        "\n".join(
            [
                "---",
                'artists: ["Artist C"]',
                "monthly_listens: 3",
                "position: 1",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (removed_dir / "Archived.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "999"',
                'title: "Archived"',
                'artists: ["Archived Artist"]',
                "monthly_listens: 99",
                "position: 1",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    tracks = exporter.top_listen_tracks()

    assert [(track.title, track.monthly_listens, track.source_position) for track in tracks] == [
        ("First", 7, 2),
        ("Second", None, 5),
    ]


def test_top_listen_tracks_preserves_missing_position_for_sort_fallback(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)

    (tracks_dir / "NoPosition.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "101"',
                'title: "No Position"',
                'artists: ["Artist"]',
                "monthly_listens: 4",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    tracks = exporter.top_listen_tracks()

    assert len(tracks) == 1
    assert tracks[0].title == "No Position"
    assert tracks[0].source_position is None


def test_dashboard_data_uses_local_active_and_removed_notes(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    tracks_dir = tmp_path / "tracks"
    removed_dir = tracks_dir / "_removed"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    removed_dir.mkdir(parents=True, exist_ok=True)

    (tracks_dir / "First.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "101"',
                'title: "First"',
                'artists: ["Artist A"]',
                'system_tags: ["indie", "focus"]',
                'user_tags: ["night"]',
                "monthly_listens: 7",
                "duration_seconds: 240",
                "position: 2",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tracks_dir / "Second.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "102"',
                'title: "Second"',
                'artists: ["Artist A", "Guest"]',
                'system_tags: ["indie"]',
                "user_tags: []",
                "monthly_listens: 3",
                "duration_seconds: 180",
                "position: 1",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (tracks_dir / "Third.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "103"',
                'title: "Third"',
                'artists: ["Artist B"]',
                'system_tags: ["ambient"]',
                'user_tags: ["focus"]',
                "monthly_listens: null",
                "duration_seconds: 300",
                "position: 3",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (removed_dir / "Archived.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "999"',
                'title: "Archived"',
                'artists: ["Artist Z"]',
                'system_tags: ["indie"]',
                "user_tags: []",
                "monthly_listens: 99",
                "duration_seconds: 400",
                "position: 9",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    dashboard = exporter.dashboard_data()

    assert dashboard.liked_tracks_count == 3
    assert dashboard.removed_tracks_count == 1
    assert dashboard.total_tracks_count == 4
    assert dashboard.total_duration_seconds == 720
    assert dashboard.total_duration_text == "12:00"
    assert dashboard.monthly_listens_known_count == 2
    assert dashboard.monthly_listens_coverage_percent == 66.67
    assert dashboard.average_monthly_listens == 5.0
    assert dashboard.median_monthly_listens == 5.0
    assert dashboard.most_listened_track is not None
    assert dashboard.most_listened_track.title == "First"
    assert dashboard.most_listened_artist is not None
    assert dashboard.most_listened_artist.name == "Artist A"
    assert dashboard.most_listened_artist.monthly_listens == 10
    assert dashboard.most_used_tag is not None
    assert dashboard.most_used_tag.name == "indie"
    assert dashboard.most_used_tag.count == 2
    assert dashboard.longest_track is not None
    assert dashboard.longest_track.title == "Third"
    assert [(entry.name, entry.count) for entry in dashboard.top_tags] == [
        ("indie", 2),
        ("focus", 2),
        ("ambient", 1),
        ("night", 1),
    ]
    assert [(entry.name, entry.count) for entry in dashboard.top_artists] == [
        ("Artist A", 2),
        ("Artist B", 1),
        ("Guest", 1),
    ]


def test_dashboard_file_is_written_in_vault_root(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync(
        [
            _track("101", 1, "First", monthly_listens=7),
            TrackInfo(
                track_id="102",
                title="Second",
                artists=["Other Artist"],
                album="Album",
                tags=["ambient"],
                year=2024,
                cover_url="",
                duration_seconds=300,
                source_position=2,
                yandex_url="https://music.yandex.ru/track/102",
                monthly_listens=3,
            ),
        ],
        synced_at=synced_at,
    )

    dashboard_path = tmp_path / "dashboard.md"
    dashboard_content = dashboard_path.read_text(encoding="utf-8")

    assert dashboard_path.exists()
    assert "# Music Dashboard" in dashboard_content
    assert "- Liked tracks: 2" in dashboard_content
    assert "- Removed tracks: 0" in dashboard_content
    assert "- Total tracks known: 2" in dashboard_content
    assert "- Most listened track: First - Artist (7 listens)" in dashboard_content
    assert "- Most listened artist: Artist (7 listens across 1 track)" in dashboard_content
    assert "- Most used tag: indie (1 track)" in dashboard_content
    assert "- Total duration: 8:00" in dashboard_content
    assert "- Monthly listens coverage: 2/2 (100.00%)" in dashboard_content
    assert "## Top Tags" in dashboard_content
    assert "1. indie (1 track)" in dashboard_content
    assert "2. ambient (1 track)" in dashboard_content
    assert "## Top Artists" in dashboard_content
    assert "1. Artist (1 track)" in dashboard_content
    assert "## Longest Track" in dashboard_content
    assert "Second - Other Artist (5:00)" in dashboard_content


def test_dashboard_refresh_writes_file_without_sync_input(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    tracks_dir = tmp_path / "tracks"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "First.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "101"',
                'title: "First"',
                'artists: ["Artist"]',
                'system_tags: ["indie"]',
                "user_tags: []",
                "monthly_listens: 7",
                "duration_seconds: 180",
                "position: 1",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    dashboard = exporter.refresh_dashboard()
    dashboard_content = (tmp_path / "dashboard.md").read_text(encoding="utf-8")

    assert dashboard.liked_tracks_count == 1
    assert "# Music Dashboard" in dashboard_content
    assert "- Liked tracks: 1" in dashboard_content


def test_recommendation_tracks_reads_active_by_default_and_archive_with_flag(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    tracks_dir = tmp_path / "tracks"
    removed_dir = tracks_dir / "_removed"
    tracks_dir.mkdir(parents=True, exist_ok=True)
    removed_dir.mkdir(parents=True, exist_ok=True)
    (tracks_dir / "Active.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "101"',
                'title: "Active"',
                'artists: ["Artist"]',
                'system_tags: ["indie"]',
                'user_tags: ["night"]',
                "monthly_listens: 2",
                "position: 1",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (removed_dir / "Archived.md").write_text(
        "\n".join(
            [
                "---",
                'track_id: "102"',
                'title: "Archived"',
                'artists: ["Artist"]',
                'system_tags: ["indie"]',
                'user_tags: ["night"]',
                "monthly_listens: 0",
                "position: 2",
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    active_only = exporter.recommendation_tracks()
    with_archived = exporter.recommendation_tracks(include_archived=True)

    assert [track.title for track in active_only] == ["Active"]
    assert [track.title for track in with_archived] == ["Active", "Archived"]


def test_dashboard_file_omits_relisten_recommendations_section(tmp_path: Path) -> None:
    exporter = ObsidianExporter(tmp_path)
    synced_at = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    exporter.sync(
        [
            TrackInfo(
                track_id="101",
                title="Recent",
                artists=["Artist A"],
                album="Album",
                tags=["indie"],
                year=2024,
                cover_url="",
                duration_seconds=180,
                source_position=1,
                yandex_url="https://music.yandex.ru/track/101",
                monthly_listens=9,
            ),
            TrackInfo(
                track_id="102",
                title="Old Match",
                artists=["Artist A"],
                album="Album",
                tags=["indie"],
                year=2024,
                cover_url="",
                duration_seconds=180,
                source_position=2,
                yandex_url="https://music.yandex.ru/track/102",
                monthly_listens=0,
            ),
        ],
        synced_at=synced_at,
    )

    dashboard_content = (tmp_path / "dashboard.md").read_text(encoding="utf-8")

    assert "## Re-listen Recommendations" not in dashboard_content
    assert "1. Old Match - Artist A" not in dashboard_content
