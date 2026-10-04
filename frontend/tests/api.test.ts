import { afterEach, describe, expect, it, vi } from "vitest";

import { createVerification } from "../lib/api";


afterEach(() => vi.unstubAllGlobals());

describe("createVerification", () => {
  it("posts the pull request and returns the run", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "run-1" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(createVerification("https://github.com/acme/store/pull/42")).resolves.toEqual({ id: "run-1" });
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/verifications"), expect.objectContaining({ method: "POST" }));
  });

  it("surfaces the bounded API error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Invalid PR" }), { status: 422 })));
    await expect(createVerification("bad")).rejects.toThrow("Invalid PR");
  });

  it("uses a safe fallback when an error response is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not-json", { status: 500 })));
    await expect(createVerification("bad")).rejects.toThrow("Verification could not start");
  });
});
