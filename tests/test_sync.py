from datetime import datetime, timezone

import pytest

from music_synchronizer.config import Settings
from music_synchronizer.models import (
    DashboardData,
    DashboardStatEntry,
    DiscoverySummary,
    DiscoveryTrackInfo,
    SavedTrackInfo,
    SyncSummary,
    TrackDashboardEntry,
)
from music_synchronizer.models import TrackInfo
from music_synchronizer.sync import MONTHLY_TOP_LIMIT, SyncService


def _track(
    track_id: str,
    title: str,
    monthly_listens: int,
    source_position: int,
) -> TrackInfo:
    return TrackInfo(
        track_id=track_id,
        title=title,
        artists=[f"Artist {track_id}"],
        album="Album",
        tags=[],
        year=2024,
        cover_url="",
        duration_seconds=180,
        source_position=source_position,
        yandex_url=f"https://music.yandex.ru/track/{track_id}",
        monthly_listens=monthly_listens,
    )


def _discovery_track(
    track_id: str,
    title: str,
    *,
    source: str,
    monthly_listens: int | None = None,
    album_id: str | None = None,
    artists: list[str] | None = None,
) -> DiscoveryTrackInfo:
    yandex_url = f"https://music.yandex.ru/track/{track_id}"
    if album_id is not None:
        yandex_url = f"https://music.yandex.ru/album/{album_id}/track/{track_id}"

    return DiscoveryTrackInfo(
        track_id=track_id,
        title=title,
        artists=artists or [f"Artist {track_id}"],
        album="Album",
        album_id=album_id,
        system_tags=["indie"],
        year=2024,
        cover_url="",
        duration_seconds=180,
        yandex_url=yandex_url,
        monthly_listens=monthly_listens,
        discovery_sources=[source],
    )


def test_monthly_top_report_sorts_by_monthly_listens_and_like_order(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    tracks = [
        _track("1", "Late Song", monthly_listens=4, source_position=3),
        _track("2", "First Song", monthly_listens=7, source_position=1),
        _track("3", "Second Song", monthly_listens=7, source_position=2),
        _track("4", "Quiet Song", monthly_listens=1, source_position=4),
        _track("5", "Zero Song", monthly_listens=0, source_position=5),
    ]

    monkeypatch.setattr(
        service.exporter,
        "top_listen_tracks",
        lambda: tracks,
    )
    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: (_ for _ in ()).throw(AssertionError("Yandex client must not be used")),
    )

    most_played = service.top_listen_entries(most=True)
    least_played = service.top_listen_entries(most=False)

    assert [entry.title for entry in most_played] == [
        "First Song",
        "Second Song",
        "Late Song",
        "Quiet Song",
        "Zero Song",
    ]
    assert [entry.title for entry in least_played] == [
        "Zero Song",
        "Quiet Song",
        "Late Song",
        "First Song",
        "Second Song",
    ]


def test_monthly_top_report_limits_each_list_to_top_ten(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    tracks = [
        _track(str(index), f"Song {index}", monthly_listens=20 - index, source_position=index)
        for index in range(1, 14)
    ]

    monkeypatch.setattr(
        service.exporter,
        "top_listen_tracks",
        lambda: tracks,
    )

    most_played = service.top_listen_entries(most=True)
    least_played = service.top_listen_entries(most=False)

    assert len(most_played) == MONTHLY_TOP_LIMIT
    assert len(least_played) == MONTHLY_TOP_LIMIT
    assert [entry.title for entry in most_played] == [f"Song {index}" for index in range(1, 11)]
    assert [entry.title for entry in least_played] == [f"Song {index}" for index in range(13, 3, -1)]


def test_monthly_top_report_sends_missing_positions_to_end_of_ties(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    tracks = [
        _track("1", "Known Position", monthly_listens=5, source_position=2),
        _track("2", "Missing Position", monthly_listens=5, source_position=None),
        _track("3", "Earlier Position", monthly_listens=5, source_position=1),
    ]

    monkeypatch.setattr(
        service.exporter,
        "top_listen_tracks",
        lambda: tracks,
    )

    most_played = service.top_listen_entries(most=True)

    assert [entry.title for entry in most_played] == [
        "Earlier Position",
        "Known Position",
        "Missing Position",
    ]


def test_dashboard_data_uses_only_local_exporter_data(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    dashboard = DashboardData(
        liked_tracks_count=2,
        removed_tracks_count=1,
        total_tracks_count=3,
        total_duration_seconds=360,
        total_duration_text="6:00",
        monthly_listens_known_count=2,
        monthly_listens_coverage_percent=100.0,
        average_monthly_listens=5.0,
        median_monthly_listens=5.0,
        most_listened_track=TrackDashboardEntry(
            title="First Song",
            artists=["Artist 1"],
            monthly_listens=7,
            duration_seconds=180,
            duration_text="3:00",
        ),
        most_listened_artist=DashboardStatEntry(
            name="Artist 1",
            count=1,
            monthly_listens=7,
        ),
        most_used_tag=DashboardStatEntry(name="indie", count=2),
        longest_track=TrackDashboardEntry(
            title="Long Song",
            artists=["Artist 2"],
            monthly_listens=3,
            duration_seconds=240,
            duration_text="4:00",
        ),
        top_tags=[DashboardStatEntry(name="indie", count=2)],
        top_artists=[DashboardStatEntry(name="Artist 1", count=1, monthly_listens=7)],
    )

    monkeypatch.setattr(service.exporter, "dashboard_data", lambda: dashboard)
    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: (_ for _ in ()).throw(AssertionError("Yandex client must not be used")),
    )

    result = service.dashboard_data()

    assert result == dashboard


def test_refresh_dashboard_delegates_to_exporter_without_api(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    refreshed = DashboardData(
        liked_tracks_count=0,
        removed_tracks_count=0,
        total_tracks_count=0,
        total_duration_seconds=0,
        total_duration_text="0:00",
        monthly_listens_known_count=0,
        monthly_listens_coverage_percent=0.0,
        average_monthly_listens=None,
        median_monthly_listens=None,
        most_listened_track=None,
        most_listened_artist=None,
        most_used_tag=None,
        longest_track=None,
        top_tags=[],
        top_artists=[],
    )

    monkeypatch.setattr(service.exporter, "refresh_dashboard", lambda: refreshed)
    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: (_ for _ in ()).throw(AssertionError("Yandex client must not be used")),
    )

    result = service.refresh_dashboard()

    assert result == refreshed


def test_relisten_recommendations_rank_old_matching_tracks_without_api(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    tracks = [
        SavedTrackInfo(
            track_id="1",
            title="Recent Favorite",
            artists=["Artist A"],
            tags=["indie", "night"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=9,
            source_position=1,
        ),
        SavedTrackInfo(
            track_id="2",
            title="Another Recent Favorite",
            artists=["Artist B"],
            tags=["ambient", "focus"],
            system_tags=["ambient"],
            user_tags=["focus"],
            monthly_listens=7,
            source_position=2,
        ),
        SavedTrackInfo(
            track_id="3",
            title="Old Match",
            artists=["Artist A"],
            tags=["indie", "night"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=0,
            source_position=4,
        ),
        SavedTrackInfo(
            track_id="4",
            title="Tag Match",
            artists=["Artist C"],
            tags=["ambient", "focus"],
            system_tags=["ambient"],
            user_tags=["focus"],
            monthly_listens=None,
            source_position=5,
        ),
        SavedTrackInfo(
            track_id="5",
            title="No Signal",
            artists=["Artist Z"],
            tags=["metal"],
            system_tags=["metal"],
            user_tags=[],
            monthly_listens=None,
            source_position=6,
        ),
    ]

    monkeypatch.setattr(
        service.exporter,
        "recommendation_tracks",
        lambda *, include_archived: tracks,
    )
    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: (_ for _ in ()).throw(AssertionError("Yandex client must not be used")),
    )

    recommendations = service.relisten_recommendations(include_archived=False)

    assert [entry.title for entry in recommendations] == ["Old Match", "Tag Match"]
    assert recommendations[0].matched_artists == ["Artist A"]
    assert recommendations[0].matched_genres == ["indie"]
    assert recommendations[0].matched_user_tags == ["night"]
    assert recommendations[0].archived is False
    assert recommendations[1].matched_artists == []
    assert recommendations[1].matched_genres == ["ambient"]
    assert recommendations[1].matched_user_tags == ["focus"]


def test_relisten_recommendations_pass_archived_flag_to_exporter(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    captured_flags: list[bool] = []

    def fake_recommendation_tracks(*, include_archived: bool) -> list[SavedTrackInfo]:
        captured_flags.append(include_archived)
        return []

    monkeypatch.setattr(service.exporter, "recommendation_tracks", fake_recommendation_tracks)

    recommendations = service.relisten_recommendations(include_archived=True)

    assert recommendations == []
    assert captured_flags == [True]


def test_relisten_recommendations_limit_primary_artist_to_two_entries(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    tracks = [
        SavedTrackInfo(
            track_id="1",
            title="Recent Artist A",
            artists=["Artist A"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=8,
            source_position=1,
        ),
        SavedTrackInfo(
            track_id="2",
            title="Recent Artist B",
            artists=["Artist B"],
            tags=["ambient"],
            system_tags=["ambient"],
            user_tags=["focus"],
            monthly_listens=7,
            source_position=2,
        ),
        SavedTrackInfo(
            track_id="3",
            title="Old Artist A One",
            artists=["Artist A"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=0,
            source_position=3,
        ),
        SavedTrackInfo(
            track_id="4",
            title="Old Artist A Two",
            artists=["Artist A"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=0,
            source_position=4,
        ),
        SavedTrackInfo(
            track_id="5",
            title="Old Artist A Three",
            artists=["Artist A"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=0,
            source_position=5,
        ),
        SavedTrackInfo(
            track_id="6",
            title="Old Artist B",
            artists=["Artist B"],
            tags=["ambient"],
            system_tags=["ambient"],
            user_tags=["focus"],
            monthly_listens=0,
            source_position=6,
        ),
    ]

    monkeypatch.setattr(service.exporter, "recommendation_tracks", lambda *, include_archived: tracks)

    recommendations = service.relisten_recommendations(include_archived=False)

    artist_a_titles = [entry.title for entry in recommendations if entry.artists and entry.artists[0] == "Artist A"]
    assert artist_a_titles == ["Old Artist A One", "Old Artist A Two"]
    assert "Old Artist A Three" not in [entry.title for entry in recommendations]


def test_relisten_recommendations_prefer_cleaner_collabs_on_ties(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    tracks = [
        SavedTrackInfo(
            track_id="1",
            title="Recent Artist A",
            artists=["Artist A", "Profile Guest A"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=9,
            source_position=1,
        ),
        SavedTrackInfo(
            track_id="2",
            title="Recent Artist B",
            artists=["Artist B", "Profile Guest B"],
            tags=["ambient"],
            system_tags=["ambient"],
            user_tags=["focus"],
            monthly_listens=8,
            source_position=2,
        ),
        SavedTrackInfo(
            track_id="3",
            title="Lead Candidate",
            artists=["Artist C", "Shared Guest"],
            tags=["indie", "ambient"],
            system_tags=["indie", "ambient"],
            user_tags=["night", "focus"],
            monthly_listens=0,
            source_position=3,
        ),
        SavedTrackInfo(
            track_id="4",
            title="Clean Candidate",
            artists=["Artist D", "Fresh Guest"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=0,
            source_position=4,
        ),
        SavedTrackInfo(
            track_id="5",
            title="Overlap Candidate",
            artists=["Artist E", "Shared Guest"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=0,
            source_position=5,
        ),
    ]

    monkeypatch.setattr(service.exporter, "recommendation_tracks", lambda *, include_archived: tracks)

    recommendations = service.relisten_recommendations(include_archived=False)

    assert [entry.title for entry in recommendations] == ["Lead Candidate", "Clean Candidate", "Overlap Candidate"]


def test_relisten_recommendations_balance_similarity_and_staleness(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    tracks = [
        SavedTrackInfo(
            track_id="1",
            title="Recent Favorite",
            artists=["Artist A"],
            tags=["indie"],
            system_tags=["indie"],
            user_tags=["night"],
            monthly_listens=9,
            source_position=1,
        ),
        SavedTrackInfo(
            track_id="2",
            title="Second Favorite",
            artists=["Artist B"],
            tags=["ambient"],
            system_tags=["ambient"],
            user_tags=["focus"],
            monthly_listens=8,
            source_position=2,
        ),
        SavedTrackInfo(
            track_id="3",
            title="Artist Match Only",
            artists=["Artist A"],
            tags=["metal"],
            system_tags=["metal"],
            user_tags=[],
            monthly_listens=None,
            source_position=3,
        ),
        SavedTrackInfo(
            track_id="4",
            title="Stale Tag Match",
            artists=["Artist C"],
            tags=["ambient"],
            system_tags=["ambient"],
            user_tags=["focus"],
            monthly_listens=None,
            source_position=4,
        ),
    ]

    monkeypatch.setattr(service.exporter, "recommendation_tracks", lambda *, include_archived: tracks)

    recommendations = service.relisten_recommendations(include_archived=False)

    assert [entry.title for entry in recommendations] == ["Stale Tag Match", "Artist Match Only"]


def test_discovery_recommendations_mix_sources_and_save_results(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    liked_tracks = [
        _track("1", "Liked One", monthly_listens=7, source_position=1),
        _track("2", "Liked Two", monthly_listens=5, source_position=2),
    ]
    saved_payload: dict[str, object] = {}
    playlist_calls: list[tuple[str, list[DiscoveryTrackInfo]]] = []

    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: liked_tracks,
    )
    monkeypatch.setattr(
        service.client,
        "fetch_recent_liked_track_ids",
        lambda *, liked_track_ids, reference_time, limit: ["1", "2"],
    )
    monkeypatch.setattr(
        service.client,
        "fetch_popular_tracks_for_artist_seeds",
        lambda seed_track_ids, exclude_track_ids: [
            _discovery_track("10", "Popular One", source="artist-popular", album_id="100"),
            _discovery_track("11", "Popular Two", source="artist-popular", album_id="110"),
            _discovery_track("12", "Popular Three", source="artist-popular", album_id="120"),
        ],
    )
    monkeypatch.setattr(
        service.client,
        "fetch_similar_tracks",
        lambda seed_track_ids, exclude_track_ids: [
            _discovery_track("20", "Similar One", source="similar", album_id="200"),
            _discovery_track("11", "Popular Two", source="similar", album_id="110"),
            _discovery_track("21", "Similar Two", source="similar", album_id="210"),
        ],
    )
    monkeypatch.setattr(service.exporter, "read_discovery_tracks", lambda: [_discovery_track("30", "Existing", source="similar")])

    def fake_save(tracks: list[DiscoveryTrackInfo]) -> DiscoverySummary:
        saved_payload["tracks"] = tracks
        return DiscoverySummary(added=5, skipped=0, removed_liked=0, cleared=0, total=6)

    monkeypatch.setattr(service.exporter, "save_discovery_tracks", fake_save)
    monkeypatch.setattr(
        service.client,
        "sync_discovery_playlist",
        lambda playlist_name, tracks: playlist_calls.append((playlist_name, tracks)),
    )

    recommendations, summary = service.discovery_recommendations()

    assert [track.track_id for track in recommendations] == ["10", "20", "11", "21", "12"]
    assert recommendations[2].discovery_sources == ["artist-popular", "similar"]
    assert saved_payload["tracks"] == recommendations
    assert [playlist_name for playlist_name, _ in playlist_calls] == [service.settings.discovery_playlist_name]
    assert [[track.track_id for track in tracks] for _, tracks in playlist_calls] == [["10", "20", "11", "21", "12", "30"]]
    assert summary == DiscoverySummary(added=5, skipped=0, removed_liked=0, cleared=0, total=6)


def test_discovery_recommendations_backfill_from_other_source(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    liked_tracks = [_track("1", "Liked One", monthly_listens=7, source_position=1)]
    playlist_calls: list[tuple[str, list[DiscoveryTrackInfo]]] = []

    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: liked_tracks,
    )
    monkeypatch.setattr(
        service.client,
        "fetch_recent_liked_track_ids",
        lambda *, liked_track_ids, reference_time, limit: ["1"],
    )
    monkeypatch.setattr(
        service.client,
        "fetch_popular_tracks_for_artist_seeds",
        lambda seed_track_ids, exclude_track_ids: [_discovery_track("10", "Popular One", source="artist-popular", album_id="100")],
    )
    monkeypatch.setattr(
        service.client,
        "fetch_similar_tracks",
        lambda seed_track_ids, exclude_track_ids: [
            _discovery_track("20", "Similar One", source="similar", album_id="200"),
            _discovery_track("21", "Similar Two", source="similar", album_id="210"),
            _discovery_track("22", "Similar Three", source="similar", album_id="220"),
        ],
    )
    monkeypatch.setattr(service.exporter, "read_discovery_tracks", lambda: [])
    monkeypatch.setattr(
        service.exporter,
        "save_discovery_tracks",
        lambda tracks: DiscoverySummary(added=len(tracks), skipped=0, removed_liked=0, cleared=0, total=len(tracks)),
    )
    monkeypatch.setattr(
        service.client,
        "sync_discovery_playlist",
        lambda playlist_name, tracks: playlist_calls.append((playlist_name, tracks)),
    )

    recommendations, summary = service.discovery_recommendations()

    assert [track.track_id for track in recommendations] == ["10", "20", "21", "22"]
    assert [playlist_name for playlist_name, _ in playlist_calls] == [service.settings.discovery_playlist_name]
    assert [[track.track_id for track in tracks] for _, tracks in playlist_calls] == [["10", "20", "21", "22"]]
    assert summary.total == 4


def test_discovery_recommendations_backfills_playlist_from_existing_notes(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    liked_tracks = [_track("1", "Liked One", monthly_listens=7, source_position=1)]
    existing_tracks = [_discovery_track("30", "Existing", source="similar", album_id="300")]
    playlist_calls: list[tuple[str, list[DiscoveryTrackInfo]]] = []

    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: liked_tracks,
    )
    monkeypatch.setattr(
        service.client,
        "fetch_recent_liked_track_ids",
        lambda *, liked_track_ids, reference_time, limit: ["1"],
    )
    monkeypatch.setattr(
        service.client,
        "fetch_popular_tracks_for_artist_seeds",
        lambda seed_track_ids, exclude_track_ids: [_discovery_track("10", "Popular One", source="artist-popular", album_id="100")],
    )
    monkeypatch.setattr(
        service.client,
        "fetch_similar_tracks",
        lambda seed_track_ids, exclude_track_ids: [],
    )
    monkeypatch.setattr(service.exporter, "read_discovery_tracks", lambda: existing_tracks)
    monkeypatch.setattr(
        service.exporter,
        "save_discovery_tracks",
        lambda tracks: DiscoverySummary(added=len(tracks), skipped=0, removed_liked=0, cleared=0, total=len(tracks) + len(existing_tracks)),
    )
    monkeypatch.setattr(
        service.client,
        "sync_discovery_playlist",
        lambda playlist_name, tracks: playlist_calls.append((playlist_name, tracks)),
    )

    recommendations, summary = service.discovery_recommendations()

    assert [track.track_id for track in recommendations] == ["10"]
    assert [playlist_name for playlist_name, _ in playlist_calls] == [service.settings.discovery_playlist_name]
    assert [[track.track_id for track in tracks] for _, tracks in playlist_calls] == [["10", "30"]]
    assert [[track.album_id for track in tracks] for _, tracks in playlist_calls] == [["100", "300"]]
    assert summary.total == 2


def test_sync_leaves_discovery_recommendations_untouched(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    synced_at = datetime.now(timezone.utc)
    liked_tracks = [_track("1", "Liked One", monthly_listens=7, source_position=1)]

    monkeypatch.setattr(
        service.client,
        "fetch_liked_tracks",
        lambda *, reference_time: liked_tracks,
    )
    monkeypatch.setattr(
        service.exporter,
        "sync",
        lambda tracks, synced_at: SyncSummary(added=1, unchanged=0, removed=0),
    )
    monkeypatch.setattr(
        service.exporter,
        "remove_discovery_tracks_by_ids",
        lambda track_ids: pytest.fail("sync must not remove discovery recommendation notes"),
    )
    monkeypatch.setattr(
        service.client,
        "remove_tracks_from_playlist",
        lambda playlist_name, track_ids: pytest.fail("sync must not remove discovery playlist tracks"),
    )

    summary = service.run()

    assert summary == SyncSummary(added=1, unchanged=0, removed=0)


def test_clear_discovery_recommendations_delegates_to_exporter(monkeypatch) -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    cleared_playlists: list[str] = []
    monkeypatch.setattr(
        service.exporter,
        "clear_discovery_tracks",
        lambda: DiscoverySummary(added=0, skipped=0, removed_liked=0, cleared=3, total=0),
    )
    monkeypatch.setattr(
        service.client,
        "clear_playlist",
        lambda playlist_name: cleared_playlists.append(playlist_name),
    )

    summary = service.clear_discovery_recommendations()

    assert summary == DiscoverySummary(added=0, skipped=0, removed_liked=0, cleared=3, total=0)
    assert cleared_playlists == [service.settings.discovery_playlist_name]


def test_discovery_recommendations_limit_primary_artist_to_two_entries_per_artist() -> None:
    service = SyncService(Settings.model_construct(yandex_music_token="token"))
    popular_candidates = [
        _discovery_track("10", "Eminem Popular 1", source="artist-popular", artists=["Eminem"]),
        _discovery_track("11", "Eminem Popular 2", source="artist-popular", artists=["Eminem"]),
        _discovery_track("12", "Eminem Popular 3", source="artist-popular", artists=["Eminem"]),
        _discovery_track("13", "Other Popular", source="artist-popular", artists=["Nas"]),
    ]
    similar_candidates = [
        _discovery_track("20", "Eminem Similar 1", source="similar", artists=["Eminem"]),
        _discovery_track("21", "Eminem Similar 2", source="similar", artists=["Eminem"]),
        _discovery_track("22", "Other Similar", source="similar", artists=["Jay-Z"]),
    ]

    recommendations = service._mix_discovery_candidates(popular_candidates, similar_candidates)

    assert sum(1 for track in recommendations if track.artists and track.artists[0] == "Eminem") == 2
