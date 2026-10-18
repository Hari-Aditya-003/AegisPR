import { afterEach, expect, test, vi } from "vitest";

afterEach(() => { vi.unstubAllEnvs(); vi.resetModules(); });

test("CSP permits the configured API origin without a broad remote wildcard", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "http://private-worker.example:8080");
  const { default: config } = await import("../next.config.mjs");
  const entries = await config.headers();
  const csp = entries[0].headers.find(header => header.key === "Content-Security-Policy").value;
  expect(csp.split("; ").find(part => part.startsWith("connect-src")))
    .toBe("connect-src 'self' http://private-worker.example:8080");
});

test("invalid or credential-bearing backend origins fail at build time", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "https://user:password@example.com");
  await expect(import("../next.config.mjs")).rejects.toThrow("API URL");
});
