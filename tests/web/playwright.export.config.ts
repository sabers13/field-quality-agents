import { defineConfig, devices } from "@playwright/test";

/**
 * Q10 screenshots run against the static export served by a plain file
 * server: no API, no model calls, no network.
 */

const PORT = 4176;

export default defineConfig({
  testDir: ".",
  testMatch: "screenshots.export.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    viewport: { width: 1280, height: 900 },
    colorScheme: "light",
    trace: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
  ],
  webServer: {
    command: `sh -c 'python3 -m http.server ${PORT} --bind 127.0.0.1 --directory "$(git rev-parse --show-toplevel)/dist/field-quality-agents"'`,
    url: `http://127.0.0.1:${PORT}`,
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
