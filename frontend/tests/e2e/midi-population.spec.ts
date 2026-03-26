import { test, expect } from "@playwright/test";

const AUDIO_PATH: string =
  (globalThis as any)?.process?.env?.E2E_AUDIO_PATH ||
  "F:\\DrumTracKAI_v1.1.17\\admin\\data\\drummer_songs\\jeff_porcaro_Rosanna.mp3";

async function waitForDtkState(page: any) {
  await page.waitForFunction(() => typeof (window as any).__DTK_STATE__ === "object");
}

async function ensureLegacyDrummerSelected(page: any) {
  const hasSelected = await page
    .evaluate(() => {
      const s = (window as any).__DTK_STATE__;
      const selected = s?.selectedDrummer || s?.drummer || null;
      const id = (selected && typeof selected === 'object' ? (selected as any).id : null) || s?.drummerId || null;
      if (typeof id === 'string' && id.length > 0) {
        return id !== 'default_neutral';
      }
      return Boolean(s?.selectedDrummer || s?.drummer || s?.drummerId || s?.drummerName);
    })
    .catch(() => false);

  // If no drummer is selected yet, proactively open the modal via the UI control.
  if (!hasSelected) {
    const changeBtn = page.getByRole('button', { name: /change drummer/i }).first();
    if (await changeBtn.isVisible().catch(() => false)) {
      await changeBtn.click().catch(() => {});
    }
  }

  const modalTitle = page.getByText(/Choose Your Drummer!/i).first();
  if (!(await modalTitle.isVisible().catch(() => false))) {
    return;
  }

  const modal = page
    .locator('div.fixed.inset-0.z-\\[10000\\]')
    .filter({ hasText: 'Choose Your Drummer!' })
    .first();
  await expect(modal).toBeVisible({ timeout: 60_000 });

  const preferredCard = modal.locator('.drummer-card[data-drummer-id="rock_powerhouse"]').first();
  const preferredCard2 = modal.locator('.drummer-card[data-drummer-id="studio_groove_master"]').first();
  const nonDefaultCard = modal
    .locator('.drummer-card[data-drummer-id]:not([data-drummer-id="default_neutral"])')
    .first();
  const fallbackCard = modal.locator('.drummer-card').first();

  const cardToClick = (await preferredCard.isVisible().catch(() => false))
    ? preferredCard
    : (await preferredCard2.isVisible().catch(() => false))
      ? preferredCard2
      : (await nonDefaultCard.isVisible().catch(() => false))
        ? nonDefaultCard
        : fallbackCard;
  await expect(cardToClick).toBeVisible({ timeout: 60_000 });
  await cardToClick.click({ force: true });

  await expect(modalTitle).toBeHidden({ timeout: 60_000 });
}

async function ensureLegacyTimeSignature4_4(page: any) {
  const timeSigSelect = page
    .getByText(/Time Signature/i)
    .locator('..')
    .locator('select')
    .first();
  if (await timeSigSelect.isVisible().catch(() => false)) {
    await timeSigSelect.selectOption({ label: '4/4' }).catch(() => {});
  }

  // Also force beats/bar spinner when present (payload timeSignature is derived from this in legacy flows).
  const beatsSpin = page
    .getByText(/Beats\s*\/\s*Bar/i)
    .locator('..')
    .locator('input[type="number"], input')
    .first();
  if (await beatsSpin.isVisible().catch(() => false)) {
    await beatsSpin.fill('4').catch(() => {});
    await beatsSpin.dispatchEvent('input').catch(() => {});
    await beatsSpin.dispatchEvent('change').catch(() => {});
  }

  const beatUnitSelect = page
    .getByText(/Beat Unit/i)
    .locator('..')
    .locator('select')
    .first();
  if (await beatUnitSelect.isVisible().catch(() => false)) {
    await beatUnitSelect.selectOption({ label: '4' }).catch(() => {});
  }

  await page
    .waitForFunction(
      () => {
        const s = (window as any).__DTK_STATE__;
        const ts = (s?.timeSignature || s?.time_signature) as any;
        if (!ts) return true;
        if (Array.isArray(ts) && ts.length >= 2) {
          return Number(ts[0]) === 4 && Number(ts[1]) === 4;
        }
        return true;
      },
      null,
      { timeout: 5_000 },
    )
    .catch(() => {});
}

async function ensureLegacyRudimentFamilySnare(page: any) {
  const snareBtn = page.getByRole('button', { name: /^Snare rudiments$/i }).first();
  if (await snareBtn.isVisible().catch(() => false)) {
    await snareBtn.click({ timeout: 10_000 }).catch(() => {});
  }
}

async function assertLegacyHasNotesOrTracks(page: any, label: string) {
  const ok = await page
    .evaluate(() => {
      const s = (window as any).__DTK_STATE__;
      if (!s) return false;
      if (typeof s.notesCount === 'number' && s.notesCount > 0) return true;
      if (Array.isArray(s.sectionTrackKeys) && s.sectionTrackKeys.length > 0) return true;
      if (s.sectionDrumTracks && typeof s.sectionDrumTracks === 'object' && Object.keys(s.sectionDrumTracks).length > 0)
        return true;
      return false;
    })
    .catch(() => false);

  if (!ok) {
    const snapshot = await page.evaluate(() => (window as any).__DTK_STATE__).catch(() => undefined);
    throw new Error(`${label}: expected notes/tracks after generation but found none; __DTK_STATE__=${JSON.stringify(snapshot)}`);
  }
}

async function ensureLegacyGrooveSourceEgmdPhrases(page: any) {
  const labeledContainer = page
    .getByText(/^Groove Source$/i)
    .locator('..')
    .first();
  const labeledSelect = labeledContainer.locator('select').first();

  const anyGrooveSelect = page
    .locator('select')
    .filter({ has: page.locator('option', { hasText: /^Built-in$/i }) })
    .filter({ has: page.locator('option', { hasText: /^E-GMD Phrases$/i }) })
    .first();

  const combo = (await labeledSelect.isVisible().catch(() => false)) ? labeledSelect : anyGrooveSelect;
  if (!(await combo.isVisible().catch(() => false))) return;

  await expect(combo).toBeVisible({ timeout: 60_000 });
  await combo.selectOption({ label: 'E-GMD Phrases' }).catch(async () => {
    await combo.selectOption({ value: 'egmd_phrases' });
  });
}

async function ensureLegacyGrooveSourceBuiltIn(page: any) {
  // Anchor on the actual UI label to avoid selecting the wrong <select> elsewhere in the page.
  const labeledContainer = page
    .getByText(/^Groove Source$/i)
    .locator('..')
    .first();
  const labeledSelect = labeledContainer.locator('select').first();

  // Fallback: any select that has both Built-in and E-GMD Phrases options.
  const anyGrooveSelect = page
    .locator('select')
    .filter({ has: page.locator('option', { hasText: /^Built-in$/i }) })
    .filter({ has: page.locator('option', { hasText: /^E-GMD Phrases$/i }) })
    .first();

  const combo = (await labeledSelect.isVisible().catch(() => false)) ? labeledSelect : anyGrooveSelect;
  if (!(await combo.isVisible().catch(() => false))) return;

  await expect(combo).toBeVisible({ timeout: 60_000 });

  // Prefer DOM-set + event dispatch to guarantee React onChange fires in the legacy UI.
  // Also update *all* Groove Source-like selects (there may be duplicates/hidden ones).
  await page.evaluate((el: any) => {
    const setBuiltIn = (select: HTMLSelectElement) => {
      const opts = Array.from(select.options);
      const builtInOpt =
        opts.find((o) => /^Built-in$/i.test((o.textContent || '').trim())) ||
        opts.find((o) => /Built/i.test((o.textContent || '').trim())) ||
        opts.find((o) => o.value === 'pattern');
      if (!builtInOpt) return false;
      select.value = builtInOpt.value;
      select.dispatchEvent(new Event('input', { bubbles: true }));
      select.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    };

    const target = el as HTMLSelectElement | null;
    if (target) setBuiltIn(target);

    const all = Array.from(document.querySelectorAll('select')) as HTMLSelectElement[];
    for (const s of all) {
      const hasEgmd = Array.from(s.options).some((o) => /E-GMD Phrases/i.test(o.textContent || ''));
      const hasBuiltIn = Array.from(s.options).some((o) => /Built-in/i.test(o.textContent || ''));
      if (hasEgmd && hasBuiltIn) setBuiltIn(s);
    }
  }, await combo.elementHandle());

  // Verify the UI selection actually stuck.
  await page.waitForFunction(
    () => {
      const selects = Array.from(document.querySelectorAll('select')) as HTMLSelectElement[];
      const groove = selects.find((s) => Array.from(s.options).some((o) => /E-GMD Phrases/i.test(o.textContent || '')));
      if (!groove) return true;
      const selected = groove.options[groove.selectedIndex]?.textContent || '';
      return /Built-in/i.test(selected);
    },
    null,
    { timeout: 30_000 },
  );

  // If legacy state exposes grooveSource, verify it too (this catches cases where the UI lies).
  await page
    .waitForFunction(
      () => {
        const s = (window as any).__DTK_STATE__;
        if (!s || typeof s !== 'object') return true;
        if (typeof s.grooveSource !== 'string') return true;
        return s.grooveSource === 'pattern';
      },
      null,
      { timeout: 10_000 },
    )
    .catch(() => {});
}

async function waitForLegacyGenerationToPopulate(page: any, label: string) {
  try {
    await page.waitForFunction(() => {
      const s = (window as any).__DTK_STATE__;
      if (!s) return false;
      // In the legacy UI, errors are rendered via a separate React state (not always mirrored into __DTK_STATE__).
      if (typeof document !== 'undefined') {
        const bodyText = document.body?.innerText || '';
        if (/Drum generation failed/i.test(bodyText)) return true;
      }
      if (typeof s.error === 'string' && s.error.length > 0) return true;
      if (typeof s.notesCount === 'number' && s.notesCount > 0) return true;
      if (Array.isArray(s.sectionTrackKeys) && s.sectionTrackKeys.length > 0) return true;
      if (s.sectionDrumTracks && typeof s.sectionDrumTracks === 'object' && Object.keys(s.sectionDrumTracks).length > 0)
        return true;
      return false;
    }, null, { timeout: 120_000 });
  } catch {
    const snapshot = await page.evaluate(() => (window as any).__DTK_STATE__);
    throw new Error(
      `${label}: generation did not populate (notesCount/sectionTrackKeys/sectionDrumTracks); __DTK_STATE__=${JSON.stringify(
        snapshot,
      )}`,
    );
  }

  const snapshot = await page.evaluate(() => (window as any).__DTK_STATE__);
  // If the UI is showing an error banner, fail immediately with a helpful message.
  const hasUiError = await page
    .evaluate(() => /Drum generation failed/i.test(document.body?.innerText || ''))
    .catch(() => false);
  if (hasUiError) {
    const req = await page.evaluate(() => (window as any).__E2E_LAST_GENERATE_REQ__).catch(() => undefined);
    throw new Error(
      `${label}: UI shows drum generation failed; __DTK_STATE__=${JSON.stringify(snapshot)} __lastGenerateReq__=${JSON.stringify(
        req,
      )}`,
    );
  }
  if (snapshot?.error) {
    const req = await page.evaluate(() => (window as any).__E2E_LAST_GENERATE_REQ__).catch(() => undefined);
    throw new Error(
      `${label}: app error after generation; __DTK_STATE__=${JSON.stringify(snapshot)} __lastGenerateReq__=${JSON.stringify(req)}`,
    );
  }
}

async function runLegacyGenerateAndAssertOk(page: any, button: any, label: string) {
  const clickGenerate = async () => {
    await button.scrollIntoViewIfNeeded().catch(() => {});
    // Legacy UI often wires generation on onMouseDown.
    await button.dispatchEvent('mousedown').catch(() => {});
    await button.dispatchEvent('mouseup').catch(() => {});
    await button.dispatchEvent('click').catch(() => {});
    await button.click({ force: true }).catch(() => {});
  };

  // Ensure preconditions BEFORE clicking, otherwise the first click can trigger a failing generation.
  await ensureLegacyDrummerSelected(page);
  await ensureLegacyTimeSignature4_4(page);
  await ensureLegacyGrooveSourceBuiltIn(page);
  await ensureLegacyRudimentFamilySnare(page);

  const attemptGenerate = async () => {
    const reqPromise = page.waitForRequest(
      (r: any) => r.url().includes('/api/generate-drums') && r.method() === 'POST',
      { timeout: 45_000 },
    );
    const respPromise = page.waitForResponse(
      (r: any) => r.url().includes('/api/generate-drums') && r.request().method() === 'POST',
      { timeout: 180_000 },
    );

    await clickGenerate();

    return { reqPromise, respPromise };
  };

  let reqPromise: any;
  let respPromise: any;
  ({ reqPromise, respPromise } = await attemptGenerate());

  // If the request wasn't emitted, it's likely gating (drummer modal). Handle and retry once.
  try {
    await reqPromise;
  } catch {
    await respPromise.catch(() => {});
    await ensureLegacyDrummerSelected(page);
    await ensureLegacyTimeSignature4_4(page);
    await ensureLegacyGrooveSourceBuiltIn(page);
    await ensureLegacyRudimentFamilySnare(page);
    ({ reqPromise, respPromise } = await attemptGenerate());
    await reqPromise;
  }

  // Capture request payload as soon as the request exists (before waiting on response/body).
  const reqPayload = await reqPromise
    .then((r: any) => {
      const postData = r.postData();
      let parsed: any = undefined;
      try {
        parsed = postData ? JSON.parse(postData) : undefined;
      } catch {
        parsed = postData;
      }
      return parsed;
    })
    .catch(() => undefined);
  await page
    .evaluate((payload: any) => {
      (window as any).__E2E_LAST_GENERATE_REQ__ = payload;
    }, reqPayload)
    .catch(() => {});

  const resp = await respPromise;
  if (!resp.ok()) {
    const body = await resp.text().catch(() => '');
    const snapshot = await page.evaluate(() => (window as any).__DTK_STATE__);
    const req = reqPayload;
    throw new Error(
      `${label}: /api/generate-drums failed: status=${resp.status()} body=${body.slice(0, 800)} __DTK_STATE__=${JSON.stringify(
        snapshot,
      )} __lastGenerateReq__=${JSON.stringify(req)}`,
    );
  }

  // Some backend failures return HTTP 200 with { ok: false, error: ... }.
  const text = await resp.text().catch(() => '');
  let json: any = undefined;
  try {
    json = text ? JSON.parse(text) : undefined;
  } catch {
    json = undefined;
  }
  await page
    .evaluate((payload: any) => {
      (window as any).__E2E_LAST_GENERATE_RESP__ = payload;
    }, json)
    .catch(() => {});
  if (json && (json.ok === false || typeof json.error === 'string' || typeof json.message === 'string')) {
    const snapshot = await page.evaluate(() => (window as any).__DTK_STATE__).catch(() => undefined);
    const req = await page.evaluate(() => (window as any).__E2E_LAST_GENERATE_REQ__).catch(() => reqPayload);
    throw new Error(
      `${label}: /api/generate-drums returned ok=false (HTTP 200). body=${JSON.stringify(json).slice(0, 1200)} __DTK_STATE__=${JSON.stringify(
        snapshot,
      )} __lastGenerateReq__=${JSON.stringify(req)}`,
    );
  }

  // Request payload already captured above.
}

test("upload → auto-sectionize → generate entire song populates notes", async ({ page }) => {
  test.setTimeout(600_000);
  await page.goto("/");

  const uploadReqDiagnostics: { failed?: string } = {};
  page.on("requestfailed", (req) => {
    if (req.url().includes("/api/upload") && req.method() === "POST") {
      uploadReqDiagnostics.failed = req.failure()?.errorText || "requestfailed";
    }
  });

  const uploadButton = page.getByRole("button", { name: /Upload Audio/i });
  await expect(uploadButton).toBeVisible({ timeout: 30_000 });

  const fileInput = page.locator('input[type="file"][accept="audio/*"]').first();
  await expect(fileInput).toBeAttached();

  await uploadButton.click().catch(() => {});

  const uploadReqPromise = page.waitForRequest((r) =>
    r.url().includes("/api/upload") && r.method() === "POST",
  );
  const uploadRespPromise = page.waitForResponse((r) =>
    r.url().includes("/api/upload") && r.request().method() === "POST",
    { timeout: 600_000 },
  );
  const analyzeRespPromise = page.waitForResponse((r) =>
    r.url().includes("/api/analyze") && r.request().method() === "POST",
    { timeout: 600_000 },
  );
  const resultsRespPromise = page.waitForResponse((r) =>
    r.url().includes("/api/results/") && r.request().method() === "GET",
    { timeout: 600_000 },
  );

  await fileInput.setInputFiles(AUDIO_PATH);

  await uploadReqPromise.catch(() => {
    throw new Error("/api/upload request was never sent after setting input files");
  });

  const uploadResp = await uploadRespPromise;
  if (uploadReqDiagnostics.failed) {
    throw new Error(`upload request failed: ${uploadReqDiagnostics.failed}`);
  }
  if (!uploadResp.ok()) {
    const body = await uploadResp.text().catch(() => "");
    throw new Error(`upload failed: ${uploadResp.status()} ${body.slice(0, 300)}`);
  }

  const analyzeResp = await analyzeRespPromise;
  if (!analyzeResp.ok()) {
    const body = await analyzeResp.text().catch(() => "");
    throw new Error(`analyze failed: ${analyzeResp.status()} ${body.slice(0, 300)}`);
  }

  const resultsResp = await resultsRespPromise;
  if (!resultsResp.ok()) {
    const body = await resultsResp.text().catch(() => "");
    throw new Error(`results failed: ${resultsResp.status()} ${body.slice(0, 300)}`);
  }

  await waitForDtkState(page);

  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return s && s.tracksCount > 0;
  }, null, { timeout: 180_000 });

  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return s && s.sectionsCount > 0;
  }, null, { timeout: 180_000 });

  const genEntireSong = page.getByRole("button", { name: /Generate Complete Song/i });
  await expect(genEntireSong).toBeVisible({ timeout: 60_000 });
  await expect(genEntireSong).toBeEnabled({ timeout: 60_000 });

  await ensureLegacyGrooveSourceBuiltIn(page);
  await ensureLegacyRudimentFamilySnare(page);
  await runLegacyGenerateAndAssertOk(page, genEntireSong, 'entire-song');

  await waitForLegacyGenerationToPopulate(page, "entire-song");

  await expect(page.getByText(/Drum Performance Editor/i)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole('button', { name: /^16th$/i })).toBeVisible({ timeout: 60_000 });
  await assertLegacyHasNotesOrTracks(page, 'entire-song');
});

test("upload → auto-sectionize → select section → generate drums populates grids", async ({ page }) => {
  test.setTimeout(600_000);
  await page.goto("/");

  page.on("dialog", async (dialog) => {
    await dialog.accept().catch(() => {});
  });

  const uploadButton = page.getByRole("button", { name: /Upload Audio/i });
  await expect(uploadButton).toBeVisible({ timeout: 30_000 });

  const fileInput = page.locator('input[type="file"][accept="audio/*"]').first();
  await expect(fileInput).toBeAttached();

  await uploadButton.click().catch(() => {});

  const uploadRespPromise = page.waitForResponse((r) =>
    r.url().includes("/api/upload") && r.request().method() === "POST",
    { timeout: 600_000 },
  );
  const analyzeRespPromise = page.waitForResponse((r) =>
    r.url().includes("/api/analyze") && r.request().method() === "POST",
    { timeout: 600_000 },
  );
  const resultsRespPromise = page.waitForResponse((r) =>
    r.url().includes("/api/results/") && r.request().method() === "GET",
    { timeout: 600_000 },
  );

  await fileInput.setInputFiles(AUDIO_PATH);
  const uploadResp = await uploadRespPromise;
  expect(uploadResp.ok()).toBeTruthy();
  const analyzeResp = await analyzeRespPromise;
  expect(analyzeResp.ok()).toBeTruthy();
  const resultsResp = await resultsRespPromise;
  expect(resultsResp.ok()).toBeTruthy();

  await waitForDtkState(page);

  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return s && s.tracksCount > 0 && s.sectionsCount > 0;
  }, null, { timeout: 180_000 });

  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return s && typeof s.sectionsCount === "number" && s.sectionsCount > 0;
  }, null, { timeout: 180_000 });

  await page.evaluate(() => {
    const state = (window as any).__DTK_STATE__;
    if (!state?.sectionsCount || state.sectionsCount < 1) {
      throw new Error("No sections available to select");
    }
  });

  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return s && Array.isArray(s.sections) && s.sections.length > 0 && typeof s.timelineDurationSec === "number";
  }, null, { timeout: 30_000 });

  // Timeline sections are drawn on a canvas; click the section header area at the midpoint of the first section.
  const canvas = page.locator("canvas.w-full.cursor-pointer").first();
  await expect(canvas).toBeVisible({ timeout: 30_000 });

  const { clickXRatio } = await page.evaluate(() => {
    const s = (window as any).__DTK_STATE__;
    const duration = Math.max(0.0001, Number(s?.timelineDurationSec ?? 0));
    const first = s?.sections?.[0];
    if (!first) {
      throw new Error("No sections in __DTK_STATE__");
    }
    const start = Math.max(0, Number(first.start ?? 0));
    const end = Math.max(start, Number(first.end ?? start));
    const startRatio = start / duration;
    const endRatio = end / duration;
    const midRatio = startRatio + (endRatio - startRatio) * 0.5;
    const ratio = Math.max(0.0005, Math.min(0.9995, midRatio));
    return { clickXRatio: ratio };
  });

  await page.evaluate((ratio) => {
    const el = document.querySelector<HTMLCanvasElement>("canvas.w-full.cursor-pointer");
    if (!el) return;
    const scrollContainer = el.closest<HTMLDivElement>(".overflow-x-auto");
    if (!scrollContainer) return;
    const targetX = el.clientWidth * ratio;
    const viewportWidth = scrollContainer.clientWidth;
    const maxScrollLeft = Math.max(0, el.clientWidth - viewportWidth);
    const desired = Math.max(0, Math.min(maxScrollLeft, targetX - viewportWidth / 2));
    scrollContainer.scrollLeft = desired;
  }, clickXRatio);

  const { localClickX } = await page.evaluate((ratio) => {
    const el = document.querySelector<HTMLCanvasElement>("canvas.w-full.cursor-pointer");
    const scrollContainer = el?.closest<HTMLDivElement>(".overflow-x-auto");
    const scrollLeft = scrollContainer?.scrollLeft ?? 0;
    const targetX = (el?.clientWidth ?? 0) * ratio;
    return { localClickX: Math.max(1, targetX - scrollLeft) };
  }, clickXRatio);

  await canvas.click({ position: { x: localClickX, y: 10 } });

  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return s && typeof s.selectedSectionId === "string" && s.selectedSectionId.length > 0;
  }, null, { timeout: 30_000 });

  // Ensure the builder is showing a selected range
  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return s && Array.isArray(s.sectionTrackKeys);
  }).catch(() => {});

  const genButton = page.getByRole("button", { name: /Generate Section Specific Track/i });
  await genButton.scrollIntoViewIfNeeded().catch(() => {});
  await expect(genButton).toBeVisible({ timeout: 60_000 });
  await expect(genButton).toBeEnabled({ timeout: 60_000 });

  await ensureLegacyGrooveSourceBuiltIn(page);
  await runLegacyGenerateAndAssertOk(page, genButton, 'section');

  await waitForLegacyGenerationToPopulate(page, "section");

  await expect(page.getByText(/Drum Performance Editor/i)).toBeVisible({ timeout: 60_000 });
  await expect(page.getByRole('button', { name: /^16th$/i })).toBeVisible({ timeout: 60_000 });
  await assertLegacyHasNotesOrTracks(page, 'section');
});
