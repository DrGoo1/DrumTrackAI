import { test, expect } from "@playwright/test";

// End-to-end regression: ensure that generating drums for a section and for the
// full song results in MIDI notes being applied into the DAW drum editor.
//
// Preconditions (manual for now):
// - Backend server running and reachable at API_BASE from web-frontend
// - web-frontend dev server running at E2E_BASE_URL or http://localhost:5173
// - Audio file available at F:\\Audio_Test_Files\\Torn_no_drums.mp3

const AUDIO_PATH = "F:/Audio_Test_Files/Torn_no_drums.mp3";

async function uploadSourceSong(page: any) {
  await page.goto("/");

  // Click the Source Song drop zone to open the file picker
  const dropZone = page.getByText("Click or drop an audio file (no drums)");
  await expect(dropZone).toBeVisible();

  // The hidden input[type=file] lives inside SourceSongPanel
  const fileInput = page.locator('input[type="file"][accept="audio/*"]').first();
  await fileInput.setInputFiles(AUDIO_PATH);

  // Validate the expected backend calls happened and succeeded.
  const uploadResp = await page.waitForResponse((r: any) =>
    r.url().includes("/api/upload") && r.request().method() === "POST"
  );
  const uploadJson = await uploadResp.json().catch(() => ({}));
  expect(uploadJson.success).toBeTruthy();

  const analyzeResp = await page.waitForResponse((r: any) =>
    r.url().includes("/api/analyze") && r.request().method() === "POST"
  );
  const analyzeJson = await analyzeResp.json().catch(() => ({}));
  expect(analyzeJson.success).toBeTruthy();

  // getResults is a GET on /api/results/<job_id>
  await page.waitForResponse((r: any) =>
    r.url().includes("/api/results/") && r.request().method() === "GET"
  );

  // Wait for upload/analyze lifecycle to complete.
  // SourceSongPanel shows "Uploading & analyzing…" while busy and then
  // replaces it with the uploaded filename.
  const busyText = page.getByText(/Uploading\s*&\s*analyzing/i);
  await busyText.waitFor({ state: "visible", timeout: 10_000 }).catch(() => {});
  await busyText.waitFor({ state: "hidden", timeout: 180_000 }).catch(() => {});

  // If upload failed, surface UI error for debugging.
  const err = page.locator("text=Error:");
  if (await err.isVisible().catch(() => false)) {
    const msg = await err.textContent();
    throw new Error(msg || "Upload failed");
  }

  // Wait until the filename appears in the SourceSongPanel drop zone
  await expect(dropZone).toContainText("Torn_no_drums.mp3", { timeout: 180_000 });
}

async function autoSectionize(page: any) {
  const autoButton = page.getByRole("button", { name: /Auto Sectionize/i });
  await autoButton.click();

  // Wait for at least one section row to appear (Arrangement Sections list)
  const sectionRow = page.getByText("Fill In").first();
  await expect(sectionRow).toBeVisible({ timeout: 60_000 });
}

async function waitForGenerateDrumsResponse(page: any) {
  const resp = await page.waitForResponse((r: any) =>
    r.url().includes("/api/generate-drums") && r.request().method() === "POST"
  );
  const json = await resp.json();
  expect(json.ok).toBeTruthy();
  expect(Array.isArray(json.drum_track?.notes)).toBeTruthy();
  expect(json.drum_track.notes.length).toBeGreaterThan(0);
  return json;
}

async function expectMidiNotesInEditor(page: any) {
  // DrumEditorPanel/LimbBarEditor ultimately writes MIDI notes into the
  // DAW midi store and renders them; here we use a coarse DOM heuristic
  // that at least one note rectangle is present.
  //
  // If selectors change, this assertion can be updated to a more specific
  // data-testid-based check.
  const limbViewToggle = page.getByRole("combobox", { name: /View/i });
  await expect(limbViewToggle).toBeVisible();

  // First check Limb View
  await limbViewToggle.selectOption("limb");
  const limbNotes = page.locator("[class*='LimbBar'] div");
  const limbCount = await limbNotes.count();

  // Then check Piano Roll view as a fallback signal
  await limbViewToggle.selectOption("piano");
  const pianoNotes = page.locator("[class*='note']");
  const pianoCount = await pianoNotes.count();

  expect(limbCount + pianoCount).toBeGreaterThan(0);
}

test.describe("Drum track generation populates DAW editors", () => {
  test.setTimeout(240_000);
  test("Generate drums for selected sections and full song populates MIDI notes", async ({ page }) => {
    await uploadSourceSong(page);
    await autoSectionize(page);

    // Ensure Drum Creation panel is visible and scope is "selected_section" first
    const scopeSelect = page.getByRole("combobox", { name: /Scope/i });
    // Scope selector only appears in Advanced mode; if it's not there, switch modes
    if (!(await scopeSelect.isVisible().catch(() => false))) {
      const basicButton = page.getByRole("button", { name: /Basic/i });
      const advancedButton = page.getByRole("button", { name: /Advanced/i });
      await advancedButton.click();
      await expect(scopeSelect).toBeVisible();
    }

    await scopeSelect.selectOption("selected_section");

    const generateButton = page.getByRole("button", { name: /Generate Drum Track/i });
    await expect(generateButton).toBeEnabled();

    // 1) Generate for selected section
    await generateButton.click();
    const jsonSection = await waitForGenerateDrumsResponse(page);
    await expectMidiNotesInEditor(page);

    // 2) Generate for full song (toggle scope and regenerate)
    await scopeSelect.selectOption("full_song");
    await generateButton.click();
    const jsonSong = await waitForGenerateDrumsResponse(page);

    // Sanity: full song should have at least as many notes as section
    expect(jsonSong.drum_track.notes.length).toBeGreaterThanOrEqual(
      jsonSection.drum_track.notes.length
    );

    await expectMidiNotesInEditor(page);
  });
});
