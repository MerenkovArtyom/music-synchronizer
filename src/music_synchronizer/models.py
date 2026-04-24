from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackInfo:
    track_id: str
    title: str
    artists: list[str]
    album: str
    duration_seconds: int
    source_position: int
    yandex_url: str

    @property
    def filename(self) -> str:
        return f"{self.title}.md"
