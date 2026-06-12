import { execFile } from "node:child_process";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const execFileAsync = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const electronDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(electronDir, "..");
const sourceIconPath = path.join(repoRoot, "assets", "icon.png");
const buildDir = path.join(electronDir, "build");
const outputIconPath = path.join(buildDir, "icon.png");

async function main() {
  await mkdir(buildDir, { recursive: true });

  await execFileAsync("sips", [
    "-z",
    "1024",
    "1024",
    sourceIconPath,
    "--out",
    outputIconPath,
  ]);

  console.log(`Prepared ${outputIconPath}`);
}

await main();
