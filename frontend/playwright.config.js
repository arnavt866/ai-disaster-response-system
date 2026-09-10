import { defineConfig, devices } from "@playwright/test";

const previewPort = process.env.PLAYWRIGHT_PREVIEW_PORT || "4173";
const baseURL =
  process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${previewPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./tests/e2e/results/test-output",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "tests/e2e/results/summary.json" }],
    ["html", { outputFolder: "tests/e2e/results/html-report", open: "never" }],
  ],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "off",
    video: "off",
  },
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: `npm run build && npx vite preview --host 127.0.0.1 --port ${previewPort}`,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 180_000,
        env: {
          ...process.env,
          VITE_API_URL: process.env.VITE_API_URL || "http://127.0.0.1:8000",
        },
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },
  ],
});
