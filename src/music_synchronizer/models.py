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
    monthly_listens: int | None = None

    @property
    def filename(self) -> str:
        return f"{self.title}.md"


@dataclass(frozen=True, slots=True)
class SavedTrackInfo:
    track_id: str | None
    title: str
    artists: list[str]
    tags: list[str]
    system_tags: list[str]
    user_tags: list[str]
    duration_seconds: int = 0
    monthly_listens: int | None = None
    source_position: int | None = None


@dataclass(frozen=True, slots=True)
class SyncSummary:
    added: int
    unchanged: int
    removed: int


@dataclass(frozen=True, slots=True)
class MonthlyTopEntry:
    title: str
    artists: list[str]
    monthly_listens: int
    source_position: int


@dataclass(frozen=True, slots=True)
class DashboardStatEntry:
    name: str
    count: int
    monthly_listens: int | None = None


@dataclass(frozen=True, slots=True)
class TrackDashboardEntry:
    title: str
    artists: list[str]
    monthly_listens: int | None
    duration_seconds: int
    duration_text: str


@dataclass(frozen=True, slots=True)
class DashboardData:
    liked_tracks_count: int
    removed_tracks_count: int
    total_tracks_count: int
    total_duration_seconds: int
    total_duration_text: str
    monthly_listens_known_count: int
    monthly_listens_coverage_percent: float
    average_monthly_listens: float | None
    median_monthly_listens: float | None
    most_listened_track: TrackDashboardEntry | None
    most_listened_artist: DashboardStatEntry | None
    most_used_tag: DashboardStatEntry | None
    longest_track: TrackDashboardEntry | None
    top_tags: list[DashboardStatEntry]
    top_artists: list[DashboardStatEntry]
