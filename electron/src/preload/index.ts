import { contextBridge, ipcRenderer } from "electron";

import type { MusicSyncBridge } from "../shared/bridge.js";
import type { ListTracksRequest, RecommendationRequest, TopListenRequest } from "../shared/contracts.js";

const api: MusicSyncBridge = {
  showConfig: async () => {
    return await ipcRenderer.invoke("music-sync:show-config");
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
};

contextBridge.exposeInMainWorld("musicSync", api);
