import type {
  BackendEnvelope,
  ConfigData,
  DashboardData,
  ListData,
  ListTracksRequest,
  MonthlyTopData,
  SyncData,
  TopListenRequest,
} from "./contracts.js";

export interface MusicSyncBridge {
  showConfig: () => Promise<BackendEnvelope<ConfigData>>;
  runSync: () => Promise<BackendEnvelope<SyncData>>;
  listTracks: (request: ListTracksRequest) => Promise<BackendEnvelope<ListData>>;
  getTopListen: (request: TopListenRequest) => Promise<BackendEnvelope<MonthlyTopData>>;
  getDashboard: () => Promise<BackendEnvelope<DashboardData>>;
}
