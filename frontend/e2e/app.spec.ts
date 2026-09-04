import { expect, test } from "@playwright/test";

test("renders the landing page, reaches the demo and persists theme", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "Dependency Sentinel" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /One upgrade\. Full evidence/ })).toBeVisible();

  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

  await page.getByRole("button", { name: "Try the demo" }).first().click();
  await expect(page.getByText("No maintenance run yet")).toBeVisible();
  await expect(page.getByRole("button", { name: "Scan repository" })).toBeEnabled();

  await page.getByRole("button", { name: "Back to overview" }).click();
  await expect(page.getByRole("heading", { name: /One upgrade\. Full evidence/ })).toBeVisible();
});

test("landing page has no horizontal overflow at 390, 768 and 1440", async ({ page }) => {
  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(0);
  }
});
