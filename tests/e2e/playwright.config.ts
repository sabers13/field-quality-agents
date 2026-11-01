import { defineConfig, devices } from "@playwright/test";

const PORT = 4175;
const URL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: URL,
    viewport: { width: 1280, height: 900 },
    colorScheme: "light",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } },
    },
  ],
  webServer: {
    command:
      "sh -c 'cd \"$(git rev-parse --show-toplevel)\" && " +
      `uv run fqa serve --mode live --run-id e2e-fixture ` +
      `--results-dir results/runs --recordings-dir tests/fixtures/recordings ` +
      `--static-dir web/dist --port ${PORT}'`,
    url: `${URL}/api/health`,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
