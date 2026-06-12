import assert from "node:assert/strict";
import path from "node:path";
import test from "node:test";

// @ts-ignore Plain ESM script import for packaging tests.
import {
  buildLauncherScript,
  buildPackagedBackendLayout,
  listPrunedPythonRuntimePaths,
} from "../scripts/package-backend.mjs";

test("buildPackagedBackendLayout describes the embedded runtime layout", () => {
  const layout = buildPackagedBackendLayout("3.14");

  assert.equal(layout.launcherPath, "music-sync-app");
  assert.equal(layout.pythonHomePath, path.join("runtime", "Python.framework", "Versions", "Current"));
  assert.equal(
    layout.pythonBinaryPath,
    path.join("runtime", "Python.framework", "Versions", "Current", "bin", "python3"),
  );
  assert.equal(layout.appPath, "app");
  assert.equal(layout.sitePackagesPath, "site-packages");
});

test("buildLauncherScript targets the embedded runtime instead of a virtualenv", () => {
  const launcher = buildLauncherScript({
    appPath: "app",
    pythonBinaryPath: path.join("runtime", "Python.framework", "Versions", "Current", "bin", "python3"),
    pythonHomePath: path.join("runtime", "Python.framework", "Versions", "Current"),
    sitePackagesPath: "site-packages",
  });

  assert.match(launcher, /PYTHONHOME/);
  assert.match(launcher, /PYTHONNOUSERSITE=1/);
  assert.match(launcher, /__PYVENV_LAUNCHER__/);
  assert.match(launcher, /music_synchronizer\.backend_cli/);
  assert.doesNotMatch(launcher, /\.venv/);
});

test("listPrunedPythonRuntimePaths removes non-runtime Tcl/Tk and developer assets", () => {
  assert.deepEqual(listPrunedPythonRuntimePaths("3.14"), [
    path.join("Versions", "3.14", "Frameworks", "Tcl.framework"),
    path.join("Versions", "3.14", "Frameworks", "Tk.framework"),
    path.join("Versions", "3.14", "Headers"),
    path.join("Versions", "3.14", "share", "doc"),
    path.join("Versions", "3.14", "share", "man"),
    path.join("Versions", "3.14", "lib", "pkgconfig"),
    path.join("Versions", "3.14", "bin", "idle3"),
  ]);
});
