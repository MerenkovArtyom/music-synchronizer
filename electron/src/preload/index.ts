import { contextBridge, ipcRenderer } from "electron";

import type { MusicSyncBridge } from "../shared/bridge.js";
import type {
  DiscoveryRequest,
  ListTracksRequest,
  RecommendationRequest,
  SaveConfigRequest,
  TopListenRequest,
  VaultRequest,
} from "../shared/contracts.js";

const api: MusicSyncBridge = {
  showConfig: async () => {
    return await ipcRenderer.invoke("music-sync:show-config");
  },
  saveConfig: async (request: SaveConfigRequest) => {
    return await ipcRenderer.invoke("music-sync:save-config", request);
  },
  chooseVaultPath: async () => {
    return await ipcRenderer.invoke("music-sync:choose-vault-path");
  },
  runSync: async () => {
    return await ipcRenderer.invoke("music-sync:sync");
  },
  listTracks: async (request: ListTracksRequest) => {
    return await ipcRenderer.invoke("music-sync:list", request);
  },
  getTopListen: async (request: TopListenRequest) => {
    return await ipcRenderer.invoke("music-sync:top-listen", request);
  },
  getDashboard: async () => {
    return await ipcRenderer.invoke("music-sync:dashboard");
  },
  getRecommendations: async (request: RecommendationRequest) => {
    return await ipcRenderer.invoke("music-sync:recommend", request);
  },
  getDiscoveryRecommendations: async (request: DiscoveryRequest) => {
    return await ipcRenderer.invoke("music-sync:discovery", request);
  },
  getVaultView: async (request: VaultRequest) => {
    return await ipcRenderer.invoke("music-sync:vault", request);
  },
};

contextBridge.exposeInMainWorld("musicSync", api);
