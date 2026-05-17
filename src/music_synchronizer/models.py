from dataclasses import dataclass, field


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
class DiscoveryTrackInfo:
    track_id: str
    title: str
    artists: list[str]
    album: str
    system_tags: list[str]
    year: int | None
    cover_url: str
    duration_seconds: int
    yandex_url: str
    album_id: str | None = None
    monthly_listens: int | None = None
    discovery_sources: list[str] = field(default_factory=list)

    @property
    def explain(self) -> str:
        return ", ".join(self.discovery_sources)


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
class DiscoverySummary:
    added: int
    skipped: int
    removed_liked: int
    cleared: int
    total: int


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
class RelistenRecommendationEntry:
    title: str
    artists: list[str]
    monthly_listens: int | None
    position: int | None
    archived: bool
    matched_artists: list[str]
    matched_genres: list[str]
    matched_user_tags: list[str]
    score: int

    @property
    def explain(self) -> str:
        parts: list[str] = []
        if self.matched_artists:
            parts.append(f"artists={', '.join(self.matched_artists)}")
        if self.matched_genres:
            parts.append(f"genres={', '.join(self.matched_genres)}")
        if self.matched_user_tags:
            parts.append(f"user_tags={', '.join(self.matched_user_tags)}")
        return "; ".join(parts)


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
    discovery_recommendations: list[DiscoveryTrackInfo] = field(default_factory=list)
    relisten_recommendations: list[RelistenRecommendationEntry] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VaultTreeNode:
    name: str
    path: str
    kind: str
    children: list["VaultTreeNode"] | None = None


@dataclass(frozen=True, slots=True)
class VaultNote:
    name: str
    path: str
    title: str
    content: str


@dataclass(frozen=True, slots=True)
class VaultData:
    vault_path: str
    tree: list[VaultTreeNode]
    selected_path: str | None = None
    selected_note: VaultNote | None = None
