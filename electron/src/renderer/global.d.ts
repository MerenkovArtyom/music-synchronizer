import type { MusicSyncBridge } from "../shared/bridge.js";

declare global {
  interface Window {
    musicSync: MusicSyncBridge;
  }
}

export {};
