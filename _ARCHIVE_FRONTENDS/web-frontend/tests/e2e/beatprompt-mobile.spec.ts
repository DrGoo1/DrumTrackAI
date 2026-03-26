import { test, expect, devices } from "@playwright/test";

const iPhone = devices["iPhone 13 Pro"];

const mockResponse = {
  success: true,
  job_id: "beatprompt_mock",
  tempo: 170,
  hits: [
    { instrument: "kick", beat_position: 0, time: 0, velocity: 120, confidence: 0.98 },
    { instrument: "snare", beat_position: 1, time: 0.35, velocity: 115, confidence: 0.95 },
    { instrument: "kick", beat_position: 2, time: 0.7, velocity: 118, confidence: 0.96 },
    { instrument: "snare", beat_position: 3, time: 1.05, velocity: 117, confidence: 0.94 },
  ],
  summary: { kick: 2, snare: 2 },
  preview_midi: "TVRoZAAAAAYAAQABANBNVHJrAA==",
  plugin: "jamstix",
  ticks_per_beat: 480,
  persona_id: "arena_rock_captain",
  style_pack: "pop_punk_energy",
  sections: [
    {
      label: "Chorus",
      bars: 8,
      tempo: 170,
      meter: "4/4",
      persona_id: "arena_rock_captain",
      style_pack: "pop_punk_energy",
      pattern_template: "chorus_pop_punk",
      modifiers: ["doubletime hats"],
      confidence: 0.9,
    },
  ],
  warnings: [],
};

test.describe("BeatPrompt mobile storyline", () => {
  test.use({
    viewport: iPhone.viewport,
    userAgent: iPhone.userAgent,
    deviceScaleFactor: iPhone.deviceScaleFactor,
    hasTouch: iPhone.hasTouch,
    isMobile: iPhone.isMobile,
  });

  test("mobile prompt flow renders guidance and consumes stubbed result", async ({ page }) => {
    await page.route("**/api/beatprompt/render", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(mockResponse),
      });
    });

    await page.goto("/beat-prompt");

    await expect(page.getByRole("heading", { name: /Type a vibe/i })).toBeVisible();
    await expect(page.getByText(/Mobile tip/i)).toBeVisible();

    const textarea = page.getByLabel(/Describe the groove/i);
    await textarea.fill("Pop punk chorus with doubletime hats");

    const generateButton = page.getByRole("button", { name: /Generate Groove/i });
    await expect(generateButton).toBeEnabled();
    await generateButton.click();

    await expect(page.getByRole("button", { name: /Generating Groove/i })).toBeVisible({ timeout: 2000 });
    await expect(page.getByRole("button", { name: /Generate Groove/i })).toBeVisible();

    await expect(page.getByText(/Tempo: 170\.0 BPM/i)).toBeVisible();
    await expect(page.getByText(/Hits generated: 4/i)).toBeVisible();
    await expect(page.getByText(/doubletime hats/i)).toBeVisible();
  });
});