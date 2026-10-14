import { expect, test } from "@playwright/test";


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
