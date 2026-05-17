import { defineConfig, devices } from "@playwright/test";

const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  fullyParallel: true,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
  },
  webServer: skipWebServer
    ? undefined
    : {
        command: "node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort",
        url: "http://127.0.0.1:5173",
        reuseExistingServer: !process.env.CI,
        gracefulShutdown: { signal: "SIGTERM", timeout: 500 },
        timeout: 120_000,
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
