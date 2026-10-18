import { afterEach, describe, expect, it, vi } from "vitest";

import { createVerification, getVerification, requestRepair, saveAccessCode } from "../lib/api";


afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear(); });

describe("private deployment access", () => {
  it("attaches the session code to every paid or evidence request, and can clear it", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ id: "run-1" }), { status: 200 })));
    vi.stubGlobal("fetch", fetchMock);
    saveAccessCode("private-code");
    await createVerification("https://github.com/acme/store/pull/42");
    await getVerification("run-1");
    await requestRepair("run-1", "finding-1");
    for (const [, options] of fetchMock.mock.calls) expect(options.headers).toMatchObject({ Authorization: "Bearer private-code" });
    saveAccessCode("");
    await getVerification("run-1");
    expect(fetchMock.mock.lastCall?.[1].headers).not.toHaveProperty("Authorization");
    expect(sessionStorage.length).toBe(0);
  });

  it("explains how to recover from an authorization failure without exposing the code", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 401 })));
    await expect(getVerification("run-1")).rejects.toThrow(/private deployment access/i);
  });
});

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

  it("uses the safe fallback when an error response contains JSON null", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("null", { status: 502 })));
    await expect(createVerification("bad")).rejects.toThrow("Verification could not start");
  });
});

describe("requestRepair", () => {
  it("starts isolated repair verification for the selected finding", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "run-1", status: "RUNNING" }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(requestRepair("run-1", "finding-1")).resolves.toEqual({ id: "run-1", status: "RUNNING" });
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/verifications/run-1/repair"),
      expect.objectContaining({ method: "POST", body: JSON.stringify({ finding_id: "finding-1" }) }),
    );
  });

  it("surfaces a bounded repair error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Repair unavailable" }), { status: 409 })));
    await expect(requestRepair("run-1", "finding-1")).rejects.toThrow("Repair unavailable");
  });
});
