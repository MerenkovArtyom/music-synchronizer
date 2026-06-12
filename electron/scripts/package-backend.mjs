import { execFile } from "node:child_process";
import { chmod, cp, mkdir, readlink, readdir, rm, stat, symlink, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const electronDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(electronDir, "..");
const packageDir = path.join(electronDir, "dist", "package");
const backendDir = path.join(packageDir, "backend");

export function buildPackagedBackendLayout(pythonVersion) {
  return {
    appPath: "app",
    launcherPath: "music-sync-app",
    pythonFrameworkPath: path.join("runtime", "Python.framework"),
    pythonHomePath: path.join("runtime", "Python.framework", "Versions", "Current"),
    pythonBinaryPath: path.join("runtime", "Python.framework", "Versions", "Current", "bin", "python3"),
    pythonVersion,
    sitePackagesPath: "site-packages",
  };
}

export function listPrunedPythonRuntimePaths(pythonVersion) {
  return [
    path.join("Versions", pythonVersion, "Frameworks", "Tcl.framework"),
    path.join("Versions", pythonVersion, "Frameworks", "Tk.framework"),
    path.join("Versions", pythonVersion, "Headers"),
    path.join("Versions", pythonVersion, "share", "doc"),
    path.join("Versions", pythonVersion, "share", "man"),
    path.join("Versions", pythonVersion, "lib", "pkgconfig"),
    path.join("Versions", pythonVersion, "bin", "idle3"),
  ];
}

export function buildLauncherScript({
  appPath,
  pythonBinaryPath,
  pythonHomePath,
  sitePackagesPath,
}) {
  return [
    "#!/bin/sh",
    "set -eu",
    'SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"',
    `PYTHON_HOME="$SCRIPT_DIR/${pythonHomePath}"`,
    `PYTHON_BIN="$SCRIPT_DIR/${pythonBinaryPath}"`,
    `APP_PATH="$SCRIPT_DIR/${appPath}"`,
    `SITE_PACKAGES_PATH="$SCRIPT_DIR/${sitePackagesPath}"`,
    "unset __PYVENV_LAUNCHER__",
    'export PYTHONHOME="$PYTHON_HOME"',
    'export PYTHONPATH="$SITE_PACKAGES_PATH:$APP_PATH${PYTHONPATH:+:$PYTHONPATH}"',
    'export PYTHONNOUSERSITE=1',
    'exec "$PYTHON_BIN" -m music_synchronizer.backend_cli "$@"',
    "",
  ].join("\n");
}

async function readPackagingPythonInfo(currentRepoRoot) {
  const venvPython = path.join(currentRepoRoot, ".venv", "bin", "python");

  try {
    await stat(venvPython);
  } catch {
    throw new Error(`Expected a local virtual environment at ${venvPython}. Run "uv sync" first.`);
  }

  const { stdout } = await execFileAsync(
    venvPython,
    [
      "-c",
      [
        "import json, platform, sys, sysconfig",
        "from pathlib import Path",
        "base_prefix = Path(sys.base_prefix).resolve()",
        "site_packages = Path(sysconfig.get_path('purelib')).resolve()",
        "info = {",
        "    'base_prefix': str(base_prefix),",
        "    'framework_root': str(base_prefix.parents[1]),",
        "    'machine': platform.machine(),",
        "    'platform_system': platform.system(),",
        "    'python_version': '.'.join(platform.python_version_tuple()[:2]),",
        "    'site_packages': str(site_packages),",
        "}",
        "print(json.dumps(info))",
      ].join("\n"),
    ],
    {
      cwd: currentRepoRoot,
    },
  );

  return JSON.parse(stdout);
}

async function removeVirtualenvPthFiles(sitePackagesDir) {
  const entries = await readdir(sitePackagesDir);
  const blockedNames = new Set([
    "_editable_impl_music_synchronizer.pth",
    "_virtualenv.pth",
  ]);

  await Promise.all(
    entries
      .filter((entry) => blockedNames.has(entry))
      .map((entry) => unlink(path.join(sitePackagesDir, entry))),
  );
}

async function rewriteFrameworkSymlinks(rootDir, sourceFrameworkRoot, packagedFrameworkRoot = rootDir) {
  const entries = await readdir(rootDir, { withFileTypes: true });

  await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(rootDir, entry.name);

      if (entry.isSymbolicLink()) {
        const targetPath = await readlink(entryPath);
        if (!path.isAbsolute(targetPath) || !targetPath.startsWith(sourceFrameworkRoot)) {
          return;
        }

        const targetRelativeToFramework = path.relative(sourceFrameworkRoot, targetPath);
        const packagedTargetPath = path.join(packagedFrameworkRoot, targetRelativeToFramework);
        const replacementTarget = path.relative(path.dirname(entryPath), packagedTargetPath);

        await unlink(entryPath);
        await symlink(replacementTarget || ".", entryPath);
        return;
      }

      if (entry.isDirectory()) {
        await rewriteFrameworkSymlinks(entryPath, sourceFrameworkRoot, packagedFrameworkRoot);
      }
    }),
  );
}

async function pruneBrokenSymlinks(rootDir) {
  const entries = await readdir(rootDir, { withFileTypes: true });

  await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(rootDir, entry.name);

      if (entry.isSymbolicLink()) {
        try {
          await stat(entryPath);
        } catch {
          await unlink(entryPath);
        }
        return;
      }

      if (entry.isDirectory()) {
        await pruneBrokenSymlinks(entryPath);
      }
    }),
  );
}

async function prunePythonRuntimeFiles(runtimeDir, pythonVersion) {
  await Promise.all(
    listPrunedPythonRuntimePaths(pythonVersion).map((relativePath) =>
      rm(path.join(runtimeDir, relativePath), { recursive: true, force: true }),
    ),
  );
}

async function validatePackagedBackend(stagedBackendDir) {
  const launcherPath = path.join(stagedBackendDir, "music-sync-app");
  const { stdout } = await execFileAsync(launcherPath, ["show-config"], {
    cwd: stagedBackendDir,
    env: {
      ...process.env,
      MUSIC_SYNC_CONFIG_PATH: path.join(stagedBackendDir, "packaged-backend-smoke.env"),
    },
  });

  const payload = JSON.parse(stdout);
  if (!payload || payload.ok !== true || payload.command !== "show-config") {
    throw new Error("Packaged backend self-check failed: expected a show-config success envelope.");
  }
}

export async function stagePackagedBackend({
  currentBackendDir = backendDir,
  currentPackageDir = packageDir,
  currentRepoRoot = repoRoot,
} = {}) {
  const pythonInfo = await readPackagingPythonInfo(currentRepoRoot);

  if (pythonInfo.platform_system !== "Darwin" || pythonInfo.machine !== "arm64") {
    throw new Error(
      `Standalone packaging requires a macOS arm64 Python runtime. Received ${pythonInfo.platform_system} ${pythonInfo.machine}.`,
    );
  }

  const layout = buildPackagedBackendLayout(pythonInfo.python_version);
  const appDir = path.join(currentBackendDir, layout.appPath);
  const runtimeDir = path.join(currentBackendDir, layout.pythonFrameworkPath);
  const sitePackagesDir = path.join(currentBackendDir, layout.sitePackagesPath);

  await rm(currentPackageDir, { recursive: true, force: true });
  await Promise.all([
    mkdir(currentBackendDir, { recursive: true }),
    mkdir(path.dirname(runtimeDir), { recursive: true }),
    mkdir(appDir, { recursive: true }),
  ]);

  await Promise.all([
    cp(
      path.join(currentRepoRoot, "src", "music_synchronizer"),
      path.join(appDir, "music_synchronizer"),
      { recursive: true },
    ),
    cp(pythonInfo.framework_root, runtimeDir, { recursive: true }),
    cp(pythonInfo.site_packages, sitePackagesDir, { recursive: true }),
  ]);

  await prunePythonRuntimeFiles(runtimeDir, layout.pythonVersion);
  await rewriteFrameworkSymlinks(runtimeDir, pythonInfo.framework_root);
  await pruneBrokenSymlinks(runtimeDir);
  await removeVirtualenvPthFiles(sitePackagesDir);

  const launcherPath = path.join(currentBackendDir, layout.launcherPath);
  await writeFile(
    launcherPath,
    buildLauncherScript({
      appPath: layout.appPath,
      pythonBinaryPath: layout.pythonBinaryPath,
      pythonHomePath: layout.pythonHomePath,
      sitePackagesPath: layout.sitePackagesPath,
    }),
    "utf8",
  );
  await chmod(launcherPath, 0o755);

  await validatePackagedBackend(currentBackendDir);
}

async function main() {
  await stagePackagedBackend();
  console.log(`Packaged backend staged at ${backendDir}`);
}

if (process.argv[1] === __filename) {
  await main();
}
