import assert from "node:assert/strict";
import test from "node:test";

import type { BackendEnvelope, ConfigData } from "../src/shared/contracts.js";
import {
  buildBackendInvocation,
  normalizeBackendEnvelope,
  parseBackendCommandEnv,
  resolveBackendCommand,
} from "../src/main/backend.js";

test("parseBackendCommandEnv accepts a JSON string array", () => {
  assert.deepEqual(parseBackendCommandEnv('["python", "-m", "music_synchronizer.cli"]'), [
    "python",
    "-m",
    "music_synchronizer.cli",
  ]);
});

test("parseBackendCommandEnv rejects a non-array JSON value", () => {
  assert.throws(() => parseBackendCommandEnv('"uv run music-sync"'), /JSON array/);
});

test("resolveBackendCommand falls back to uv run music-sync", () => {
  assert.deepEqual(resolveBackendCommand({}), ["uv", "run", "music-sync"]);
});

test("buildBackendInvocation appends command arguments and --json", () => {
  const invocation = buildBackendInvocation("list", ["--artist", "Artist Guest"], {
    MUSIC_SYNC_BACKEND_COMMAND: '["python", "-m", "music_synchronizer.cli"]',
    MUSIC_SYNC_REPO_ROOT: "/tmp/music-sync",
  });

  assert.equal(invocation.command, "python");
  assert.deepEqual(invocation.args, [
    "-m",
    "music_synchronizer.cli",
    "list",
    "--artist",
    "Artist Guest",
    "--json",
  ]);
  assert.equal(invocation.cwd, "/tmp/music-sync");
});

test("normalizeBackendEnvelope preserves a valid backend success envelope", () => {
  const envelope = normalizeBackendEnvelope("show-config", {
    stdout: JSON.stringify({
      ok: true,
      command: "show-config",
      data: {
        config: {
          yandexMusicTokenPresent: false,
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
});

test("normalizeBackendEnvelope returns a structured protocol error for invalid JSON", () => {
  const envelope = normalizeBackendEnvelope("sync", {
    stdout: "not json",
    stderr: "traceback",
    exitCode: 1,
  });

  assert.equal(envelope.ok, false);
  if (envelope.ok) {
    throw new Error("expected error envelope");
  }

  assert.equal(envelope.error.code, "BACKEND_INVALID_JSON");
  assert.match(envelope.error.details.stdout as string, /not json/);
});
