import type {
  BackendEnvelope,
  ConfigData,
  DiscoveryData,
  DiscoveryRequest,
  DashboardData,
  ListData,
  ListTracksRequest,
  MonthlyTopData,
  RecommendationData,
  RecommendationRequest,
  SyncData,
  TopListenRequest,
  VaultData,
  VaultRequest,
} from "./contracts.js";

export interface MusicSyncBridge {
  showConfig: () => Promise<BackendEnvelope<ConfigData>>;
  runSync: () => Promise<BackendEnvelope<SyncData>>;
  listTracks: (request: ListTracksRequest) => Promise<BackendEnvelope<ListData>>;
  getTopListen: (request: TopListenRequest) => Promise<BackendEnvelope<MonthlyTopData>>;
  getDashboard: () => Promise<BackendEnvelope<DashboardData>>;
  getRecommendations: (request: RecommendationRequest) => Promise<BackendEnvelope<RecommendationData>>;
  getDiscoveryRecommendations: (request: DiscoveryRequest) => Promise<BackendEnvelope<DiscoveryData>>;
  getVaultView: (request: VaultRequest) => Promise<BackendEnvelope<VaultData>>;
}
