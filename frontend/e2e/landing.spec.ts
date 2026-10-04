import { expect, test } from "@playwright/test";


test("visitor can understand and start the verification flow", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /don't trust a pr/i })).toBeVisible();
  await page.getByLabel(/github pull request/i).fill("https://github.com/acme/store/pull/42");
  await page.getByRole("button", { name: /verify pr/i }).click();
  await expect(page).toHaveURL(/\/verifications\//);
});

