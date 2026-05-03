from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TrackInfo:
    track_id: str
    title: str
    artists: list[str]
    album: str
    tags: list[str]
    year: int | None
    cover_url: str
    duration_seconds: int
    source_position: int
    yandex_url: str

    @property
    def filename(self) -> str:
        return f"{self.title}.md"


@dataclass(frozen=True, slots=True)
class SavedTrackInfo:
    title: str
    artists: list[str]
    tags: list[str]


@dataclass(frozen=True, slots=True)
class ExporterSyncSummary:
    written: int
    archived: int
    restored: int


@dataclass(frozen=True, slots=True)
class SyncSummary:
    fetched: int
    written: int
    archived: int
    restored: int
