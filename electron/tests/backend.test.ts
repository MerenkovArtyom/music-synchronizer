import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

import type { BackendEnvelope, ConfigData, TopListenRequest } from "../src/shared/contracts.js";
import {
  BackendRunnerError,
  buildBackendInvocation,
  normalizeBackendEnvelope,
  parseBackendCommandEnv,
  resolveBackendCommand,
  resolveBackendRuntime,
} from "../src/main/backend.js";

test("parseBackendCommandEnv accepts a JSON string array", () => {
  assert.deepEqual(parseBackendCommandEnv('["python", "-m", "music_synchronizer.backend_cli"]'), [
    "python",
    "-m",
    "music_synchronizer.backend_cli",
  ]);
});

test("parseBackendCommandEnv rejects a non-array JSON value", () => {
  assert.throws(() => parseBackendCommandEnv('"uv run music-sync-app"'), /JSON array/);
});

test("resolveBackendCommand falls back to uv run music-sync-app", () => {
  assert.deepEqual(resolveBackendCommand({}), ["uv", "run", "music-sync-app"]);
});

test("buildBackendInvocation appends backend command arguments", () => {
  const invocation = buildBackendInvocation("list", ["--artist", "Artist Guest"], {
    MUSIC_SYNC_BACKEND_COMMAND: '["python", "-m", "music_synchronizer.backend_cli"]',
    MUSIC_SYNC_REPO_ROOT: "/tmp/music-sync",
  });

  assert.equal(invocation.command, "python");
  assert.deepEqual(invocation.args, [
    "-m",
    "music_synchronizer.backend_cli",
    "list",
    "--artist",
    "Artist Guest",
  ]);
  assert.equal(invocation.cwd, "/tmp/music-sync");
});

test("resolveBackendRuntime prefers development repo root", () => {
  const runtime = resolveBackendRuntime({
    MUSIC_SYNC_REPO_ROOT: "/tmp/music-sync",
  }, false, "/Applications/Music Sync.app/Contents/Resources/app.asar");

  assert.deepEqual(runtime, {
    cwd: "/tmp/music-sync",
    command: ["uv", "run", "music-sync-app"],
  });
});

test("resolveBackendRuntime uses packaged backend command in production", () => {
  const resourcesPath = "/Applications/Music Sync.app/Contents/Resources";
  const runtime = resolveBackendRuntime({}, true, path.join(resourcesPath, "app.asar"));

  assert.equal(runtime.cwd, path.join(resourcesPath, "backend"));
  assert.deepEqual(runtime.command, [path.join(resourcesPath, "backend", "music-sync-app")]);
});

test("normalizeBackendEnvelope accepts a machine-readable success envelope", () => {
  const envelope = normalizeBackendEnvelope("show-config", {
    stdout: JSON.stringify({
      ok: true,
      command: "show-config",
      data: {
        config: {
          yandexMusicTokenPresent: true,
          obsidianVaultPath: "/tmp/vault",
          logLevel: "INFO",
        },
      },
    }),
    stderr: "",
    exitCode: 0,
  }) as BackendEnvelope<ConfigData>;

  assert.equal(envelope.ok, true);
  if (!envelope.ok) {
    throw new Error("expected success envelope");
  }

  assert.equal(envelope.data.config.obsidianVaultPath, "/tmp/vault");
  assert.equal(envelope.data.config.yandexMusicTokenPresent, true);
});

test("normalizeBackendEnvelope accepts a machine-readable top-listen envelope", () => {
  const envelope = normalizeBackendEnvelope("top-listen", {
    stdout: JSON.stringify({
      ok: true,
      command: "top-listen",
      data: {
        mostPlayed: [
          {
            title: "Loud Song",
            artists: ["Artist", "Guest"],
            monthlyListens: 9,
            position: 2,
          },
        ],
        leastPlayed: [],
      },
    }),
    stderr: "",
    exitCode: 0,
  }, {
    mode: "most",
  } as TopListenRequest);

  assert.equal(envelope.ok, true);
  if (!envelope.ok) {
    throw new Error("expected success envelope");
  }

  assert.deepEqual(envelope.data, {
    mostPlayed: [
      {
        title: "Loud Song",
        artists: ["Artist", "Guest"],
        monthlyListens: 9,
        position: 2,
      },
    ],
    leastPlayed: [],
  });
});

test("normalizeBackendEnvelope surfaces backend error envelopes", () => {
  const envelope = normalizeBackendEnvelope("sync", {
    stdout: JSON.stringify({
      ok: false,
      command: "sync",
      error: {
        code: "SYNC_FAILED",
        message: "Sync failed: boom",
        details: {},
      },
    }),
    stderr: "",
    exitCode: 1,
  });

  assert.equal(envelope.ok, false);
  if (envelope.ok) {
    throw new Error("expected error envelope");
  }

  assert.equal(envelope.error.code, "SYNC_FAILED");
  assert.match(envelope.error.message, /boom/);
});

test("normalizeBackendEnvelope rejects non-json backend output", () => {
  const envelope = normalizeBackendEnvelope("dashboard", {
    stdout: "Dashboard updated: /tmp/vault/dashboard.md\nliked_tracks=3\n",
    stderr: "",
    exitCode: 0,
  });

  assert.equal(envelope.ok, false);
  if (envelope.ok) {
    throw new Error("expected error envelope");
  }

  assert.equal(envelope.error.code, "BACKEND_INVALID_OUTPUT");
  assert.match(envelope.error.message, /json/i);
});
