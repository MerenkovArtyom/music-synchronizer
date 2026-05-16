import { spawn } from "node:child_process";
import path from "node:path";

import type {
  BackendCommand,
  BackendEnvelope,
  ConfigData,
  DashboardData,
  ListData,
  ListTracksRequest,
  MonthlyTopData,
  RecommendationData,
  RecommendationRequest,
  SyncData,
  TopListenRequest,
} from "../shared/contracts.js";

type BackendData =
  | ConfigData
  | SyncData
  | ListData
  | MonthlyTopData
  | DashboardData
  | RecommendationData;

export interface BackendRuntimeEnv extends NodeJS.ProcessEnv {
  MUSIC_SYNC_BACKEND_COMMAND?: string;
  MUSIC_SYNC_PACKAGED_BACKEND_COMMAND?: string;
  MUSIC_SYNC_REPO_ROOT?: string;
}

export interface BackendRuntimeContext {
  appPath: string;
  isPackaged: boolean;
}

export interface BackendInvocation {
  command: string;
  args: string[];
  cwd?: string;
}

export interface BackendRuntime {
  command: string[];
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

function isRelativeCommandToken(value: string): boolean {
  return value.startsWith("./") || value.startsWith("../");
}

function resolveCommandTokens(tokens: string[], cwd: string | undefined): string[] {
  if (!cwd) {
    return tokens;
  }

  return tokens.map((token, index) =>
    index === 0 && isRelativeCommandToken(token) ? path.resolve(cwd, token) : token,
  );
}

function buildRequestArgs(
  command: BackendCommand,
  request?: ListTracksRequest | TopListenRequest | RecommendationRequest,
): string[] {
  if (command === "list") {
    const listRequest = request as ListTracksRequest | undefined;
    if (!listRequest) {
      return [];
    }
    return listRequest.kind === "tag"
      ? ["--tag", listRequest.value]
      : ["--artist", listRequest.value];
  }

  if (command === "top-listen") {
    const topListenRequest = request as TopListenRequest | undefined;
    if (!topListenRequest) {
      return [];
    }
    return [topListenRequest.mode === "least" ? "--least" : "--most"];
  }

  if (command === "recommend") {
    const recommendationRequest = request as RecommendationRequest | undefined;
    if (!recommendationRequest?.archived) {
      return [];
    }
    return ["--archived"];
  }

  return [];
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

  return ["uv", "run", "music-sync-app"];
}

export function resolveBackendRuntime(
  env: BackendRuntimeEnv,
  isPackaged: boolean,
  appPath: string,
): BackendRuntime {
  if (!isPackaged) {
    return {
      command: resolveBackendCommand(env),
      cwd: env.MUSIC_SYNC_REPO_ROOT,
    };
  }

  const resourcesDir = path.dirname(appPath);
  const backendDir = path.join(resourcesDir, "backend");
  const commandTokens = env.MUSIC_SYNC_PACKAGED_BACKEND_COMMAND
    ? parseBackendCommandEnv(env.MUSIC_SYNC_PACKAGED_BACKEND_COMMAND)
    : ["./music-sync-app"];

  return {
    command: resolveCommandTokens(commandTokens, backendDir),
    cwd: backendDir,
  };
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

export function normalizeBackendEnvelope(
  command: BackendCommand,
  result: BackendProcessResult,
  request?: ListTracksRequest | TopListenRequest | RecommendationRequest,
): BackendEnvelope<BackendData> {
  const trimmed = result.stdout.trim();
  if (trimmed === "") {
    if ((result.exitCode ?? 1) !== 0) {
      return normalizeBackendError(
        command,
        "BACKEND_PROCESS_ERROR",
        result.stderr.trim() || `Backend exited with code ${String(result.exitCode)}`,
        {
          stdout: trimmed,
          stderr: result.stderr,
          exitCode: result.exitCode,
          request,
        },
      );
    }

    return normalizeBackendError(command, "BACKEND_EMPTY_OUTPUT", "Backend returned no output.", {
      stderr: result.stderr,
      exitCode: result.exitCode,
      request,
    });
  }

  let payload: unknown;
  try {
    payload = JSON.parse(trimmed);
  } catch {
    return normalizeBackendError(
      command,
      "BACKEND_INVALID_OUTPUT",
      "Backend returned invalid JSON output.",
      {
        stdout: trimmed,
        stderr: result.stderr,
        exitCode: result.exitCode,
        request,
      },
    );
  }

  if (!payload || typeof payload !== "object" || !("ok" in payload) || !("command" in payload)) {
    return normalizeBackendError(
      command,
      "BACKEND_INVALID_OUTPUT",
      "Backend returned an unexpected JSON envelope.",
      {
        stdout: trimmed,
        stderr: result.stderr,
        exitCode: result.exitCode,
        request,
      },
    );
  }

  return payload as BackendEnvelope<BackendData>;
}

function runProcess(invocation: BackendInvocation, env: BackendRuntimeEnv): Promise<BackendProcessResult> {
  return new Promise((resolve, reject) => {
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
      reject(
        new BackendRunnerError(
          "BACKEND_PROCESS_ERROR",
          `Failed to start backend process: ${error.message}`,
          {
            command: invocation.command,
            args: invocation.args,
            cwd: invocation.cwd,
          },
        ),
      );
    });

    child.on("close", (exitCode) => {
      resolve({ stdout, stderr, exitCode });
    });
  });
}

export async function runBackendCommand(
  command: BackendCommand,
  request: ListTracksRequest | TopListenRequest | RecommendationRequest | undefined,
  env: BackendRuntimeEnv,
  context: BackendRuntimeContext,
): Promise<BackendEnvelope<BackendData>> {
  try {
    const runtime = resolveBackendRuntime(env, context.isPackaged, context.appPath);
    const invocation = {
      command: runtime.command[0],
      args: [...runtime.command.slice(1), command, ...buildRequestArgs(command, request)],
      cwd: runtime.cwd,
    };
    const result = await runProcess(invocation, env);
    return normalizeBackendEnvelope(command, result, request);
  } catch (error) {
    if (error instanceof BackendRunnerError) {
      return normalizeBackendError(command, error.code, error.message, error.details);
    }

    return normalizeBackendError(command, "BACKEND_PROCESS_ERROR", String(error), {
      request,
    });
  }
}
