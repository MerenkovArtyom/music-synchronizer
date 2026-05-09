import { spawn } from "node:child_process";

import type {
  BackendCommand,
  BackendEnvelope,
  ConfigData,
  ListData,
  ListTracksRequest,
  SyncData,
} from "../shared/contracts.js";

type BackendData = ConfigData | SyncData | ListData;
type CommandDataMap = {
  "show-config": ConfigData;
  sync: SyncData;
  list: ListData;
};

export interface BackendRuntimeEnv extends NodeJS.ProcessEnv {
  MUSIC_SYNC_BACKEND_COMMAND?: string;
  MUSIC_SYNC_REPO_ROOT?: string;
}

export interface BackendInvocation {
  command: string;
  args: string[];
  cwd?: string;
}

export interface BackendProcessResult {
  stdout: string;
  stderr: string;
  exitCode: number | null;
}

export class BackendRunnerError extends Error {
  code: string;
  details: Record<string, unknown>;

  constructor(code: string, message: string, details: Record<string, unknown> = {}) {
    super(message);
    this.name = "BackendRunnerError";
    this.code = code;
    this.details = details;
  }
}

export function parseBackendCommandEnv(rawValue: string): string[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawValue);
  } catch (error) {
    throw new BackendRunnerError(
      "BACKEND_COMMAND_PARSE_ERROR",
      "MUSIC_SYNC_BACKEND_COMMAND must be a JSON array of command tokens.",
      { cause: error instanceof Error ? error.message : String(error) },
    );
  }

  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new BackendRunnerError(
      "BACKEND_COMMAND_PARSE_ERROR",
      "MUSIC_SYNC_BACKEND_COMMAND must be a non-empty JSON array of command tokens.",
    );
  }

  const tokens = parsed.map((value) => String(value).trim());
  if (tokens.some((value) => value === "")) {
    throw new BackendRunnerError(
      "BACKEND_COMMAND_PARSE_ERROR",
      "MUSIC_SYNC_BACKEND_COMMAND cannot include empty command tokens.",
    );
  }

  return tokens;
}

export function resolveBackendCommand(env: BackendRuntimeEnv): string[] {
  if (env.MUSIC_SYNC_BACKEND_COMMAND) {
    return parseBackendCommandEnv(env.MUSIC_SYNC_BACKEND_COMMAND);
  }

  return ["uv", "run", "music-sync"];
}

export function buildBackendInvocation(
  command: BackendCommand,
  extraArgs: string[] = [],
  env: BackendRuntimeEnv = process.env,
): BackendInvocation {
  const commandTokens = resolveBackendCommand(env);

  return {
    command: commandTokens[0],
    args: [...commandTokens.slice(1), command, ...extraArgs],
    cwd: env.MUSIC_SYNC_REPO_ROOT,
  };
}

function parseShowConfigOutput(stdout: string): ConfigData {
  const lines = stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line !== "");

  let obsidianVaultPath = "";
  let logLevel = "";

  for (const line of lines) {
    if (line.startsWith("Obsidian path: ")) {
      obsidianVaultPath = line.slice("Obsidian path: ".length).trim();
      continue;
    }
    if (line.startsWith("Log level: ")) {
      logLevel = line.slice("Log level: ".length).trim();
    }
  }

  if (obsidianVaultPath === "" || logLevel === "") {
    throw new BackendRunnerError(
      "BACKEND_INVALID_OUTPUT",
      "show-config output did not include the expected fields.",
      { stdout },
    );
  }

  return {
    config: {
      yandexMusicTokenPresent: true,
      obsidianVaultPath,
      logLevel,
    },
  };
}

function parseSyncOutput(stdout: string): SyncData {
  const trimmed = stdout.trim();
  const match = /^Added:\s*(\d+),\s*unchanged:\s*(\d+),\s*removed:\s*(\d+)\.$/m.exec(trimmed);
  if (!match) {
    throw new BackendRunnerError(
      "BACKEND_INVALID_OUTPUT",
      "sync output did not match the expected summary format.",
      { stdout: trimmed },
    );
  }

  const added = Number(match[1]);
  const unchanged = Number(match[2]);
  const removed = Number(match[3]);

  return {
    summary: {
      added,
      unchanged,
      archived: removed,
      removed,
    },
  };
}

function parseListOutput(request: ListTracksRequest | undefined, stdout: string): ListData {
  const lines = stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line !== "");

  const filter = {
    kind: request?.kind ?? "tag",
    value: request?.value ?? "",
  } as ListData["filter"];

  if (lines.length === 0) {
    return { filter, tracks: [] };
  }

  if (lines.length === 1) {
    const noTracksMessage = `No active saved tracks found for ${filter.kind} "${filter.value}".`;
    if (lines[0] === noTracksMessage) {
      return { filter, tracks: [] };
    }
  }

  return {
    filter,
    tracks: lines.map((line) => {
      const [title, artistsText = ""] = line.split(" - ", 2);
      return {
        title: title.trim(),
        artists:
          artistsText.trim() === "" ? [] : artistsText.split(",").map((artist) => artist.trim()),
      };
    }),
  };
}

function normalizeBackendError(
  command: BackendCommand,
  code: string,
  message: string,
  details: Record<string, unknown> = {},
): BackendEnvelope<never> {
  return {
    ok: false,
    command,
    error: {
      code,
      message,
      details,
    },
  };
}

export function normalizeBackendEnvelope(
  command: BackendCommand,
  result: BackendProcessResult,
  listRequest?: ListTracksRequest,
): BackendEnvelope<BackendData> {
  const trimmed = result.stdout.trim();
  if ((result.exitCode ?? 1) !== 0) {
    const message = result.stderr.trim() || trimmed || `Backend exited with code ${String(result.exitCode)}`;
    const code =
      command === "sync" ? "SYNC_FAILED" : command === "list" ? "LIST_FAILED" : "SHOW_CONFIG_FAILED";

    return normalizeBackendError(command, code, message, {
      stdout: trimmed,
      stderr: result.stderr,
      exitCode: result.exitCode,
    });
  }

  if (trimmed === "") {
    return normalizeBackendError(command, "BACKEND_EMPTY_OUTPUT", "Backend returned no output.", {
      stderr: result.stderr,
      exitCode: result.exitCode,
    });
  }

  try {
    const data =
      command === "show-config"
        ? parseShowConfigOutput(trimmed)
        : command === "sync"
          ? parseSyncOutput(trimmed)
          : parseListOutput(listRequest, trimmed);

    return {
      ok: true,
      command,
      data,
    } as BackendEnvelope<BackendData>;
  } catch (error) {
    if (error instanceof BackendRunnerError) {
      return normalizeBackendError(command, error.code, error.message, error.details);
    }

    const message = error instanceof Error ? error.message : String(error);
    return normalizeBackendError(command, "BACKEND_INVALID_OUTPUT", message, {
      stdout: trimmed,
      stderr: result.stderr,
      exitCode: result.exitCode,
    });
  }
}

function listRequestArgs(request: ListTracksRequest): string[] {
  if (request.value.trim() === "") {
    throw new BackendRunnerError("INVALID_LIST_REQUEST", "List requests require a non-empty filter value.");
  }

  return [`--${request.kind}`, request.value];
}

export async function runBackendCommand<C extends BackendCommand>(
  command: C,
  listRequest?: ListTracksRequest,
  env: BackendRuntimeEnv = process.env,
): Promise<BackendEnvelope<CommandDataMap[C]>> {
  const extraArgs = command === "list" && listRequest ? listRequestArgs(listRequest) : [];

  let invocation: BackendInvocation;

  try {
    invocation = buildBackendInvocation(command, extraArgs, env);
  } catch (error) {
    if (error instanceof BackendRunnerError) {
      return normalizeBackendError(
        command,
        error.code,
        error.message,
        error.details,
      ) as BackendEnvelope<CommandDataMap[C]>;
    }

    throw error;
  }

  return await new Promise<BackendEnvelope<CommandDataMap[C]>>((resolve) => {
    const child = spawn(invocation.command, invocation.args, {
      cwd: invocation.cwd,
      env,
      stdio: ["ignore", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    child.stdout.on("data", (chunk: Buffer | string) => {
      stdout += chunk.toString();
    });

    child.stderr.on("data", (chunk: Buffer | string) => {
      stderr += chunk.toString();
    });

    child.on("error", (error) => {
      resolve({
        ok: false,
        command,
        error: {
          code: "BACKEND_PROCESS_ERROR",
          message: `Failed to start backend command: ${error.message}`,
          details: {
            command: invocation.command,
          },
        },
      } as BackendEnvelope<CommandDataMap[C]>);
    });

    child.on("close", (exitCode) => {
      resolve(
        normalizeBackendEnvelope(command, {
          stdout,
          stderr,
          exitCode,
        }, listRequest) as BackendEnvelope<CommandDataMap[C]>,
      );
    });
  });
}
