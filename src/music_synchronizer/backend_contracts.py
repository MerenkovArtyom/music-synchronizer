from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter

BackendCommand = Literal[
    "show-config",
    "save-config",
    "sync",
    "dashboard",
    "list",
    "top-listen",
    "recommend",
    "discovery",
    "vault",
]
TopListenMode = Literal["most", "least"]
ListFilterKind = Literal["tag", "artist"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BackendErrorPayload(ContractModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ConfigSummaryData(ContractModel):
    yandexMusicToken: str
    yandexMusicTokenPresent: bool
    obsidianVaultPath: str
    discoveryPlaylistName: str
    logLevel: str


class ShowConfigData(ContractModel):
    config: ConfigSummaryData


class SaveConfigData(ContractModel):
    config: ConfigSummaryData


class SyncSummaryData(ContractModel):
    added: int
    unchanged: int
    archived: int
    removed: int


class SyncData(ContractModel):
    summary: SyncSummaryData


class ListFilterData(ContractModel):
    kind: ListFilterKind
    value: str


class TrackListEntry(ContractModel):
    title: str
    artists: list[str]


class ListData(ContractModel):
    filter: ListFilterData
    tracks: list[TrackListEntry]


class TopListenEntry(ContractModel):
    title: str
    artists: list[str]
    monthlyListens: int
    position: int


class TopListenData(ContractModel):
    mostPlayed: list[TopListenEntry]
    leastPlayed: list[TopListenEntry]


class DashboardTrackData(ContractModel):
    title: str
    artists: list[str]
    monthlyListens: int


class DashboardArtistData(ContractModel):
    name: str
    monthlyListens: int
    tracks: int


class DashboardTagData(ContractModel):
    name: str
    tracks: int


class DashboardLongestTrackData(ContractModel):
    title: str
    artists: list[str]
    duration: str


class DashboardSummaryData(ContractModel):
    likedTracks: int
    removedTracks: int
    totalTracks: int
    totalDuration: str
    monthlyListensKnown: int
    monthlyListensCoveragePercent: float
    averageMonthlyListens: float | None
    medianMonthlyListens: float | None
    mostListenedTrack: DashboardTrackData | None
    mostListenedArtist: DashboardArtistData | None
    mostUsedTag: DashboardTagData | None
    longestTrack: DashboardLongestTrackData | None


class DashboardTopTagData(ContractModel):
    name: str
    tracks: int


class DashboardTopArtistData(ContractModel):
    name: str
    monthlyListens: int
    tracks: int


class DashboardData(ContractModel):
    path: str
    summary: DashboardSummaryData
    topTags: list[DashboardTopTagData]
    topArtists: list[DashboardTopArtistData]


class RecommendationEntry(ContractModel):
    title: str
    artists: list[str]
    monthlyListens: int | None
    position: int | None
    archived: bool
    matchedArtists: list[str]
    matchedGenres: list[str]
    matchedUserTags: list[str]
    score: int
    explain: str


class RecommendationData(ContractModel):
    includeArchived: bool
    recommendations: list[RecommendationEntry]


class DiscoverySummaryData(ContractModel):
    added: int
    skipped: int
    removedLiked: int
    cleared: int
    total: int


class DiscoveryRecommendationEntry(ContractModel):
    trackId: str
    title: str
    artists: list[str]
    album: str
    systemTags: list[str]
    year: int | None
    coverUrl: str
    durationSeconds: int
    yandexUrl: str
    monthlyListens: int | None
    discoverySources: list[str]
    explain: str


class DiscoveryData(ContractModel):
    summary: DiscoverySummaryData
    recommendations: list[DiscoveryRecommendationEntry]


class VaultTreeNodeData(ContractModel):
    name: str
    path: str
    kind: Literal["directory", "file"]
    children: list["VaultTreeNodeData"] | None


class VaultNoteData(ContractModel):
    name: str
    path: str
    title: str
    content: str


class VaultData(ContractModel):
    vaultPath: str
    tree: list[VaultTreeNodeData]
    selectedPath: str | None
    selectedNote: VaultNoteData | None


class ShowConfigSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["show-config"]
    data: ShowConfigData


class ShowConfigErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["show-config"]
    error: BackendErrorPayload


class SaveConfigSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["save-config"]
    data: SaveConfigData


class SaveConfigErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["save-config"]
    error: BackendErrorPayload


class SyncSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["sync"]
    data: SyncData


class SyncErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["sync"]
    error: BackendErrorPayload


class DashboardSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["dashboard"]
    data: DashboardData


class DashboardErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["dashboard"]
    error: BackendErrorPayload


class ListSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["list"]
    data: ListData


class ListErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["list"]
    error: BackendErrorPayload


class TopListenSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["top-listen"]
    data: TopListenData


class TopListenErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["top-listen"]
    error: BackendErrorPayload


class RecommendationSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["recommend"]
    data: RecommendationData


class RecommendationErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["recommend"]
    error: BackendErrorPayload


class DiscoverySuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["discovery"]
    data: DiscoveryData


class DiscoveryErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["discovery"]
    error: BackendErrorPayload


class VaultSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: Literal["vault"]
    data: VaultData


class VaultErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: Literal["vault"]
    error: BackendErrorPayload


class SharedSuccessEnvelope(ContractModel):
    ok: Literal[True]
    command: BackendCommand
    data: dict[str, Any]


class SharedErrorEnvelope(ContractModel):
    ok: Literal[False]
    command: BackendCommand
    error: BackendErrorPayload


COMMAND_SUCCESS_MODELS: dict[BackendCommand, type[ContractModel]] = {
    "show-config": ShowConfigSuccessEnvelope,
    "save-config": SaveConfigSuccessEnvelope,
    "sync": SyncSuccessEnvelope,
    "dashboard": DashboardSuccessEnvelope,
    "list": ListSuccessEnvelope,
    "top-listen": TopListenSuccessEnvelope,
    "recommend": RecommendationSuccessEnvelope,
    "discovery": DiscoverySuccessEnvelope,
    "vault": VaultSuccessEnvelope,
}

COMMAND_ERROR_MODELS: dict[BackendCommand, type[ContractModel]] = {
    "show-config": ShowConfigErrorEnvelope,
    "save-config": SaveConfigErrorEnvelope,
    "sync": SyncErrorEnvelope,
    "dashboard": DashboardErrorEnvelope,
    "list": ListErrorEnvelope,
    "top-listen": TopListenErrorEnvelope,
    "recommend": RecommendationErrorEnvelope,
    "discovery": DiscoveryErrorEnvelope,
    "vault": VaultErrorEnvelope,
}

COMMAND_ENVELOPE_ADAPTERS: dict[BackendCommand, TypeAdapter[Any]] = {
    command: TypeAdapter(success_model | COMMAND_ERROR_MODELS[command])
    for command, success_model in COMMAND_SUCCESS_MODELS.items()
}


def build_success_envelope(command: BackendCommand, data: dict[str, Any]) -> dict[str, Any]:
    return COMMAND_SUCCESS_MODELS[command](ok=True, command=command, data=data).model_dump(mode="json")


def build_error_envelope(
    command: BackendCommand,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return COMMAND_ERROR_MODELS[command](
        ok=False,
        command=command,
        error=BackendErrorPayload(code=code, message=message, details=details or {}),
    ).model_dump(mode="json")


def validate_backend_envelope(command: BackendCommand, payload: dict[str, Any]) -> dict[str, Any]:
    validated = COMMAND_ENVELOPE_ADAPTERS[command].validate_python(payload)
    return validated.model_dump(mode="json")


def generated_backend_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {
        "backend-error.schema.json": BackendErrorPayload.model_json_schema(),
        "backend-error-envelope.schema.json": SharedErrorEnvelope.model_json_schema(),
        "backend-success-envelope.schema.json": SharedSuccessEnvelope.model_json_schema(),
    }

    for command, adapter in COMMAND_ENVELOPE_ADAPTERS.items():
        schemas[f"{command}.schema.json"] = adapter.json_schema()

    return schemas
