export type BackendCommand = "show-config" | "sync" | "list";
export type FilterKind = "tag" | "artist";

export interface ShowConfigData {
  config: {
    yandexMusicTokenPresent: boolean;
    obsidianVaultPath: string;
    logLevel: string;
  };
}

export interface SyncData {
  summary: {
    fetched: number;
    written: number;
    archived: number;
    restored: number;
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

export interface BackendErrorPayload {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

export interface ListTracksRequest {
  kind: FilterKind;
  value: string;
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
  runSync: () => Promise<BackendEnvelope<SyncData>>;
  listTracks: (request: ListTracksRequest) => Promise<BackendEnvelope<ListData>>;
}
