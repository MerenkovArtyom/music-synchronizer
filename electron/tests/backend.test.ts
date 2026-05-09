import assert from "node:assert/strict";
import test from "node:test";

import type {
  BackendEnvelope,
  ConfigData,
  ListData,
  MonthlyTopData,
  TopListenRequest,
  SyncData,
} from "../src/shared/contracts.js";
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

test("buildBackendInvocation appends command arguments without changing CLI behavior", () => {
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
  ]);
  assert.equal(invocation.cwd, "/tmp/music-sync");
});

test("buildBackendInvocation supports the top-listen command with the most flag", () => {
  const invocation = buildBackendInvocation("top-listen", ["--most"], {
    MUSIC_SYNC_BACKEND_COMMAND: '["python", "-m", "music_synchronizer.cli"]',
    MUSIC_SYNC_REPO_ROOT: "/tmp/music-sync",
  });

  assert.equal(invocation.command, "python");
  assert.deepEqual(invocation.args, ["-m", "music_synchronizer.cli", "top-listen", "--most"]);
  assert.equal(invocation.cwd, "/tmp/music-sync");
});

test("normalizeBackendEnvelope parses show-config text output", () => {
  const envelope = normalizeBackendEnvelope("show-config", {
    stdout: "Obsidian path: /tmp/vault\nLog level: INFO\n",
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

test("normalizeBackendEnvelope parses sync summary output", () => {
  const envelope = normalizeBackendEnvelope("sync", {
    stdout: "Added: 1, unchanged: 2, removed: 3.\n",
    stderr: "",
    exitCode: 0,
  }) as BackendEnvelope<SyncData>;

  assert.equal(envelope.ok, true);
  if (!envelope.ok) {
    throw new Error("expected success envelope");
  }

  assert.deepEqual(envelope.data.summary, {
    added: 1,
    unchanged: 2,
    archived: 3,
    removed: 3,
  });
});

test("normalizeBackendEnvelope parses list output using the original filter request", () => {
  const envelope = normalizeBackendEnvelope(
    "list",
    {
      stdout: "Song - Artist, Guest\n",
      stderr: "",
      exitCode: 0,
    },
    {
      kind: "artist",
      value: "artist",
    },
  ) as BackendEnvelope<ListData>;

  assert.equal(envelope.ok, true);
  if (!envelope.ok) {
    throw new Error("expected success envelope");
  }

  assert.deepEqual(envelope.data, {
    filter: {
      kind: "artist",
      value: "artist",
    },
    tracks: [
      {
        title: "Song",
        artists: ["Artist", "Guest"],
      },
    ],
  });
});

test("normalizeBackendEnvelope parses top-listen most output", () => {
  const envelope = normalizeBackendEnvelope("top-listen", {
    stdout: [
      "Most Played:",
      "1. Loud Song - Artist, Guest | monthly_listens=9 | position=2",
      "",
    ].join("\n"),
    stderr: "",
    exitCode: 0,
  }, {
    mode: "most",
  } as TopListenRequest) as BackendEnvelope<MonthlyTopData>;

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

test("normalizeBackendEnvelope parses top-listen least output", () => {
  const envelope = normalizeBackendEnvelope("top-listen", {
    stdout: [
      "Least Played:",
      "1. Quiet Song - Solo | monthly_listens=1 | position=7",
      "",
    ].join("\n"),
    stderr: "",
    exitCode: 0,
  }, {
    mode: "least",
  } as TopListenRequest) as BackendEnvelope<MonthlyTopData>;

  assert.equal(envelope.ok, true);
  if (!envelope.ok) {
    throw new Error("expected success envelope");
  }

  assert.deepEqual(envelope.data, {
    mostPlayed: [],
    leastPlayed: [
      {
        title: "Quiet Song",
        artists: ["Solo"],
        monthlyListens: 1,
        position: 7,
      },
    ],
  });
});

test("normalizeBackendEnvelope rejects invalid top-listen output", () => {
  const envelope = normalizeBackendEnvelope("top-listen", {
    stdout: "Most Played:\nnot-a-track-line\n",
    stderr: "",
    exitCode: 0,
  }, {
    mode: "most",
  } as TopListenRequest);

  assert.equal(envelope.ok, false);
  if (envelope.ok) {
    throw new Error("expected error envelope");
  }

  assert.equal(envelope.error.code, "BACKEND_INVALID_OUTPUT");
  assert.match(envelope.error.message, /top-listen/i);
});

test("normalizeBackendEnvelope returns a structured error for backend failures", () => {
  const envelope = normalizeBackendEnvelope("sync", {
    stdout: "",
    stderr: "Sync failed: boom",
    exitCode: 1,
  });

  assert.equal(envelope.ok, false);
  if (envelope.ok) {
    throw new Error("expected error envelope");
  }

  assert.equal(envelope.error.code, "SYNC_FAILED");
  assert.match(envelope.error.message, /boom/);
});
