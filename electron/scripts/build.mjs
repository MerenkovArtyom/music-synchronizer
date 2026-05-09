import { cp, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { build } from "esbuild";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, "..");
const srcDir = path.join(rootDir, "src");
const distDir = path.join(rootDir, "dist");

await mkdir(path.join(distDir, "renderer"), { recursive: true });

await Promise.all([
  build({
    entryPoints: [path.join(srcDir, "main", "index.ts")],
    outfile: path.join(distDir, "main", "index.cjs"),
    bundle: true,
    platform: "node",
    format: "cjs",
    target: "node24",
    external: ["electron"],
    sourcemap: true,
  }),
  build({
    entryPoints: [path.join(srcDir, "preload", "index.ts")],
    outfile: path.join(distDir, "preload", "index.cjs"),
    bundle: true,
    platform: "node",
    format: "cjs",
    target: "node24",
    external: ["electron"],
    sourcemap: true,
  }),
  build({
    entryPoints: [path.join(srcDir, "renderer", "index.ts")],
    outfile: path.join(distDir, "renderer", "index.js"),
    bundle: true,
    platform: "browser",
    format: "iife",
    target: "chrome138",
    sourcemap: true,
  }),
]);

await Promise.all([
  cp(path.join(srcDir, "renderer", "index.html"), path.join(distDir, "renderer", "index.html")),
  cp(path.join(srcDir, "renderer", "styles.css"), path.join(distDir, "renderer", "styles.css")),
]);
