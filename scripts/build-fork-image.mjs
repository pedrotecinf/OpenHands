import { readFileSync } from "node:fs";
import { execFileSync, spawnSync } from "node:child_process";

const manifest = JSON.parse(
  readFileSync(new URL("../fork/upgrade.json", import.meta.url)),
);
const commit = execFileSync("git", ["rev-parse", "HEAD"], {
  encoding: "utf8",
}).trim();
const result = spawnSync(
  "docker",
  [
    "build",
    "-f",
    "docker/Dockerfile.fork",
    "--build-arg",
    `BASE_IMAGE=${manifest.baseImage}`,
    "--build-arg",
    `SDK_FORK_COMMIT=${manifest.sdkCommit}`,
    "--build-arg",
    `CANVAS_FORK_COMMIT=${commit}`,
    "-t",
    `pedrotecinf/openhands-canvas:${manifest.canvasRelease}-fork`,
    ...process.argv.slice(2),
    ".",
  ],
  { stdio: "inherit" },
);
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
