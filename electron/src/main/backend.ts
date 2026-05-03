import { spawn } from "node:child_process";

import type {
  BackendCommand,
  BackendEnvelope,
  BackendErrorPayload,
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

function asObject(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
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
    args: [...commandTokens.slice(1), command, ...extraArgs, "--json"],
    cwd: env.MUSIC_SYNC_REPO_ROOT,
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
): BackendEnvelope<BackendData> {
  const trimmed = result.stdout.trim();
  if (trimmed === "") {
    return normalizeBackendError(command, "BACKEND_EMPTY_OUTPUT", "Backend returned no JSON output.", {
      stderr: result.stderr,
      exitCode: result.exitCode,
    });
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    return normalizeBackendError(command, "BACKEND_INVALID_JSON", "Backend output was not valid JSON.", {
      stdout: trimmed,
      stderr: result.stderr,
      exitCode: result.exitCode,
    });
  }

  const envelope = asObject(parsed);
  if (envelope === null) {
    return normalizeBackendError(command, "BACKEND_INVALID_ENVELOPE", "Backend JSON must be an object.", {
      stdout: trimmed,
      stderr: result.stderr,
      exitCode: result.exitCode,
    });
  }

  if (envelope.command !== command) {
    return normalizeBackendError(
      command,
      "BACKEND_COMMAND_MISMATCH",
      `Backend responded for "${String(envelope.command)}" instead of "${command}".`,
      {
        expectedCommand: command,
        actualCommand: envelope.command,
        stderr: result.stderr,
        exitCode: result.exitCode,
      },
    );
  }

  if (typeof envelope.ok !== "boolean") {
    return normalizeBackendError(
      command,
      "BACKEND_INVALID_ENVELOPE",
      "Backend JSON is missing a boolean ok field.",
      {
        stdout: trimmed,
        stderr: result.stderr,
        exitCode: result.exitCode,
      },
    );
  }

  if (envelope.ok) {
    if (asObject(envelope.data) === null) {
      return normalizeBackendError(
        command,
        "BACKEND_INVALID_ENVELOPE",
        "Backend success payload is missing data.",
        {
          stdout: trimmed,
          stderr: result.stderr,
          exitCode: result.exitCode,
        },
      );
    }

    return envelope as BackendEnvelope<BackendData>;
  }

  const errorPayload = asObject(envelope.error);
  if (
    errorPayload === null ||
    typeof errorPayload.code !== "string" ||
    typeof errorPayload.message !== "string"
  ) {
    return normalizeBackendError(
      command,
      "BACKEND_INVALID_ENVELOPE",
      "Backend error payload is malformed.",
      {
        stdout: trimmed,
        stderr: result.stderr,
        exitCode: result.exitCode,
      },
    );
  }

  const normalized: BackendErrorPayload = {
    code: errorPayload.code,
    message: errorPayload.message,
    details: asObject(errorPayload.details) ?? {},
  };

  return {
    ok: false,
    command,
    error: normalized,
  };
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
        }) as BackendEnvelope<CommandDataMap[C]>,
      );
    });
  });
}
