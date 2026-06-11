export type BackendCommand = "show-config" | "save-config" | "sync" | "list" | "top-listen" | "dashboard" | "recommend" | "discovery" | "vault";
export type FilterKind = "tag" | "artist";
export type TopListenMode = "most" | "least";

export interface ConfigValues {
  yandexMusicToken: string;
  yandexMusicTokenPresent: boolean;
  obsidianVaultPath: string;
  discoveryPlaylistName: string;
  logLevel: string;
}

export interface ShowConfigData {
  config: ConfigValues;
}

export interface SaveConfigRequest {
  yandexMusicToken: string;
  obsidianVaultPath: string;
  discoveryPlaylistName: string;
  logLevel: string;
}

export interface SaveConfigData {
  config: ConfigValues;
}

export interface SyncData {
  summary: {
    added: number;
    unchanged: number;
    archived: number;
    removed: number;
  };
}

export interface ListData {
  filter: {
    kind: FilterKind;
    value: string;
  };
  tracks: Array<{
    title: string;
    artists: string[];
  }>;
}

export interface MonthlyTopData {
  mostPlayed: Array<{
    title: string;
    artists: string[];
    monthlyListens: number;
    position: number;
  }>;
  leastPlayed: Array<{
    title: string;
    artists: string[];
    monthlyListens: number;
    position: number;
  }>;
}

export interface DashboardData {
  path: string;
  summary: {
    likedTracks: number;
    removedTracks: number;
    totalTracks: number;
    totalDuration: string;
    monthlyListensKnown: number;
    monthlyListensCoveragePercent: number;
    averageMonthlyListens: number | null;
    medianMonthlyListens: number | null;
    mostListenedTrack: {
      title: string;
      artists: string[];
      monthlyListens: number;
    } | null;
    mostListenedArtist: {
      name: string;
      monthlyListens: number;
      tracks: number;
    } | null;
    mostUsedTag: {
      name: string;
      tracks: number;
    } | null;
    longestTrack: {
      title: string;
      artists: string[];
      duration: string;
    } | null;
  };
  topTags: Array<{
    name: string;
    tracks: number;
  }>;
  topArtists: Array<{
    name: string;
    monthlyListens: number;
    tracks: number;
  }>;
}

export interface RecommendationRequest {
  archived: boolean;
}

export interface DiscoveryRequest {
  clear: boolean;
}

export interface RecommendationData {
  includeArchived: boolean;
  recommendations: Array<{
    title: string;
    artists: string[];
    monthlyListens: number | null;
    position: number | null;
    archived: boolean;
    matchedArtists: string[];
    matchedGenres: string[];
    matchedUserTags: string[];
    score: number;
    explain: string;
  }>;
}

export interface DiscoveryData {
  summary: {
    added: number;
    skipped: number;
    removedLiked: number;
    cleared: number;
    total: number;
  };
  recommendations: Array<{
    trackId: string;
    title: string;
    artists: string[];
    album: string;
    systemTags: string[];
    year: number | null;
    coverUrl: string;
    durationSeconds: number;
    yandexUrl: string;
    monthlyListens: number | null;
    discoverySources: string[];
    explain: string;
  }>;
}

export interface VaultTreeNode {
  name: string;
  path: string;
  kind: "directory" | "file";
  children: VaultTreeNode[] | null;
}

export interface VaultRequest {
  selectedPath?: string;
}

export interface VaultData {
  vaultPath: string;
  tree: VaultTreeNode[];
  selectedPath: string | null;
  selectedNote: {
    name: string;
    path: string;
    title: string;
    content: string;
  } | null;
}

export interface BackendErrorPayload {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface ListTracksRequest {
  kind: FilterKind;
  value: string;
}

export interface TopListenRequest {
  mode: TopListenMode;
}

export type ConfigData = ShowConfigData;

export type BackendSuccessEnvelope<T> = {
  ok: true;
  command: BackendCommand;
  data: T;
};

export type BackendErrorEnvelope = {
  ok: false;
  command: BackendCommand;
  error: BackendErrorPayload;
};

export type BackendEnvelope<T> = BackendSuccessEnvelope<T> | BackendErrorEnvelope;

export interface RendererApi {
  showConfig: () => Promise<BackendEnvelope<ConfigData>>;
  saveConfig: (request: SaveConfigRequest) => Promise<BackendEnvelope<SaveConfigData>>;
  chooseVaultPath: () => Promise<string | null>;
  runSync: () => Promise<BackendEnvelope<SyncData>>;
  listTracks: (request: ListTracksRequest) => Promise<BackendEnvelope<ListData>>;
  getTopListen: (request: TopListenRequest) => Promise<BackendEnvelope<MonthlyTopData>>;
  getDashboard: () => Promise<BackendEnvelope<DashboardData>>;
  getRecommendations: (request: RecommendationRequest) => Promise<BackendEnvelope<RecommendationData>>;
  getDiscoveryRecommendations: (request: DiscoveryRequest) => Promise<BackendEnvelope<DiscoveryData>>;
  getVaultView: (request: VaultRequest) => Promise<BackendEnvelope<VaultData>>;
}
