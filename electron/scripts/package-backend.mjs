import { chmod, cp, mkdir, rm, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const electronDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(electronDir, "..");
const packageDir = path.join(electronDir, "dist", "package");
const backendDir = path.join(packageDir, "backend");
const venvDir = path.join(repoRoot, ".venv");

try {
  await stat(venvDir);
} catch {
  throw new Error(`Expected a local virtual environment at ${venvDir}. Run "uv sync" first.`);
}

await rm(packageDir, { recursive: true, force: true });
await mkdir(backendDir, { recursive: true });

await Promise.all([
  cp(path.join(repoRoot, "src"), path.join(backendDir, "src"), { recursive: true }),
  cp(venvDir, path.join(backendDir, ".venv"), { recursive: true, dereference: true }),
  cp(path.join(repoRoot, "pyproject.toml"), path.join(backendDir, "pyproject.toml")),
  cp(path.join(repoRoot, "uv.lock"), path.join(backendDir, "uv.lock")),
]);

try {
  await stat(path.join(repoRoot, ".env"));
  await cp(path.join(repoRoot, ".env"), path.join(backendDir, ".env"));
} catch {
  // Packaged app can still run without a bundled .env if the user provides configuration another way.
}

const launcherPath = path.join(backendDir, "music-sync-app");
await writeFile(
  launcherPath,
  [
    "#!/bin/sh",
    'SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"',
    'export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"',
    'exec "$SCRIPT_DIR/.venv/bin/python3" -m music_synchronizer.backend_cli "$@"',
    "",
  ].join("\n"),
  "utf8",
);
await chmod(launcherPath, 0o755);

console.log(`Packaged backend staged at ${backendDir}`);
