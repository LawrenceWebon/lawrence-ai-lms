import { expect, test } from "@playwright/test";

test("Step 0 exposes only the inert foundation page", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "AI LMS engineering foundation" })).toBeVisible();
  await expect(page.getByRole("button")).toHaveCount(0);
});
