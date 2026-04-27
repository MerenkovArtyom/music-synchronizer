from music_synchronizer.models import TrackInfo


def test_track_info_markdown_filename_uses_track_title() -> None:
    track = TrackInfo(
        track_id="123",
        title="Song Name",
        artists=["Artist"],
        album="Album",
        tags=["rock"],
        year=2024,
        cover_url="https://avatars.yandex.net/get-music-content/cover.jpg",
        duration_seconds=180,
        source_position=1,
        yandex_url="https://music.yandex.ru/track/123",
    )

    assert track.filename == "Song Name.md"
