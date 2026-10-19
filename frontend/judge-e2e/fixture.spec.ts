import { readFileSync, readdirSync } from "node:fs";
import { expect, test, type Locator } from "@playwright/test";

import type { TestExecution, VerificationRun } from "../lib/types";

const apiOrigin = "http://127.0.0.1:18080";
const artifacts = new URL("../../artifacts/judge/", import.meta.url);
type Language = "python" | "node";
type JudgeRun = VerificationRun & {
  completed_at: string;
  metrics: VerificationRun["metrics"] & { model_calls: number };
};

function privateCode(): string {
  try {
    const code = readFileSync(new URL("access-code", artifacts), "utf8").trim();
    if (code.length < 16 || code.length > 512) throw new Error("Invalid private code");
    return code;
  } catch {
    throw new Error("Judge access-code file is missing or invalid. Run the isolated judge build and export first.");
  }
}

function exportedFixture(language: Language, code: string): JudgeRun {
  const evidence = new URL("evidence/", artifacts);
  let reports: JudgeRun[];
  try {
    reports = readdirSync(evidence).filter(name => /^[a-f\d-]+\.json$/i.test(name)).map(name => {
      const serialized = readFileSync(new URL(name, evidence), "utf8");
      // Never let an assertion dump a credential accidentally present in data.
      if (serialized.includes(code)) throw new Error("Unsafe exported evidence");
      return JSON.parse(serialized) as JudgeRun;
    });
  } catch {
    throw new Error("Judge evidence export is missing, invalid, or unsafe. Export the real fixture receipts first.");
  }
  const report = reports.filter(item => item.summary?.repository === `coupon-${language}`)
    .sort((a, b) => b.completed_at.localeCompare(a.completed_at))[0];
  if (!report || !/^[a-f\d-]{36}$/i.test(report.id)) {
    throw new Error(`A real exported ${language} controlled fixture receipt is required.`);
  }
  return report;
}

async function apiGet(path: string, code?: string): Promise<Response> {
  // Native fetch avoids Playwright's request call logs retaining Bearer headers.
  // Hardcoded loopback and redirect refusal keep the private code on this host.
  if (!/^\/api\/(?:budget|verifications\/[a-f\d-]{36})$/i.test(path)) {
    throw new Error("Judge smoke tests only allow read-only fixture and budget URLs.");
  }
  try {
    return await fetch(`${apiOrigin}${path}`, {
      method: "GET", redirect: "error", signal: AbortSignal.timeout(10_000),
      headers: code ? { Authorization: `Bearer ${code}` } : {},
    });
  } catch {
    throw new Error("The isolated judge API GET failed. Check the local 18080 tunnel or service.");
  }
}

async function safeJson<T>(response: Response, code: string): Promise<T> {
  const serialized = await response.text();
  if (serialized.includes(code)) throw new Error("Private access code appeared in an API response.");
  try { return JSON.parse(serialized) as T; }
  catch { throw new Error("The isolated judge API did not return valid JSON."); }
}

async function assertExecution(container: Locator, execution: TestExecution, command?: string) {
  await expect(container.getByText(execution.commit, { exact: true })).toBeVisible();
  await expect(container.getByText(`${execution.duration_ms} ms`, { exact: true })).toBeVisible();
  await expect(container.locator("dd").last()).toHaveText(String(execution.exit_code ?? "Not recorded"));
  const captured = container.locator("pre");
  await expect(captured.nth(0)).toHaveText(execution.environment?.command ?? command ?? "Not recorded");
  await expect(captured.nth(1)).toHaveText(execution.stdout || "No standard output captured.");
  await expect(captured.nth(2)).toHaveText(execution.stderr || "No standard error captured.");
}

for (const language of ["python", "node"] as const) {
  test.describe(`Real ${language} controlled fixture`, () => {
    test("unauthenticated evidence and spending requests are rejected", async () => {
      const exported = exportedFixture(language, privateCode());
      expect((await apiGet(`/api/verifications/${exported.id}`)).status).toBe(401);
      expect((await apiGet("/api/budget")).status).toBe(401);
    });

    test("renders actual authenticated Docker receipts with explicit no-model provenance", async ({ page, context }) => {
      const code = privateCode();
      const exported = exportedFixture(language, code);
      const response = await apiGet(`/api/verifications/${exported.id}`, code);
      expect(response.status).toBe(200);
      const run = await safeJson<JudgeRun>(response, code);
      expect(run).toEqual(exported);
      expect(run.evidence_mode).toBe("controlled_fixture");
      expect(run.model_used).toBe("controlled-fixture-no-model");
      expect(run.status).toBe("FIX_VERIFIED");
      expect(run.metrics.model_calls).toBe(0);
      expect(run.metrics.input_tokens).toBe(0);
      expect(run.metrics.output_tokens).toBe(0);
      expect(run.metrics.accounted_cost_usd).toBe(0);
      expect(run.metrics.context_accelerator).toBe("not_used");
      expect(run.findings).toHaveLength(1);
      expect(run.summary?.base_commit).toMatch(/^[a-f\d]{40}$/);
      expect(run.summary?.head_commit).toMatch(/^[a-f\d]{40}$/);
      expect(run.summary?.base_commit).not.toBe(run.summary?.head_commit);
      expect(run.findings[0].base_execution.status).toBe("PASSED");
      expect(run.findings[0].head_execution.status).toBe("FAILED");
      expect(run.repair?.status).toBe("VERIFIED");
      expect(run.repair?.checks.map(check => check.name)).toEqual(expect.arrayContaining(["existing_tests", "generated_tests"]));

      await context.addInitScript(value => {
        if (window.location.origin === "http://127.0.0.1:3300") {
          sessionStorage.setItem("aegispr.deployment-access", value);
        }
      }, code);
      let unsafeBrowserRequest = false;
      page.on("request", request => {
        if (request.url().includes(code) || !["GET", "OPTIONS"].includes(request.method())) unsafeBrowserRequest = true;
      });
      await page.goto(`/verifications/${run.id}`);
      const provenance = page.getByRole("note", { name: /controlled fixture/i });
      await expect(provenance).toBeVisible();
      await expect(provenance).toContainText("No model call or live GitHub pull request analysis was performed.");
      await expect(page.getByRole("heading", { name: "Manual repair evidence" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Fixed fixture test artifacts" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Prewritten fixture hypothesis" })).toBeVisible();
      await expect(page.getByText("Not used (controlled fixture)", { exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: /generate and verify repair/i })).toHaveCount(0);
      await page.getByText("Inspect branch execution evidence", { exact: true }).click();
      await assertExecution(page.getByRole("heading", { name: "Base revision", exact: true }).locator(".."), run.findings[0].base_execution);
      await assertExecution(page.getByRole("heading", { name: "Fixture head revision", exact: true }).locator(".."), run.findings[0].head_execution);
      for (const check of run.repair!.checks) {
        // Unsupported optional build/lint checks must remain honestly skipped.
        expect(check.execution.status).toBe(check.command ? "PASSED" : "SKIPPED");
        const summary = page.getByText(`Inspect repair check: ${check.name.replaceAll("_", " ")}`, { exact: true });
        await summary.click();
        await assertExecution(summary.locator(".."), check.execution, check.command);
      }
      for (const artifact of run.generated_tests ?? []) {
        const summary = page.getByText(artifact.file_path, { exact: true });
        await summary.click();
        await expect(summary.locator("..").locator("pre")).toHaveText(artifact.test_code);
      }
      await page.setViewportSize({ width: 390, height: 844 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect((await page.locator("body").innerText()).includes(code), "Access code must stay absent from rendered text").toBe(false);
      expect(await page.getByLabel("Deployment access code", { exact: true }).inputValue()).toBe("");
      expect(unsafeBrowserRequest, "Browser must only read evidence without putting credentials in URLs").toBe(false);

      const budgetResponse = await apiGet("/api/budget", code);
      expect(budgetResponse.status).toBe(200);
      const budget = await safeJson<Record<string, number>>(budgetResponse, code);
      for (const field of ["accounted_cost_usd", "input_tokens", "output_tokens", "cache_hits", "calls"]) {
        expect(budget[field], `Isolated judge ${field} must remain zero`).toBe(0);
      }
    });
  });
}
