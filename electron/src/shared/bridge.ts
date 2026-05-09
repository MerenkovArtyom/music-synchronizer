import type {
  BackendEnvelope,
  ConfigData,
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
}
