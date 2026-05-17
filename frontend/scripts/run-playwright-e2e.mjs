import { spawn } from "node:child_process";

const port = 5173;
const baseUrl = `http://127.0.0.1:${port}`;

function spawnProcess(command, args, options = {}) {
  return spawn(command, args, {
    cwd: process.cwd(),
    stdio: options.stdio ?? "inherit",
    env: { ...process.env, ...options.env },
  });
}

async function waitForServer(timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(baseUrl);
      if (response.ok) return;
    } catch {
      // Server is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${baseUrl}`);
}

function stopProcessTree(child) {
  if (!child.pid || child.killed) return;
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], {
      stdio: "ignore",
    });
    return;
  }
  child.kill("SIGTERM");
}

const server = spawnProcess(
  "node",
  ["./node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(port), "--strictPort"],
  { stdio: "ignore" },
);

let exitCode = 1;
try {
  await waitForServer();
  const test = spawnProcess("node", ["./node_modules/@playwright/test/cli.js", "test"], {
    env: { PLAYWRIGHT_SKIP_WEBSERVER: "1" },
  });
  exitCode = await new Promise((resolve) => {
    test.on("exit", (code) => resolve(code ?? 1));
  });
} finally {
  stopProcessTree(server);
}

process.exit(exitCode);
