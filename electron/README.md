# Electron Prototype

This workspace contains the desktop shell for the existing Python sync engine. The Electron side stays thin:

- `src/main/` owns window lifecycle and Python subprocess execution
- `src/preload/` exposes a narrow `window.musicSync` bridge
- `src/renderer/` renders the prototype UI and does not get direct Node access

## Commands

```bash
cd electron
npm install
npm run test
npm run build
npm run dev
```

`npm run dev` currently performs a production-style local build and opens Electron. That is enough for the scaffold slice; live reload can come later if the team wants it.

## Backend Discovery

By default, the desktop shell runs the backend with:

```bash
uv run music-sync
```

from the repository root. For local experiments you can override the backend command:

```bash
MUSIC_SYNC_BACKEND_COMMAND='["uv", "run", "music-sync"]' npm run dev
```

The override is parsed as a JSON array of command tokens so the desktop shell can spawn the backend without shell parsing. The renderer never launches subprocesses directly.

## Current IPC Surface

- `showConfig()`
- `runSync()`
- `listTracks({ kind, value })`

All three calls expect the backend JSON contract described in the root `README.md`.

## Packaging Follow-Up

This prototype does not package Python yet. The next packaging decision is whether to:

1. bundle a Python runtime and the app environment inside the desktop distribution, or
2. keep the prototype developer-only and require a local `uv`/Python installation.
