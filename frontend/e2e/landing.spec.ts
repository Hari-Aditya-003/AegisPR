import { expect, test } from "@playwright/test";

test("visitor can explore example outcomes and test code with the keyboard", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Interactive example · not a live review")).toBeVisible();
  const safeChange = page.getByRole("button", { name: "Safe change", exact: true });
  await safeChange.focus();
  await page.keyboard.press("Enter");
  await expect(safeChange).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("VERIFIED WITHIN SCOPE", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Verified repair", exact: true }).click();
  await expect(page.getByText("FIX VERIFIED", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Show test code", exact: true }).click();
  await expect(page.getByText(/def test_discount_boundary/)).toBeVisible();
  await page.getByRole("button", { name: "Show evidence", exact: true }).click();
  await expect(page.getByText("FIX VERIFIED", { exact: true })).toBeVisible();
});

test("branded mobile page fits the viewport and respects reduced motion", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const logo = page.getByAltText("AegisPR shield and branching circuit logo");
  await expect(logo).toBeVisible();
  expect(await logo.evaluate((node) => (node as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  expect(await logo.evaluate((node) => getComputedStyle(node).animationName)).toBe("none");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByLabel(/github pull request/i)).toBeVisible();
});


test("visitor can understand and start the verification flow", async ({ page }) => {
  await page.route("http://localhost:8000/api/verifications", async (route) => {
    await route.fulfill({ status: 202, contentType: "application/json", body: JSON.stringify({ id: "run-e2e" }) });
  });
  await page.route("http://localhost:8000/api/verifications/run-e2e", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "run-e2e",
        pull_request_url: "https://github.com/acme/store/pull/42",
        status: "VERIFIED_WITHIN_SCOPE",
        model_used: "nvidia/nemotron",
        summary: {
          owner: "acme", repository: "store", number: 42, title: "Coupon boundary verification",
          base_commit: "a".repeat(40), head_commit: "b".repeat(40), changed_files: 1, additions: 4, deletions: 1,
        },
        stages: [{ key: "report", label: "Evidence report completed", state: "complete", detail: "Stored" }],
        findings: [], changed_files: ["coupon.py"], hypotheses: [],
        metrics: { files_analyzed: 3, hypotheses_generated: 0, generated_tests: 0, regressions_found: 0, model_calls: 1, context_accelerator: "cuda", analysis_duration_ms: 1, sandbox_duration_ms: 1 },
        disclaimer: "Evidence is scoped to the checks executed in this run.",
      }),
    });
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /don't trust a pr/i })).toBeVisible();
  await page.getByLabel(/github pull request/i).fill("https://github.com/acme/store/pull/42");
  await page.getByRole("button", { name: /verify pr/i }).click();
  await expect(page).toHaveURL(/\/verifications\/run-e2e/);
  await expect(page.getByRole("heading", { name: "Coupon boundary verification" })).toBeVisible();
  await expect(page.getByText("VERIFIED WITHIN TESTED SCOPE")).toBeVisible();
});


test("visitor receives validation feedback for a non-GitHub URL", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/github pull request/i).fill("https://example.com/pull/42");
  await page.getByRole("button", { name: /verify pr/i }).click();
  await expect(page.locator("#pr-error")).toContainText("public GitHub pull request");
});


test("reviewer can generate and verify an isolated repair", async ({ page }) => {
  let repairStarted = false;
  const regression = {
    id: "run-repair",
    pull_request_url: "https://github.com/acme/store/pull/42",
    status: "REGRESSION_FOUND",
    summary: {
      owner: "acme", repository: "store", number: 42, title: "Coupon repair",
      base_commit: "a".repeat(40), head_commit: "b".repeat(40), changed_files: 1, additions: 4, deletions: 1,
    },
    stages: [{ key: "report", label: "Evidence report completed", state: "complete", detail: "Stored" }],
    findings: [{
      id: "finding-1", classification: "REGRESSION", severity: "high", summary: "Negative total",
      affected_file: "coupon.py", root_cause: "The result is not clamped.",
      base_execution: { branch: "base", commit: "a".repeat(40), status: "PASSED", stdout: "", stderr: "", duration_ms: 4 },
      head_execution: { branch: "head", commit: "b".repeat(40), status: "FAILED", stdout: "", stderr: "", duration_ms: 5 },
    }],
    changed_files: ["coupon.py"],
    hypotheses: [{ id: "H1", description: "Negative total", test_strategy: "Oversized discount" }],
    metrics: { files_analyzed: 3, hypotheses_generated: 1, generated_tests: 1, regressions_found: 1, context_accelerator: "cuda" },
    disclaimer: "Evidence is scoped to executed checks.",
  };
  await page.route("http://localhost:8000/api/verifications/run-repair/repair", async (route) => {
    repairStarted = true;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ ...regression, status: "RUNNING", repair: { finding_id: "finding-1", status: "PENDING", patch: "", summary: "", checks: [] } }),
    });
  });
  await page.route("http://localhost:8000/api/verifications/run-repair", async (route) => {
    const body = repairStarted ? {
      ...regression,
      status: "FIX_VERIFIED",
      repair: {
        finding_id: "finding-1", status: "VERIFIED",
        patch: "diff --git a/coupon.py b/coupon.py", summary: "Clamp the result at zero.",
        checks: [{ name: "existing_tests", command: "pytest -q", execution: { branch: "repair", commit: "b".repeat(40), status: "PASSED", stdout: "", stderr: "", duration_ms: 8 } }],
      },
    } : regression;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/verifications/run-repair");
  await page.getByRole("button", { name: /generate and verify repair/i }).click();
  await expect(page.getByText("Clamp the result at zero.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Repair evidence" })).toBeVisible();
  await expect(page.getByText("View isolated patch")).toBeVisible();
});
