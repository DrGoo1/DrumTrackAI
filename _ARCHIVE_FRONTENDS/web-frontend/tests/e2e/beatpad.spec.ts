import { test, expect } from "@playwright/test";

/**
 * BeatPad regression: ensures the neon pads capture tap hits,
 * update the hit counter, and enable translation without requiring backend calls.
 */
test("beat pad capture enables translation", async ({ page }) => {
  await page.goto("/beat-sketch");

  await expect(page.getByRole("heading", { name: /Sketch a Beat/i })).toBeVisible();

  const padToggle = page.getByRole("button", { name: /Beat Pads/i });
  await padToggle.click();

  await expect(page.getByText("Tap the neon pads", { exact: false })).toBeVisible();

  const translateButton = page.getByRole("button", { name: /Translate Pad Groove/i });
  await expect(translateButton).toBeDisabled();

  const kickPad = page.getByRole("button", { name: /Kick/i }).first();
  await kickPad.click();

  await expect(page.getByText(/Hits:\s*1/)).toBeVisible();
  await expect(page.getByText(/kick:\s*1/i)).toBeVisible();
  await expect(translateButton).toBeEnabled();
});
