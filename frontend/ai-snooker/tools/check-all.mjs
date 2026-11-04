// Run the existing offline checks in isolated Node processes.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const cwd = fileURLToPath(new URL("..", import.meta.url));
const checks = [
  "check-render.mjs",
  "check-navigation.mjs",
  "check-module-settings.mjs",
  "check-m1-auto.mjs",
  "check-m3-auto-save.mjs",
  "check-camera-colour.mjs",
  "check-completion.mjs",
  "check-m3-preparation.mjs",
];
for (const check of checks) {
  const result = spawnSync(process.execPath, [fileURLToPath(new URL(check, import.meta.url))], {
    cwd,
    stdio: "inherit",
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
