import { test, expect } from "@playwright/test";
 
const TORN_PATH = "tests/fixtures/audio/Torn_no_drums.mp3";

test("v3 audio: upload Torn -> analyze/sectionize -> generate produces diagnostic metrics", async ({ page }) => {
  test.setTimeout(600_000);

  await page.goto("/v3?e2e=1");

  // Ensure audio mode
  await page.getByTestId("v3.workflow.audio").check();

  // Upload file
  const fileInput = page.locator('input[type="file"][accept="audio/*"]').first();
  await expect(fileInput).toBeAttached();
  await fileInput.setInputFiles(TORN_PATH);

  // Wait until we have a file key in diagnostics
  await page.waitForFunction(() => typeof (window as any).__dtk_getDiagnosticsSnapshot === "function");
  await page.waitForFunction(() => {
    const snap = (window as any).__dtk_getDiagnosticsSnapshot?.();
    return !!snap?.importState?.fileKey;
  }, null, { timeout: 180_000 });

  // Analyze tempo (required in many flows)
  const analyzeBtn = page.getByRole("button", { name: /Analyze tempo/i });
  await expect(analyzeBtn).toBeVisible({ timeout: 60_000 });
  await expect(analyzeBtn).toBeEnabled({ timeout: 180_000 });
  await analyzeBtn.click();

  // Sectionize
  const sectionizeBtn = page.getByRole("button", { name: /^Sectionize$/i });
  let sectionizeSummary: any = null;
  await expect(sectionizeBtn).toBeVisible({ timeout: 60_000 });
  await expect(sectionizeBtn).toBeEnabled({ timeout: 240_000 });
  const respPromise = page.waitForResponse(
    (r) => r.url().includes("/api/sectionize_smart") && r.request().method() === "POST",
    { timeout: 240_000 }
  );
  await sectionizeBtn.click();

  const resp = await respPromise;
  const bodyText = await resp.text().catch(() => "");
  if (!resp.ok()) {
    const snap = await page.evaluate(() => (window as any).__dtk_getDiagnosticsSnapshot?.());
    const summary = {
      status: resp.status(),
      body: bodyText.slice(0, 800),
      busyStage: snap?.importState?.busyStage,
      error: snap?.importState?.error,
      sectionsLen: Array.isArray(snap?.arrangement?.sections) ? snap.arrangement.sections.length : null,
    };
    throw new Error(`sectionize failed: ${JSON.stringify(summary)}`);
  }
  try {
    const json = JSON.parse(bodyText || "{}");
    const secs = (json as any)?.sections;
    sectionizeSummary = {
      responseSectionsLen: Array.isArray(secs) ? secs.length : null,
      first: Array.isArray(secs) && secs.length ? secs[0] : null,
    };
    if (!Array.isArray(secs) || secs.length === 0) {
      const snap = await page.evaluate(() => (window as any).__dtk_getDiagnosticsSnapshot?.());
      const summary = {
        body: bodyText.slice(0, 800),
        busyStage: snap?.importState?.busyStage,
        error: snap?.importState?.error,
        sectionsLen: Array.isArray(snap?.arrangement?.sections) ? snap.arrangement.sections.length : null,
      };
      throw new Error(`sectionize returned 0 sections; ${JSON.stringify(summary)}`);
    }
  } catch {
    // If response isn't JSON, let the later store wait fail with UI error surfaced.
  }

  // Wait for sectionize to settle, then either sections appear or an error is surfaced.
  await page.waitForFunction(() => {
    const snap = (window as any).__dtk_getDiagnosticsSnapshot?.();
    return snap?.importState?.busyStage === "idle";
  }, null, { timeout: 240_000 });

  const sectionSnap = await page.evaluate(() => (window as any).__dtk_getDiagnosticsSnapshot?.());
  const secs = sectionSnap?.arrangement?.sections;
  const err = sectionSnap?.importState?.error;
  const storeSummary = {
    busyStage: sectionSnap?.importState?.busyStage,
    error: err,
    sectionsLen: Array.isArray(secs) ? secs.length : null,
  };
  if (err) {
    throw new Error(`sectionize UI error: ${JSON.stringify({ storeSummary, sectionizeSummary })}`);
  }
  if (!Array.isArray(secs) || secs.length === 0) {
    throw new Error(`sectionize finished but sections still empty: ${JSON.stringify({ storeSummary, sectionizeSummary })}`);
  }

  // Select drummer (required)
  const inspectorGlobalBtn = page.getByRole("button", { name: /^Global$/ }).first();
  if (await inspectorGlobalBtn.isVisible().catch(() => false)) {
    await inspectorGlobalBtn.click();
  }

  const changeDrummerBtn = page.locator('button:has-text("Change Drummer")').first();
  await expect(changeDrummerBtn).toBeVisible({ timeout: 60_000 });
  await changeDrummerBtn.click();

  const modal = page.getByTestId("v3.drummerPicker");
  await expect(modal).toBeVisible({ timeout: 60_000 });

  const firstSelect = modal.getByRole("button", { name: /^Select$/ }).first();
  await expect(firstSelect).toBeVisible({ timeout: 60_000 });
  await firstSelect.click();

  // Generate
  const generateBtn = page.getByTestId("v3.generate");
  await expect(generateBtn).toBeVisible({ timeout: 30_000 });
  await generateBtn.click();

  // Wait for notes metrics
  await page.waitForFunction(() => {
    const snap = (window as any).__dtk_getDiagnosticsSnapshot?.();
    return !!snap?.metrics && typeof snap.metrics.notesCount === "number" && snap.metrics.notesCount > 0;
  }, null, { timeout: 240_000 });

  const snap = await page.evaluate(() => (window as any).__dtk_getDiagnosticsSnapshot());
  expect(snap.workflowMode).toBe("audio");
  expect(Array.isArray(snap.arrangement?.sections)).toBeTruthy();
  expect(snap.metrics.notesCount).toBeGreaterThan(0);
});
