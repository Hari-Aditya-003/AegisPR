import { defineConfig } from "@playwright/test";

// This suite only reads an already-running, isolated judge build. It must never
// start the normal deployment, send provider requests, or capture access codes.
export default defineConfig({
  testDir: "./judge-e2e",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 45_000,
  reporter: [["list"]],
  outputDir: "test-results/judge",
  use: {
    baseURL: "http://127.0.0.1:3300",
    browserName: "chromium",
    viewport: { width: 1280, height: 900 },
    contextOptions: { reducedMotion: "reduce" },
    serviceWorkers: "block",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    trace: "off",
    screenshot: "off",
    video: "off",
  },
});
