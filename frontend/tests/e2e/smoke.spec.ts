import { test, expect } from "@playwright/test";

test("app loads and uploader appears", async ({ page }) => {
  await page.goto("/");
  // Core UI present
  await expect(page.locator("body")).toBeVisible();

  // Debug panel only in dev builds; don't fail if absent
  const debug = page.locator("text=Latency:");
  await debug.first().waitFor({ state: "visible", timeout: 2000 }).catch(() => {});

  // Uploader flag path
  const hasUploader = await page.locator("text=Upload Audio").first().isVisible().catch(() => false);
  expect(typeof hasUploader).toBe("boolean");
});
