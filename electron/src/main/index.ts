import path from "node:path";

import { app, BrowserWindow, dialog, ipcMain } from "electron";

import type {
  DiscoveryRequest,
  ListTracksRequest,
  RecommendationRequest,
  SaveConfigRequest,
  TopListenRequest,
  VaultRequest,
} from "../shared/contracts.js";
import { runBackendCommand } from "./backend.js";

function runtimeEnv() {
  return {
    ...process.env,
    MUSIC_SYNC_REPO_ROOT: process.env.MUSIC_SYNC_REPO_ROOT ?? path.resolve(__dirname, "../../.."),
    MUSIC_SYNC_CONFIG_PATH: path.join(app.getPath("userData"), "config.env"),
  };
}

function createWindow(): BrowserWindow {
  const window = new BrowserWindow({
    width: 1200,
    height: 860,
    minWidth: 960,
    minHeight: 720,
    backgroundColor: "#040506",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, "../preload/index.cjs"),
    },
  });

  void window.loadFile(path.join(__dirname, "../renderer/index.html"));
  return window;
}

function registerIpcHandlers(): void {
  ipcMain.handle("music-sync:show-config", async () => {
    return await runBackendCommand("show-config", undefined, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:save-config", async (_event, request: SaveConfigRequest) => {
    return await runBackendCommand("save-config", request, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:sync", async () => {
    return await runBackendCommand("sync", undefined, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:list", async (_event, request: ListTracksRequest) => {
    return await runBackendCommand("list", request, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:top-listen", async (_event, request: TopListenRequest) => {
    return await runBackendCommand("top-listen", request, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:dashboard", async () => {
    return await runBackendCommand("dashboard", undefined, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:recommend", async (_event, request: RecommendationRequest) => {
    return await runBackendCommand("recommend", request, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:discovery", async (_event, request: DiscoveryRequest) => {
    return await runBackendCommand("discovery", request, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:vault", async (_event, request: VaultRequest) => {
    return await runBackendCommand("vault", request, runtimeEnv(), {
      isPackaged: app.isPackaged,
      appPath: app.getAppPath(),
    });
  });

  ipcMain.handle("music-sync:choose-vault-path", async () => {
    const window = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0];
    const result = await dialog.showOpenDialog(window, {
      properties: ["openDirectory", "createDirectory"],
    });
    if (result.canceled) {
      return null;
    }
    return result.filePaths[0] ?? null;
  });
}

app.whenReady().then(() => {
  registerIpcHandlers();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
