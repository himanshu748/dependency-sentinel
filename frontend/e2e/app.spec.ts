import { expect, test } from "@playwright/test";

test("renders the maintenance contract and persists theme", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dependency Sentinel" })).toBeVisible();
  await expect(page.getByText("No maintenance run yet")).toBeVisible();
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
