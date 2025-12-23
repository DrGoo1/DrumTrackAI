import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 240_000,
  retries: 1,
  use: {
    baseURL: (globalThis as any)?.process?.env?.E2E_BASE_URL || "http://localhost:3000",
    headless: true,
    actionTimeout: 60_000,
    navigationTimeout: 60_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
});
