import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const electronDir = path.resolve(import.meta.dirname, "..");
const packageJsonPath = path.join(electronDir, "package.json");

async function readPackageJson() {
  const raw = await readFile(packageJsonPath, "utf8");
  return JSON.parse(raw) as {
    scripts: Record<string, string>;
    build: {
      artifactName?: string;
      directories?: { output?: string };
      mac?: {
        icon?: string;
        target?: Array<string | { target: string }>;
      };
    };
  };
}

test("package:dmg builds an arm64 dmg after staging the standalone backend", async () => {
  const packageJson = await readPackageJson();

  assert.equal(
    packageJson.scripts["package:dmg"],
    "npm run prepare:icon && npm run package:standalone && electron-builder --mac dmg --arm64 && node ./scripts/move-dmg.mjs",
  );
});

test("packaging output keeps intermediate app bundles under electron/release", async () => {
  const packageJson = await readPackageJson();

  assert.equal(packageJson.build.directories?.output, "release");
});

test("mac packaging targets dmg artifacts with a stable artifact name", async () => {
  const packageJson = await readPackageJson();
  const targets = packageJson.build.mac?.target ?? [];

  assert.deepEqual(targets, ["dmg"]);
  assert.equal(packageJson.build.artifactName, "Music-Synchronizer-mac-arm64.${ext}");
});

test("package:mac:dir still builds only the app bundle without creating a dmg", async () => {
  const packageJson = await readPackageJson();

  assert.equal(
    packageJson.scripts["package:mac:dir"],
    "npm run prepare:icon && npm run package:standalone && electron-builder --mac dir --arm64",
  );
});

test("packaging prepares a resized app icon from assets/icon.png", async () => {
  const packageJson = await readPackageJson();

  assert.equal(packageJson.scripts["prepare:icon"], "node ./scripts/prepare-icon.mjs");
  assert.equal(packageJson.build.mac?.icon, "build/icon.png");
});
