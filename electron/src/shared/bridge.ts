import type { BackendEnvelope, ConfigData, ListData, ListTracksRequest, SyncData } from "./contracts.js";

export interface MusicSyncBridge {
  showConfig: () => Promise<BackendEnvelope<ConfigData>>;
  runSync: () => Promise<BackendEnvelope<SyncData>>;
  listTracks: (request: ListTracksRequest) => Promise<BackendEnvelope<ListData>>;
}
