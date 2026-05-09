from datetime import datetime, timezone

from music_synchronizer.config import Settings
from music_synchronizer.models import DashboardData, DashboardStatEntry, TrackDashboardEntry
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
