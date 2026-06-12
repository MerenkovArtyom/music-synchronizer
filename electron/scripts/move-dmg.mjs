import { copyFile, readdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const electronDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(electronDir, "..");
const releaseDir = path.join(electronDir, "release");

async function main() {
  const entries = await readdir(releaseDir, { withFileTypes: true });
  const dmgFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".dmg"))
    .map((entry) => entry.name);

  if (dmgFiles.length !== 1) {
    throw new Error(
      `Expected exactly one DMG in ${releaseDir}, found ${dmgFiles.length}: ${dmgFiles.join(", ") || "(none)"}`,
    );
  }

  const fileName = dmgFiles[0];
  if (!fileName) {
    throw new Error(`Expected a DMG file in ${releaseDir}.`);
  }

  const sourcePath = path.join(releaseDir, fileName);
  const destinationPath = path.join(repoRoot, fileName);

  await rm(destinationPath, { force: true });
  await copyFile(sourcePath, destinationPath);

  console.log(`Copied ${fileName} to ${repoRoot}`);
}

await main();
