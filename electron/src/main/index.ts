import path from "node:path";

import { app, BrowserWindow, ipcMain } from "electron";

import type { ListTracksRequest } from "../shared/contracts.js";
import { runBackendCommand } from "./backend.js";

const runtimeEnv = {
  ...process.env,
  MUSIC_SYNC_REPO_ROOT: process.env.MUSIC_SYNC_REPO_ROOT ?? path.resolve(__dirname, "../../.."),
};

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
    return await runBackendCommand("show-config", undefined, runtimeEnv);
  });

  ipcMain.handle("music-sync:sync", async () => {
    return await runBackendCommand("sync", undefined, runtimeEnv);
  });

  ipcMain.handle("music-sync:list", async (_event, request: ListTracksRequest) => {
    return await runBackendCommand("list", request, runtimeEnv);
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
