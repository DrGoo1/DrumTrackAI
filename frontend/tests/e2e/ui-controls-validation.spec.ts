import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const AUDIO_PATH: string =
  (globalThis as any)?.process?.env?.E2E_AUDIO_PATH ||
  'F:\\DrumTracKAI_v1.1.17\\admin\\data\\drummer_songs\\jeff_porcaro_Rosanna.mp3';

type EvidenceStatus = 'pass' | 'fail' | 'skip';

type EvidenceRecord = {
  controlId: string;
  controlName: string;
  status: EvidenceStatus;
  startedAt: string;
  finishedAt: string;
  durationMs: number;
  baseURL: string;
  audioPath: string;
  details?: any;
  error?: { message: string; stack?: string };
  artifacts: {
    evidenceJson: string;
    screenshotPng?: string;
    traceZip?: string;
    videoWebm?: string;
  };
};

type ControlContext = {
  page: any;
  testInfo: any;
};

type ControlDefinition = {
  controlName: string;
  run: (ctx: ControlContext) => Promise<any>;
  skip?: boolean;
  skipReason?: string;
};

function ensureDir(p: string) {
  fs.mkdirSync(p, { recursive: true });
}

function toControlId(s: string) {
  return s
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

async function writeEvidence(opts: {
  testInfo: any;
  controlName: string;
  status: EvidenceStatus;
  startedAtMs: number;
  details?: any;
  error?: any;
}) {
  const { testInfo, controlName, status, startedAtMs, details, error } = opts;

  const controlId = toControlId(controlName);
  const evidenceRoot = path.join(testInfo.project.outputDir, 'ui-control-validation', controlId);
  ensureDir(evidenceRoot);

  const startedAt = new Date(startedAtMs).toISOString();
  const finishedAtMs = Date.now();
  const finishedAt = new Date(finishedAtMs).toISOString();

  const screenshotName = 'screenshot.png';
  const screenshotPath = path.join(evidenceRoot, screenshotName);
  const screenshotRel = path.relative(testInfo.project.outputDir, screenshotPath).replace(/\\/g, '/');

  try {
    await testInfo.page.screenshot({ path: screenshotPath, fullPage: true });
  } catch {
    // ignore
  }

  const evidenceJsonName = 'evidence.json';
  const evidenceJsonPath = path.join(evidenceRoot, evidenceJsonName);
  const evidenceJsonRel = path.relative(testInfo.project.outputDir, evidenceJsonPath).replace(/\\/g, '/');

  const attachments: Array<{ name: string; path?: string }> = [];

  const trace = testInfo.attachments?.find((a: any) => a.name === 'trace');
  if (trace?.path && typeof trace.path === 'string') attachments.push({ name: 'traceZip', path: trace.path });

  const video = testInfo.attachments?.find((a: any) => a.name === 'video');
  if (video?.path && typeof video.path === 'string') attachments.push({ name: 'videoWebm', path: video.path });

  const artifacts: EvidenceRecord['artifacts'] = {
    evidenceJson: evidenceJsonRel,
  };

  if (fs.existsSync(screenshotPath)) artifacts.screenshotPng = screenshotRel;
  if (trace?.path && typeof trace.path === 'string') {
    artifacts.traceZip = path.relative(testInfo.project.outputDir, trace.path).replace(/\\/g, '/');
  }
  if (video?.path && typeof video.path === 'string') {
    artifacts.videoWebm = path.relative(testInfo.project.outputDir, video.path).replace(/\\/g, '/');
  }

  const rec: EvidenceRecord = {
    controlId,
    controlName,
    status,
    startedAt,
    finishedAt,
    durationMs: finishedAtMs - startedAtMs,
    baseURL: testInfo.project.use.baseURL,
    audioPath: AUDIO_PATH,
    details,
    error: error
      ? {
          message: String(error?.message || error),
          stack: typeof error?.stack === 'string' ? error.stack : undefined,
        }
      : undefined,
    artifacts,
  };

  fs.writeFileSync(evidenceJsonPath, JSON.stringify(rec, null, 2), 'utf8');
}

async function waitForDtkState(page: any) {
  await page.waitForFunction(() => typeof (window as any).__DTK_STATE__ === 'object');
}

async function gotoHomeAndWaitForDtkState(page: any) {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await waitForDtkState(page);
}

async function snapshotDtkState(page: any) {
  return await page.evaluate(() => (window as any).__DTK_STATE__).catch(() => undefined);
}

async function gotoV3(page: any) {
  await page.goto('/v3?e2e=1', { waitUntil: 'domcontentloaded' });
}

async function ensureV3ScratchReady(page: any) {
  await gotoV3(page);

  const scratchMode = page.getByTestId('v3.workflow.scratch');
  if (await scratchMode.isVisible().catch(() => false)) {
    await scratchMode.check();
  } else {
    const newTrackRadio = page.getByRole('radio', { name: /New Track Creation/i });
    if (await newTrackRadio.isVisible().catch(() => false)) {
      await newTrackRadio.check();
    }
  }

  const buildBtn = page.getByTestId('v3.scratch.build');
  if (await buildBtn.isVisible().catch(() => false)) {
    await buildBtn.click();
  } else {
    const fallbackBuild = page.getByRole('button', { name: /Build New Track/i }).first();
    if (await fallbackBuild.isVisible().catch(() => false)) {
      await fallbackBuild.click();
    }
  }

  const drummerSelect = page.getByRole('combobox').filter({ hasText: /Select drummer profile/i }).first();
  if (await drummerSelect.isVisible().catch(() => false)) {
    await drummerSelect.selectOption({ index: 1 });
  }

  const generateBtn = page.getByTestId('v3.generate');
  await expect(generateBtn).toBeVisible({ timeout: 60_000 });

  // Ensure the Section inspector is visible (some view modes can hide it).
  const sectionInspectorBtn = page.getByRole('button', { name: /^Section$/i }).first();
  if (await sectionInspectorBtn.isVisible().catch(() => false)) {
    await sectionInspectorBtn.click();
  }
}

async function triggerV3GenerateAndCapture(page: any) {
  await page.route('**/api/generate-drums', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(makeStubV3DrumGenResponse()),
    });
  });

  const generateBtn = page.getByTestId('v3.generate');
  await expect(generateBtn).toBeVisible({ timeout: 60_000 });
  const [req] = await Promise.all([
    page.waitForRequest('**/api/generate-drums', { timeout: 60_000 }),
    generateBtn.click(),
  ]);
  return req.postDataJSON();
}

async function triggerLegacyFullSongGenerateAndCapture(page: any) {
  await page.route('**/api/generate-drums', async (route: any) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(makeStubV3DrumGenResponse()),
    });
  });

  const generateBtn = page.getByTestId('legacy.generateCompleteSong');
  await expect(generateBtn).toBeVisible({ timeout: 60_000 });
  await expect(generateBtn).toBeEnabled({ timeout: 60_000 });
  await generateBtn.scrollIntoViewIfNeeded();
  const [req] = await Promise.all([
    page.waitForRequest('**/api/generate-drums', { timeout: 60_000 }),
    (async () => {
      await generateBtn.evaluate((el: HTMLElement) => {
        const common = { bubbles: true, cancelable: true, button: 0 } as any;
        el.dispatchEvent(new MouseEvent('mousedown', { ...common, buttons: 1 }));
        el.dispatchEvent(new MouseEvent('mouseup', { ...common, buttons: 0 }));
        el.dispatchEvent(new MouseEvent('click', { ...common, buttons: 0 }));
      });
    })(),
  ]);
  return req.postDataJSON();
}

async function ensureLegacyReady(page: any) {
  await gotoHomeAndWaitForDtkState(page);

  const sectionsCount = await page
    .evaluate(() => {
      const s = (window as any).__DTK_STATE__;
      return Number(s?.sectionsCount ?? (Array.isArray(s?.sections) ? s.sections.length : 0) ?? 0);
    })
    .catch(() => 0);

  if (!sectionsCount) {
    const { modalRoot, modalHeading } = await openManualArrangementModal(page);
    const applyBtn = modalRoot.getByRole('button', { name: /^Apply Arrangement$/i }).first();
    await expect(applyBtn).toBeVisible({ timeout: 60_000 });

    page.once('dialog', async (d: any) => {
      await d.accept();
    });

    await applyBtn.click();
    await expect(modalHeading).toBeHidden({ timeout: 60_000 });

    await page.waitForFunction(() => {
      const s = (window as any).__DTK_STATE__;
      const n = Number(s?.sectionsCount ?? (Array.isArray(s?.sections) ? s.sections.length : 0) ?? 0);
      return n > 0;
    });
  }

  await ensureLegacyDrummerSelected(page);
  await ensureLegacyGrooveSourceBuiltIn(page);

  const genBtn = page.getByTestId('legacy.generateCompleteSong');
  await expect(genBtn).toBeVisible({ timeout: 60_000 });
}

async function v3SelectFirstSection(page: any) {
  const sectionSelect = page.getByTestId('v3.section.select');
  await expect(sectionSelect).toBeVisible({ timeout: 60_000 });
  const opts = await sectionSelect.locator('option').all();
  if (!opts.length) throw new Error('No section options found');
  const firstVal = await opts[0].getAttribute('value');
  if (!firstVal) throw new Error('First section option missing value');
  await sectionSelect.selectOption(firstVal);
  return firstVal;
}

async function v3EnsureBuildScopeSelectedSection(page: any) {
  const scopeBox = page.getByText(/^Scope$/i).locator('xpath=ancestor::div[contains(@class,"border")][1]').first();
  await expect(scopeBox).toBeVisible({ timeout: 60_000 });
  const selectedSectionRadio = scopeBox.getByRole('radio', { name: /Selected section/i }).first();
  await expect(selectedSectionRadio).toBeVisible({ timeout: 60_000 });
  await selectedSectionRadio.check();
}

function v3GlobalDefaultsPanel(page: any) {
  return page.getByText(/^GLOBAL Defaults$/i).locator('xpath=ancestor::div[contains(@class,"rounded-lg")][1]');
}

function v3SectionInspectorPanel(page: any) {
  return page.getByText(/^SECTION Inspector$/i).locator('xpath=ancestor::div[contains(@class,"rounded-lg")][1]');
}

function v3KnobByTestId(page: any, testId: string) {
  return page.getByTestId(testId);
}

function v3KnobRootByLabel(panel: any, label: RegExp) {
  return panel
    .locator('div.relative.rounded-full')
    .filter({ has: panel.getByText(label).first() })
    .first();
}

async function v3AdjustKnobByDrag(page: any, panel: any, label: RegExp, dy: number) {
  const knob = v3KnobRootByLabel(panel, label);
  await expect(knob).toBeVisible({ timeout: 60_000 });

  const box = await knob.boundingBox();
  if (!box) throw new Error(`Knob bounding box not found for ${String(label)}`);

  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;

  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x, y + dy, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(50);
}

async function v3AdjustKnobByDragTestId(page: any, testId: string, dy: number) {
  const knob = v3KnobByTestId(page, testId);
  await expect(knob).toBeVisible({ timeout: 60_000 });

  const box = await knob.boundingBox();
  if (!box) throw new Error(`Knob bounding box not found for testId ${testId}`);

  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;

  const pointerId = 1;
  await knob.dispatchEvent('pointerdown', {
    pointerId,
    clientX: x,
    clientY: y,
    buttons: 1,
    button: 0,
    pointerType: 'mouse',
    isPrimary: true,
    bubbles: true,
  });

  const steps = 8;
  for (let i = 1; i <= steps; i += 1) {
    const yy = y + (dy * i) / steps;
    await knob.dispatchEvent('pointermove', {
      pointerId,
      clientX: x,
      clientY: yy,
      buttons: 1,
      button: 0,
      pointerType: 'mouse',
      isPrimary: true,
      bubbles: true,
    });
  }

  await knob.dispatchEvent('pointerup', {
    pointerId,
    clientX: x,
    clientY: y + dy,
    buttons: 0,
    button: 0,
    pointerType: 'mouse',
    isPrimary: true,
    bubbles: true,
  });
  await page.waitForTimeout(50);
}

async function v3NudgeKnobUntilPayloadChangesByTestId(args: {
  page: any;
  testId: string;
  payloadKey: string;
  maxAttempts?: number;
}) {
  const { page, testId, payloadKey, maxAttempts = 4 } = args;
  const before = await triggerV3GenerateAndCapture(page);
  const beforeVal = (before as any)?.[payloadKey];

  const dYs = [-80, 80, -140, 140];
  for (let i = 0; i < Math.min(maxAttempts, dYs.length); i += 1) {
    await v3AdjustKnobByDragTestId(page, testId, dYs[i]);
    const after = await triggerV3GenerateAndCapture(page);
    const afterVal = (after as any)?.[payloadKey];
    if (afterVal !== beforeVal) {
      return { before, after };
    }
  }

  const last = await triggerV3GenerateAndCapture(page);
  throw new Error(
    `V3 knob did not change payload.${payloadKey}. Before=${JSON.stringify(beforeVal)} After=${JSON.stringify((last as any)?.[payloadKey])}`
  );
}

async function dragSelectedNoteByPixels(page: any, args: { noteId: string; startOffsetFromRightPx?: number; dx: number; dy?: number }) {
  const loc = page.locator(`[data-note-id="${args.noteId}"]`).first();
  await expect(loc).toBeVisible({ timeout: 60_000 });
  const box = await loc.boundingBox();
  if (!box) throw new Error('Could not get bounding box for selected note');

  const dy = Number(args.dy ?? 0);
  const startOffsetFromRight = Number(args.startOffsetFromRightPx ?? 0);
  const startX = box.x + box.width / 2 + (startOffsetFromRight ? box.width / 2 - startOffsetFromRight : 0);
  const startY = box.y + box.height / 2;

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  await page.mouse.move(startX + args.dx, startY + dy, { steps: 8 });
  await page.mouse.up();
}

async function clickRangeByTestId(page: any, testId: string, frac01: number) {
  const input = page.getByTestId(testId);
  await expect(input).toBeVisible({ timeout: 60_000 });

  const box = await input.boundingBox();
  if (!box) throw new Error(`Could not resolve bounding box for range input: ${testId}`);
  const f = Math.max(0, Math.min(1, Number(frac01) || 0));
  const x = box.x + Math.max(2, Math.min(box.width - 2, box.width * f));
  const y = box.y + box.height / 2;

  await page.mouse.click(x, y);
  await page.waitForTimeout(150);
}

async function waitForSelectedNoteTicksToChange(page: any, before: { barIndex?: any; tickInBar?: any }) {
  const beforeBar = Number(before?.barIndex ?? NaN);
  const beforeTick = Number(before?.tickInBar ?? NaN);
  await page.waitForFunction(
    (args: { beforeBar: number; beforeTick: number }) => {
      const s = (window as any).__DTK_STATE__;
      const notes = s?.drumEditor?.selectedNotes;
      if (!Array.isArray(notes) || !notes.length) return false;
      const n0 = notes[0] as any;
      const bar = Number(n0?.barIndex ?? NaN);
      const tick = Number(n0?.tickInBar ?? NaN);
      if (!Number.isFinite(bar) || !Number.isFinite(tick)) return false;
      return bar !== args.beforeBar || tick !== args.beforeTick;
    },
    { beforeBar, beforeTick },
    { timeout: 10_000 },
  );
}

async function v3NudgeKnobUntilPayloadChanges(args: {
  page: any;
  panel: any;
  label: RegExp;
  payloadKey: string;
  maxAttempts?: number;
}) {
  const { page, panel, label, payloadKey, maxAttempts = 4 } = args;
  const before = await triggerV3GenerateAndCapture(page);
  const beforeVal = (before as any)?.[payloadKey];

  const dYs = [-80, 80, -140, 140];
  for (let i = 0; i < Math.min(maxAttempts, dYs.length); i += 1) {
    await v3AdjustKnobByDrag(page, panel, label, dYs[i]);
    const after = await triggerV3GenerateAndCapture(page);
    const afterVal = (after as any)?.[payloadKey];
    if (afterVal !== beforeVal) {
      return { before, after };
    }
  }

  const last = await triggerV3GenerateAndCapture(page);
  throw new Error(
    `V3 knob did not change payload.${payloadKey}. Before=${JSON.stringify(beforeVal)} After=${JSON.stringify((last as any)?.[payloadKey])}`
  );
}

function makeStubV3DrumGenResponse() {
  const ppq = 960;
  const ticksPerBeat = ppq;
  const beatsPerBar = 4;
  const notes: any[] = [];
  const push = (barIndex: number, tickInBar: number, instrumentId: string, midiPitch: number, velocity: number) => {
    notes.push({
      id: `${instrumentId}-${barIndex}-${tickInBar}`,
      barIndex,
      tickInBar,
      tickLength: Math.max(1, Math.floor(ppq / 8)),
      instrumentId,
      articulationId: null,
      channel: 9,
      midiPitch,
      velocity,
      aspect: 'groove',
      limbId: instrumentId === 'kick' ? 'RF' : instrumentId.startsWith('snare') ? 'LH' : 'RH',
      priority: 0.6,
      microTimingMs: 0,
      hatOpenLevel: 0,
      hitStyle: 'single',
      locked: false,
      isGhost: false,
      isAccent: false,
      isFlam: false,
      isDrag: false,
      phraseMarker: null,
      rudimentId: null,
    });
  };

  for (let bar = 0; bar < 2; bar += 1) {
    for (let b = 0; b < beatsPerBar * 2; b += 1) {
      push(bar, Math.floor((b * ticksPerBeat) / 2), 'hihat_closed', 42, 74);
    }
    push(bar, 0, 'kick', 36, 106);
    push(bar, 2 * ticksPerBeat, 'kick', 36, 106);
    push(bar, 1 * ticksPerBeat, 'snare_center', 38, 100);
    push(bar, 3 * ticksPerBeat, 'snare_center', 38, 100);
  }

  return {
    ok: true,
    drum_track: {
      track_id: 'test-track',
      style_id: 'rock',
      resolution_ppq: ppq,
      notes,
      performance_spec: {
        styleId: 'rock',
        globalFeel: 'straight',
        quantizationBase: '16th',
        phrases: [],
      },
    },
    midi_base64: 'AA==',
    metadata: {
      builder_version: 'v3-stub',
      generation_time_ms: 1,
      drummer_used: 'test',
      style: 'rock',
      mode: 'template',
      humanized: false,
      measure_count: 2,
    },
  };
}

async function runControlValidation(def: ControlDefinition, ctx: ControlContext) {
  const startedAt = Date.now();
  const { page, testInfo } = ctx;

  if (def.skip) {
    await writeEvidence({
      testInfo: { ...testInfo, page },
      controlName: def.controlName,
      status: 'skip',
      startedAtMs: startedAt,
      details: def.skipReason ? { skipReason: def.skipReason } : undefined,
    });
    test.skip(true, def.skipReason || 'skipped');
    return;
  }

  try {
    const details = await def.run({ page, testInfo });
    await writeEvidence({
      testInfo: { ...testInfo, page },
      controlName: def.controlName,
      status: 'pass',
      startedAtMs: startedAt,
      details,
    });
  } catch (e: any) {
    await writeEvidence({
      testInfo: { ...testInfo, page },
      controlName: def.controlName,
      status: 'fail',
      startedAtMs: startedAt,
      error: e,
    });
    throw e;
  }
}

async function ensureLegacyDrummerSelected(page: any) {
  // If UI already indicates a selection, we can skip.
  const selectedLabel = page.getByText(/^Selected$/i).first();
  if (await selectedLabel.isVisible().catch(() => false)) {
    const selectedBox = selectedLabel.locator('xpath=ancestor::div[1]').first();
    const selectedText = await selectedBox.textContent().catch(() => '');
    if (typeof selectedText === 'string' && !/\bnone\b/i.test(selectedText)) {
      return;
    }
  }

  // Inline drawer variant (Advanced Drum Tools > Select Drummer Style).
  const drawerHeading = page.getByRole('heading', { name: /Select Drummer Style/i }).first();
  if (!(await drawerHeading.isVisible().catch(() => false))) {
    const chooseStyleBtn = page.getByRole('button', { name: /choose style/i }).first();
    if (await chooseStyleBtn.isVisible().catch(() => false)) {
      await chooseStyleBtn.click();
    }
  }

  if (await drawerHeading.isVisible().catch(() => false)) {
    const drawer = drawerHeading.locator('xpath=ancestor::div[contains(@class,"rounded")][1]');
    await expect(drawer).toBeVisible({ timeout: 60_000 });

    const preferredNames = [/Studio Groove Master/i, /Rock Powerhouse/i, /Metal Atomic Clock/i];
    for (const nameRe of preferredNames) {
      const nameEl = drawer.getByRole('heading', { name: nameRe }).first();
      if (await nameEl.isVisible().catch(() => false)) {
        const card = nameEl.locator('xpath=ancestor::div[contains(@class,"rounded")][1]');
        await card.click({ force: true });
        break;
      }
    }

    await page
      .waitForFunction(() => {
        const root = document.body;
        const selectedLabel = Array.from(root.querySelectorAll('*')).find(
          (el) => (el as HTMLElement).innerText?.trim?.().toUpperCase?.() === 'SELECTED',
        );
        if (!selectedLabel) return false;
        const box = (selectedLabel as HTMLElement).parentElement;
        const text = (box?.innerText || '').toLowerCase();
        return text.includes('selected') && !text.includes('none');
      })
      .catch(() => {});

    const closeBtn = drawer.getByRole('button', { name: /^Close$/i }).first();
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
    }

    // Drawer can collapse into a compact summary row that still contains the heading.
    // Wait for the Close button to disappear to ensure it no longer blocks the page.
    await expect(closeBtn).toBeHidden({ timeout: 60_000 });
    return;
  }

  // Open modal (either via a Change Drummer button or the Choose Style button in the Select Drummer panel).
  const changeBtn = page.getByRole('button', { name: /change drummer/i }).first();
  if (await changeBtn.isVisible().catch(() => false)) {
    await changeBtn.click();
  } else {
    const chooseStyleBtn = page.getByRole('button', { name: /choose style/i }).first();
    if (await chooseStyleBtn.isVisible().catch(() => false)) {
      await chooseStyleBtn.click();
    }
  }

  const modalTitle = page.getByText(/Choose Your Drummer!/i).first();
  await expect(modalTitle).toBeVisible({ timeout: 60_000 });
  const modal = modalTitle.locator('xpath=ancestor::div[contains(@class,"fixed")][1]');
  await expect(modal).toBeVisible({ timeout: 60_000 });

  // Prefer a non-default drummer card by visible name; fallback to first clickable card.
  const preferredNames = [/Studio Groove Master/i, /Rock Powerhouse/i, /Metal Atomic Clock/i];
  let clicked = false;
  for (const nameRe of preferredNames) {
    const nameEl = modal.getByText(nameRe).first();
    if (await nameEl.isVisible().catch(() => false)) {
      const cardCursor = nameEl.locator('xpath=ancestor::div[contains(@class,"cursor-pointer")][1]');
      const cardFallback = nameEl.locator('xpath=ancestor::div[contains(@class,"rounded")][1]');
      const card = (await cardCursor.isVisible().catch(() => false)) ? cardCursor : cardFallback;
      await card.click({ force: true });
      clicked = true;
      break;
    }
  }

  if (!clicked) {
    const anyCard = modal.locator('div').filter({ hasText: /Best for:/i }).filter({ has: modal.locator('h4') }).first();
    if (await anyCard.isVisible().catch(() => false)) {
      await anyCard.click({ force: true });
      clicked = true;
    }
  }

  // Wait until the modal shows a non-None selection (this UI commonly shows 'SELECTED' and a value).
  await page.waitForFunction(() => {
    const root = document.body;
    const selectedLabel = Array.from(root.querySelectorAll('*')).find((el) => (el as HTMLElement).innerText?.trim?.() === 'SELECTED');
    if (!selectedLabel) return false;
    const box = (selectedLabel as HTMLElement).parentElement;
    const text = (box?.innerText || '').toLowerCase();
    return text.includes('selected') && !text.includes('none');
  }).catch(() => {});

  // Dismiss.
  await page.keyboard.press('Escape').catch(() => {});
  const closeBtnByName = modal.getByRole('button', { name: /^Close$/i }).first();
  const closeBtnByText = modal.locator('button').filter({ hasText: /[×✕]/ }).first();
  const closeBtn = (await closeBtnByName.isVisible().catch(() => false)) ? closeBtnByName : closeBtnByText;
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click().catch(() => {});
  }

  await expect(modalTitle).toBeHidden({ timeout: 60_000 });
}

async function ensureLegacyGrooveSourceBuiltIn(page: any) {
  const labeledContainer = page.getByText(/^Groove Source$/i).locator('..').first();
  const labeledSelect = labeledContainer.locator('select').first();

  const anyGrooveSelect = page
    .locator('select')
    .filter({ has: page.locator('option', { hasText: /^Built-in$/i }) })
    .filter({ has: page.locator('option', { hasText: /^E-GMD Phrases$/i }) })
    .first();

  const combo = (await labeledSelect.isVisible().catch(() => false)) ? labeledSelect : anyGrooveSelect;
  if (!(await combo.isVisible().catch(() => false))) return;

  await expect(combo).toBeVisible({ timeout: 60_000 });

  const deadlineMs = Date.now() + 30_000;
  // Some UI/state flows can immediately re-apply defaults (e.g. E-GMD Phrases).
  // Keep selecting until it sticks.
  while (Date.now() < deadlineMs) {
    await combo.selectOption({ label: 'Built-in' }).catch(async () => {
      await combo.selectOption({ value: 'pattern' });
    });

    // Ensure React/change handlers fire even in controlled selects.
    await combo.evaluate((el: HTMLSelectElement) => {
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.blur();
    });
    await page.waitForTimeout(150);

    const selectedText = await combo.locator('option:checked').textContent().catch(() => null);
    const selectedValue = await combo.evaluate((el: HTMLSelectElement) => el.value).catch(() => null);

    const okText = typeof selectedText === 'string' && /built-in/i.test(selectedText);
    const okValue = typeof selectedValue === 'string' && selectedValue === 'pattern';
    if (okText || okValue) return;
  }

  // Final assertion provides a clear error message.
  const selectedText = await combo.locator('option:checked').textContent().catch(() => null);
  throw new Error(`Groove Source did not stick to Built-in. Selected: ${JSON.stringify(selectedText)}`);
}

async function openManualArrangementModal(page: any) {
  const openBtn = page.getByRole('button', { name: /Manual Arrangement/i }).first();
  await expect(openBtn).toBeVisible({ timeout: 60_000 });
  await openBtn.click();

  const modalHeading = page.getByRole('heading', { name: /Manual Arrangement/i }).first();
  await expect(modalHeading).toBeVisible({ timeout: 60_000 });

  const modalRoot = modalHeading.locator('xpath=ancestor::div[contains(@class,"fixed")][1]');
  await expect(modalRoot).toBeVisible({ timeout: 60_000 });
  return { modalRoot, modalHeading };
}

function modalNumberInputByLabel(modalRoot: any, labelText: RegExp) {
  return modalRoot.getByText(labelText).locator('xpath=ancestor::div[1]//input[@type="number"]').first();
}

function modalSelectByLabel(modalRoot: any, labelText: RegExp) {
  return modalRoot.getByText(labelText).locator('xpath=ancestor::div[1]//select').first();
}

function approxEq(a: number, b: number, eps = 1e-6) {
  return Math.abs(a - b) <= eps;
}

async function ensureDrumOptionsSectionExpanded(page: any, headingText: RegExp, visibleTestId: string) {
  const target = page.getByTestId(visibleTestId);
  if (await target.isVisible().catch(() => false)) return;

  const btn = page.locator('button').filter({ hasText: headingText }).first();
  await expect(btn).toBeVisible({ timeout: 60_000 });
  await btn.click();
  await expect(target).toBeVisible({ timeout: 60_000 });
}

async function ensureDetailsExpanded(page: any, summaryText: RegExp) {
  const details = page.locator('details').filter({ has: page.locator('summary', { hasText: summaryText }) }).first();
  await expect(details).toBeVisible({ timeout: 60_000 });
  const isOpen = await details.getAttribute('open');
  if (isOpen === null) {
    const summary = details.locator('summary').first();
    await expect(summary).toBeVisible({ timeout: 60_000 });
    await summary.click();
    await page
      .waitForFunction((el) => (el as HTMLElement).hasAttribute('open'), await details.elementHandle(), {
        timeout: 60_000,
      })
      .catch(() => {});
  }
}

async function getLegacyDrumOption(page: any, key: string) {
  return page
    .evaluate((k) => {
      const s = (window as any).__DTK_STATE__;
      return s?.drumOptions?.[k] ?? null;
    }, key)
    .catch(() => null);
}

async function waitForLegacyNotesPreviewCountToBeAtLeast(page: any, minCount: number) {
  const min = Math.max(0, Math.floor(Number(minCount) || 0));
  await page.waitForFunction(
    (m: number) => {
      const s = (window as any).__DTK_STATE__;
      const notes = s?.drumEditor?.notesPreview;
      return Array.isArray(notes) && notes.length >= m;
    },
    min,
    { timeout: 60_000 },
  );
}

async function getLegacyDrumEditorState(page: any) {
  return page
    .evaluate(() => {
      const s = (window as any).__DTK_STATE__;
      return s?.drumEditor;
    })
    .catch(() => undefined);
}

async function ensureLegacyDrumEditorReady(page: any) {
  await ensureLegacyReady(page);

  // Ensure the Drum Performance Editor is active by selecting any section.
  const dtk = await snapshotDtkState(page);
  const sections = Array.isArray((dtk as any)?.sections) ? (dtk as any).sections : [];
  const firstId = sections?.[0]?.id;
  if (!firstId) {
    throw new Error('No sections found in __DTK_STATE__.sections; cannot activate Drum Performance Editor');
  }

  const sectionBtn = page.getByTestId(`drumEditor.songMap.section.${firstId}`);
  await expect(sectionBtn).toBeVisible({ timeout: 60_000 });

  // The app uses onMouseDown + preventDefault for section selection.
  await sectionBtn.evaluate((el: HTMLElement) => {
    const common = { bubbles: true, cancelable: true, button: 0 } as any;
    el.dispatchEvent(new MouseEvent('mousedown', { ...common, buttons: 1 }));
    el.dispatchEvent(new MouseEvent('mouseup', { ...common, buttons: 0 }));
    el.dispatchEvent(new MouseEvent('click', { ...common, buttons: 0 }));
  });

  // If the editor pane isn't mounted yet (no drum data), trigger a stubbed generate once.
  const hasEditor = await page
    .evaluate(() => {
      const s = (window as any).__DTK_STATE__;
      return !!s?.drumEditor && typeof s.drumEditor === 'object';
    })
    .catch(() => false);

  if (!hasEditor) {
    await triggerLegacyFullSongGenerateAndCapture(page);
  }

  await page.waitForFunction(() => {
    const s = (window as any).__DTK_STATE__;
    return !!s?.drumEditor && typeof s.drumEditor === 'object';
  }, null, { timeout: 60_000 });
}

async function getLegacySelectedNote(page: any) {
  return await page
    .evaluate(() => {
      const s = (window as any).__DTK_STATE__;
      const notes = s?.drumEditor?.selectedNotes;
      return Array.isArray(notes) && notes.length ? notes[0] : null;
    })
    .catch(() => null);
}

async function ensureLegacyFirstNoteSelected(
  page: any,
  opts?: { instrumentPrefix?: string; requireNotAtStart?: boolean },
) {
  await ensureLegacyDrumEditorReady(page);

  const noteId = await page
    .evaluate((args?: { instrumentPrefix?: string; requireNotAtStart?: boolean }) => {
      const s = (window as any).__DTK_STATE__;
      const notes = s?.drumEditor?.notesPreview;
      if (!Array.isArray(notes) || !notes.length) return null;
      const prefix = typeof args?.instrumentPrefix === 'string' ? args.instrumentPrefix : null;
      const requireNotAtStart = !!args?.requireNotAtStart;

      const candidates = prefix
        ? notes.filter((n: any) => String(n?.instrumentId || '').startsWith(prefix))
        : notes;

      const match = requireNotAtStart
        ? candidates.find((n: any) => Number(n?.barIndex || 0) > 0 || Number(n?.tickInBar || 0) > 0)
        : candidates[0];
      return match?.id ?? null;
    }, { instrumentPrefix: opts?.instrumentPrefix, requireNotAtStart: opts?.requireNotAtStart })
    .catch(() => null);

  if (!noteId) {
    throw new Error('No note id found in __DTK_STATE__.drumEditor.notesPreview');
  }

  const noteEl = page.locator(`[data-note-id="${noteId}"]`).first();
  await expect(noteEl).toBeVisible({ timeout: 60_000 });
  await noteEl.click({ force: true });

  await page.waitForFunction(
    (id: string) => {
      const s = (window as any).__DTK_STATE__;
      const notes = s?.drumEditor?.selectedNotes;
      return Array.isArray(notes) && notes.length && notes[0]?.id === id;
    },
    noteId,
    { timeout: 60_000 },
  );

  return noteId;
}

async function setRangeValueByTestId(page: any, testId: string, value: number) {
  const input = page.getByTestId(testId);
  await expect(input).toBeVisible({ timeout: 60_000 });
  await input.evaluate(
    (el: HTMLInputElement, v: number) => {
      el.value = String(v);
      try {
        (el as any).valueAsNumber = Number(v);
      } catch {
        // ignore
      }
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      el.blur();
    },
    value,
  );
  await page.waitForTimeout(100);
}

async function waitForSelectedNoteFieldToChange(page: any, field: string, beforeVal: any) {
  await page.waitForFunction(
    (args: { field: string; beforeVal: any }) => {
      const s = (window as any).__DTK_STATE__;
      const notes = s?.drumEditor?.selectedNotes;
      if (!Array.isArray(notes) || !notes.length) return false;
      const afterVal = (notes[0] as any)?.[args.field];
      return afterVal !== args.beforeVal;
    },
    { field, beforeVal },
    { timeout: 10_000 },
  );
}

test.describe('UI Control Validation (evidence artifacts)', () => {
  const controls: Array<ControlDefinition> = [
    {
      controlName: 'Legacy: Drummer selection + Groove Source Built-in',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        await ensureLegacyDrummerSelected(page);
        await ensureLegacyGrooveSourceBuiltIn(page);
        return {
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'Legacy: Drummer selection (non-default)',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        await ensureLegacyDrummerSelected(page);
        const state = await snapshotDtkState(page);
        const selected = state?.selectedDrummer || state?.drummer || null;
        const id = (selected && typeof selected === 'object' ? (selected as any).id : null) || state?.drummerId || null;
        expect(typeof id === 'string' ? id : 'unknown').not.toBe('default_neutral');
        return { dtkState: state, selectedDrummerId: id };
      },
    },
    {
      controlName: 'Legacy: Groove Source = Built-in',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        await ensureLegacyGrooveSourceBuiltIn(page);

        const labeledContainer = page.getByText(/^Groove Source$/i).locator('..').first();
        const labeledSelect = labeledContainer.locator('select').first();
        const anyGrooveSelect = page
          .locator('select')
          .filter({ has: page.locator('option', { hasText: /^Built-in$/i }) })
          .filter({ has: page.locator('option', { hasText: /^E-GMD Phrases$/i }) })
          .first();

        const combo = (await labeledSelect.isVisible().catch(() => false)) ? labeledSelect : anyGrooveSelect;
        await expect(combo).toBeVisible({ timeout: 60_000 });
        await expect(combo.locator('option:checked')).toHaveText(/Built-in/i, { timeout: 60_000 });

        return {
          dtkState: await snapshotDtkState(page),
          selectedOptionText: await combo.locator('option:checked').textContent().catch(() => null),
        };
      },
    },

    {
      controlName: 'Drum Options Panel > Fill Type affects generate payload',
      run: async ({ page }) => {
        await ensureLegacyReady(page);

        await ensureDrumOptionsSectionExpanded(page, /Fill Options/i, 'drumOptions.fills.fillType');

        const fillType = page.getByTestId('drumOptions.fills.fillType');
        await expect(fillType).toBeVisible({ timeout: 60_000 });

        const before = await triggerLegacyFullSongGenerateAndCapture(page);
        const beforeVal = String(before?.fillType || '');

        const opts = await fillType.locator('option').all();
        const values: string[] = [];
        for (const opt of opts) {
          const v = await opt.getAttribute('value');
          if (v) values.push(v);
        }
        const next = values.find((v) => v && v !== beforeVal) || values[0];
        if (!next) throw new Error('No fill type options found');

        await fillType.selectOption(next);
        const after = await triggerLegacyFullSongGenerateAndCapture(page);

        expect(String(after?.fillType || '')).toBe(String(next));
        expect(String(after?.fillType || '')).not.toBe(beforeVal);

        return { before, after };
      },
    },

    {
      controlName: 'V3 UI: Transport Follow Playhead toggle updates state',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const follow = page.getByTestId('v3.transport.follow_playhead');
        await expect(follow).toBeVisible({ timeout: 60_000 });

        const before = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        const beforeVal = !!before?.followPlayhead;

        await follow.setChecked(!beforeVal);
        await page.waitForFunction(
          (v) => (window as any).__DTK_V3_TRANSPORT__ && !!(window as any).__DTK_V3_TRANSPORT__.followPlayhead === v,
          !beforeVal,
          { timeout: 60_000 }
        );
        const after = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        expect(!!after?.followPlayhead).toBe(!beforeVal);

        return { before, after };
      },
    },

    {
      controlName: 'V3 UI: Transport Click toggle updates state',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const click = page.getByTestId('v3.transport.click');
        await expect(click).toBeVisible({ timeout: 60_000 });

        const before = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        const beforeVal = !!before?.clickEnabled;

        await click.setChecked(!beforeVal);
        await page.waitForFunction(
          (v) => (window as any).__DTK_V3_TRANSPORT__ && !!(window as any).__DTK_V3_TRANSPORT__.clickEnabled === v,
          !beforeVal,
          { timeout: 60_000 }
        );
        const after = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        expect(!!after?.clickEnabled).toBe(!beforeVal);

        return { before, after };
      },
    },

    {
      controlName: 'V3 UI: Transport Zoom controls update state',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const zoomIn = page.getByTestId('v3.transport.zoom_in');
        const zoomOut = page.getByTestId('v3.transport.zoom_out');
        const zoomReset = page.getByTestId('v3.transport.zoom_reset');
        await expect(zoomIn).toBeVisible({ timeout: 60_000 });
        await expect(zoomOut).toBeVisible({ timeout: 60_000 });
        await expect(zoomReset).toBeVisible({ timeout: 60_000 });

        const before = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        const beforePpb = Number(before?.pixelsPerBeat || 0);

        await zoomIn.click();
        await page.waitForFunction(
          (prev) => (window as any).__DTK_V3_TRANSPORT__ && Number((window as any).__DTK_V3_TRANSPORT__.pixelsPerBeat || 0) !== prev,
          beforePpb,
          { timeout: 60_000 }
        );
        const afterIn = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        const afterInPpb = Number(afterIn?.pixelsPerBeat || 0);
        expect(afterInPpb).not.toBe(beforePpb);

        await zoomOut.click();
        const afterOut = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        const afterOutPpb = Number(afterOut?.pixelsPerBeat || 0);
        expect(afterOutPpb).toBeGreaterThan(0);

        await zoomReset.click();
        await page.waitForFunction(
          () => (window as any).__DTK_V3_TRANSPORT__ && Number((window as any).__DTK_V3_TRANSPORT__.pixelsPerBeat || 0) === 64,
          undefined,
          { timeout: 60_000 }
        );
        const afterReset = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        expect(Number(afterReset?.pixelsPerBeat || 0)).toBe(64);

        return { before, afterIn, afterOut, afterReset };
      },
    },

    {
      controlName: 'V3 UI: Transport Return to Start resets playhead',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        await page.evaluate(() => {
          try {
            (window as any).__DTK_V3_SET_PLAYHEAD__?.(1.23);
          } catch {
            // ignore
          }
        });

        const btn = page.getByTestId('v3.transport.return_to_start');
        await expect(btn).toBeVisible({ timeout: 60_000 });
        await btn.click();

        await page.waitForFunction(() => {
          const t = (window as any).__DTK_V3_TRANSPORT__;
          return t && Number(t.playheadSec || 0) === 0;
        });

        const after = await page.evaluate(() => (window as any).__DTK_V3_TRANSPORT__).catch(() => undefined);
        expect(Number(after?.playheadSec || 0)).toBe(0);

        return { after };
      },
    },

    {
      controlName: 'V3 UI: Bar Edits Add Note affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        const selectedSectionId = await v3SelectFirstSection(page);

        const sectionPanel = v3SectionInspectorPanel(page);
        await expect(sectionPanel).toBeVisible({ timeout: 60_000 });

        const barScope = sectionPanel.getByRole('radio', { name: /Per\s*bar/i }).first();
        await expect(barScope).toBeVisible({ timeout: 60_000 });
        await barScope.check();

        // Ensure track exists and per-bar tools are active.
        await triggerV3GenerateAndCapture(page);

        const addBtn = sectionPanel.getByTestId('v3.bar.notes.add');
        await expect(addBtn).toBeVisible({ timeout: 60_000 });
        await addBtn.click();

        const req = await triggerV3GenerateAndCapture(page);
        expect(String((req as any)?.sectionId || '')).toBe(String(selectedSectionId));
        const edits = (req as any)?.barEdits || {};
        const bars = Object.keys(edits);
        expect(bars.length).toBeGreaterThan(0);
        const firstBar = bars[0];
        const added = (edits as any)?.[firstBar]?.addedNotes || [];
        expect(Array.isArray(added)).toBeTruthy();
        expect(added.length).toBeGreaterThan(0);
        return { req };
      },
    },

    {
      controlName: 'V3 UI: Bar Edits Nudge Note affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        const selectedSectionId = await v3SelectFirstSection(page);

        const sectionPanel = v3SectionInspectorPanel(page);
        await expect(sectionPanel).toBeVisible({ timeout: 60_000 });

        const barScope = sectionPanel.getByRole('radio', { name: /Per\s*bar/i }).first();
        await expect(barScope).toBeVisible({ timeout: 60_000 });
        await barScope.check();

        await triggerV3GenerateAndCapture(page);

        const addBtn = sectionPanel.getByTestId('v3.bar.notes.add');
        await expect(addBtn).toBeVisible({ timeout: 60_000 });
        await addBtn.click();

        const nudgeRight = sectionPanel.getByTestId('v3.bar.notes.nudge_right').first();
        await expect(nudgeRight).toBeVisible({ timeout: 60_000 });
        const noteId = String(await nudgeRight.getAttribute('data-note-id'));
        expect(noteId.length).toBeGreaterThan(0);
        await nudgeRight.click();

        const req = await triggerV3GenerateAndCapture(page);
        expect(String((req as any)?.sectionId || '')).toBe(String(selectedSectionId));

        const edits = (req as any)?.barEdits || {};
        const bars = Object.keys(edits);
        expect(bars.length).toBeGreaterThan(0);
        const firstBar = bars[0];
        const deltas = (edits as any)?.[firstBar]?.tickDeltaByNoteId || {};
        expect(typeof deltas).toBe('object');
        expect(Number((deltas as any)?.[noteId] || 0)).not.toBe(0);
        return { req, noteId };
      },
    },

    {
      controlName: 'V3 UI: Bar Edits Delete Note affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        const selectedSectionId = await v3SelectFirstSection(page);

        const sectionPanel = v3SectionInspectorPanel(page);
        await expect(sectionPanel).toBeVisible({ timeout: 60_000 });

        const barScope = sectionPanel.getByRole('radio', { name: /Per\s*bar/i }).first();
        await expect(barScope).toBeVisible({ timeout: 60_000 });
        await barScope.check();

        await triggerV3GenerateAndCapture(page);

        const addBtn = sectionPanel.getByTestId('v3.bar.notes.add');
        await expect(addBtn).toBeVisible({ timeout: 60_000 });
        await addBtn.click();

        const delBtn = sectionPanel.getByTestId('v3.bar.notes.delete').first();
        await expect(delBtn).toBeVisible({ timeout: 60_000 });
        const noteId = String(await delBtn.getAttribute('data-note-id'));
        expect(noteId.length).toBeGreaterThan(0);
        await delBtn.click();

        const req = await triggerV3GenerateAndCapture(page);
        expect(String((req as any)?.sectionId || '')).toBe(String(selectedSectionId));

        const edits = (req as any)?.barEdits || {};
        const bars = Object.keys(edits);
        expect(bars.length).toBeGreaterThan(0);
        const firstBar = bars[0];
        const deleted = (edits as any)?.[firstBar]?.deletedNoteIds || [];
        expect(Array.isArray(deleted)).toBeTruthy();
        expect(deleted.map(String)).toContain(noteId);
        return { req, noteId };
      },
    },

    {
      controlName: 'V3 UI: Humanize (section override) affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        await v3SelectFirstSection(page);

        const humanOverride = page.getByTestId('v3.section.inherit.humanization.override');
        await expect(humanOverride).toBeVisible({ timeout: 60_000 });
        await humanOverride.check();

        const humanizeToggle = page.getByTestId('v3.section.humanization.humanize');
        await expect(humanizeToggle).toBeVisible({ timeout: 60_000 });

        await humanizeToggle.setChecked(false);
        const reqOff = await triggerV3GenerateAndCapture(page);
        expect(!!(reqOff as any)?.humanize).toBeFalsy();

        await humanizeToggle.setChecked(true);
        const reqOn = await triggerV3GenerateAndCapture(page);
        expect(!!(reqOn as any)?.humanize).toBeTruthy();

        return { reqOff, reqOn };
      },
    },

    {
      controlName: 'V3 UI: Rudiments Hand Lead (section override) affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        await v3SelectFirstSection(page);

        const rudOverride = page.getByTestId('v3.section.inherit.rudiments.override');
        await expect(rudOverride).toBeVisible({ timeout: 60_000 });
        await rudOverride.check();

        const select = page.getByTestId('v3.section.rudiments.handLead');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const before = await triggerV3GenerateAndCapture(page);
        const beforeVal = String((before as any)?.rudimentControls?.handLead || '');
        const next = beforeVal === 'left' ? 'right' : 'left';
        await select.selectOption({ value: next });

        const after = await triggerV3GenerateAndCapture(page);
        expect(String((after as any)?.rudimentControls?.handLead || '')).toBe(next);
        expect(String((after as any)?.rudimentControls?.handLead || '')).not.toBe(beforeVal);

        return { before, after };
      },
    },

    {
      controlName: 'V3 UI: Groove Use (section override) affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        await v3SelectFirstSection(page);

        const grooveOverride = page.getByTestId('v3.section.inherit.groove.override');
        await expect(grooveOverride).toBeVisible({ timeout: 60_000 });
        await grooveOverride.check();

        const select = page.getByTestId('v3.section.groove.grooveUse');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const before = await triggerV3GenerateAndCapture(page);
        const beforeVal = String((before as any)?.grooveUse || '');
        const next = beforeVal === 'use_as_fill' ? 'use_as_groove' : 'use_as_fill';
        await select.selectOption({ value: next });

        const after = await triggerV3GenerateAndCapture(page);
        expect(String((after as any)?.grooveUse || '')).toBe(next);
        expect(String((after as any)?.grooveUse || '')).not.toBe(beforeVal);

        return { before, after };
      },
    },

    {
      controlName: 'V3 UI: Fill Locations (force/suppress bar) affect generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        await v3EnsureBuildScopeSelectedSection(page);
        const selectedSectionId = await v3SelectFirstSection(page);

        const sectionPanel = v3SectionInspectorPanel(page);
        await expect(sectionPanel).toBeVisible({ timeout: 60_000 });

        const reqBaseline = await triggerV3GenerateAndCapture(page);
        if (String((reqBaseline as any)?.buildScope || '') !== 'selected_section') {
          throw new Error(`Expected buildScope=selected_section, got ${(reqBaseline as any)?.buildScope}`);
        }
        if (String((reqBaseline as any)?.sectionId || '') !== String(selectedSectionId)) {
          throw new Error(`Expected payload.sectionId=${selectedSectionId}, got ${(reqBaseline as any)?.sectionId}`);
        }

        const barScope = sectionPanel.getByRole('radio', { name: /Per\s*bar/i }).first();
        await expect(barScope).toBeVisible({ timeout: 60_000 });
        await barScope.check();

        // Ensure there is a generated track so Bar Edits UI becomes available.
        await triggerV3GenerateAndCapture(page);

        const force = sectionPanel.getByTestId('v3.bar.forceFill');
        await expect(force).toBeVisible({ timeout: 60_000 });
        await expect(force).toBeEnabled({ timeout: 60_000 });
        await force.setChecked(true);
        await expect(force).toBeChecked({ timeout: 60_000 });

        let reqForce: any = null;
        for (let i = 0; i < 6; i += 1) {
          reqForce = await triggerV3GenerateAndCapture(page);
          const n = Array.isArray((reqForce as any)?.forceFillBars) ? (reqForce as any).forceFillBars.length : 0;
          if (n > 0) break;
          await page.waitForTimeout(100);
        }
        expect(Array.isArray((reqForce as any)?.forceFillBars) ? (reqForce as any).forceFillBars.length : 0).toBeGreaterThan(0);

        await force.setChecked(false);

        const suppress = sectionPanel.getByTestId('v3.bar.suppressFill');
        await expect(suppress).toBeVisible({ timeout: 60_000 });
        await expect(suppress).toBeEnabled({ timeout: 60_000 });
        await suppress.setChecked(true);
        await expect(suppress).toBeChecked({ timeout: 60_000 });

        let reqSuppress: any = null;
        for (let i = 0; i < 6; i += 1) {
          reqSuppress = await triggerV3GenerateAndCapture(page);
          const n = Array.isArray((reqSuppress as any)?.suppressFillBars) ? (reqSuppress as any).suppressFillBars.length : 0;
          if (n > 0) break;
          await page.waitForTimeout(100);
        }
        expect(Array.isArray((reqSuppress as any)?.suppressFillBars) ? (reqSuppress as any).suppressFillBars.length : 0).toBeGreaterThan(0);

        return { reqForce, reqSuppress };
      },
    },

    {
      controlName: 'V3 UI: Measure Range (selected section) affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const selectedSectionRadio = page.getByRole('radio', { name: /Selected\s*section/i }).first();
        await expect(selectedSectionRadio).toBeVisible({ timeout: 60_000 });
        await selectedSectionRadio.check();

        const reqSel = await triggerV3GenerateAndCapture(page);

        const fullSongRadio = page.getByRole('radio', { name: /Full\s*song/i }).first();
        await expect(fullSongRadio).toBeVisible({ timeout: 60_000 });
        await fullSongRadio.check();

        const reqFull = await triggerV3GenerateAndCapture(page);

        expect(Number((reqSel as any)?.endMeasure ?? -1)).toBeGreaterThanOrEqual(Number((reqSel as any)?.startMeasure ?? 0));
        expect(String((reqSel as any)?.buildScope || '')).toBe('selected_section');
        expect(String((reqFull as any)?.buildScope || '')).toBe('full_song');
        expect(Number((reqFull as any)?.endMeasure ?? -1)).toBeGreaterThanOrEqual(Number((reqFull as any)?.startMeasure ?? 0));

        return { reqSel, reqFull };
      },
    },

    {
      controlName: 'V3 UI: Guide Enabled affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        await v3EnsureBuildScopeSelectedSection(page);
        await v3SelectFirstSection(page);

        const guideOverride = page.getByTestId('v3.section.inherit.guide.override');
        await expect(guideOverride).toBeVisible({ timeout: 60_000 });
        await guideOverride.check();

        const enabled = page.getByTestId('v3.section.guide.enabled');
        await expect(enabled).toBeVisible({ timeout: 60_000 });

        await enabled.setChecked(false);
        const reqOff = await triggerV3GenerateAndCapture(page);

        await enabled.setChecked(true);
        const reqOn = await triggerV3GenerateAndCapture(page);

        expect(Boolean((reqOff as any)?.guideEnabled)).toBe(false);
        expect(Boolean((reqOn as any)?.guideEnabled)).toBe(true);

        return { reqOff, reqOn };
      },
    },

    {
      controlName: 'V3 UI: Guide Instrument affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        await v3EnsureBuildScopeSelectedSection(page);
        await v3SelectFirstSection(page);

        const guideOverride = page.getByTestId('v3.section.inherit.guide.override');
        await expect(guideOverride).toBeVisible({ timeout: 60_000 });
        await guideOverride.check();

        const enabled = page.getByTestId('v3.section.guide.enabled');
        await expect(enabled).toBeVisible({ timeout: 60_000 });
        await enabled.setChecked(true);

        const inst = page.getByTestId('v3.section.guide.instrument');
        await expect(inst).toBeVisible({ timeout: 60_000 });
        await expect(inst).toBeEnabled({ timeout: 60_000 });

        const before = await triggerV3GenerateAndCapture(page);
        const beforeVal = String((before as any)?.guideInstrument || '');

        const opts = await inst.locator('option').all();
        const values: string[] = [];
        for (const opt of opts) {
          const v = await opt.getAttribute('value');
          if (v) values.push(v);
        }
        const next = values.find((v) => v && v !== beforeVal) || values[0];
        if (!next) throw new Error('No guide instrument options found');

        await inst.selectOption(next);
        const after = await triggerV3GenerateAndCapture(page);

        expect(String((after as any)?.guideInstrument || '')).toBe(String(next));
        expect(String((after as any)?.guideInstrument || '')).not.toBe(beforeVal);

        return { before, after };
      },
    },

    {
      controlName: 'DCSM Drum Editor > Generate Groove',
      run: async ({ page }) => {
        await ensureLegacyDrumEditorReady(page);

        const beforeState = await getLegacyDrumEditorState(page);
        const beforeCount = Array.isArray((beforeState as any)?.notesPreview)
          ? (beforeState as any).notesPreview.length
          : 0;

        const btn = page.getByTestId('dcsm.drumEditor.generateGroove');
        await expect(btn).toBeVisible({ timeout: 60_000 });
        await btn.click({ force: true });

        await waitForLegacyNotesPreviewCountToBeAtLeast(page, Math.max(1, beforeCount));
        const afterState = await getLegacyDrumEditorState(page);
        const afterCount = Array.isArray((afterState as any)?.notesPreview)
          ? (afterState as any).notesPreview.length
          : 0;
        if (!(afterCount >= 1)) {
          throw new Error(`Expected notesPreview after generate. beforeCount=${beforeCount} afterCount=${afterCount}`);
        }

        return { beforeCount, afterCount };
      },
    },

    {
      controlName: 'DrumGrid > Select notes',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const selected = await getLegacySelectedNote(page);
        if (!selected?.id) throw new Error('Expected a selected note');
        return { selectedId: selected.id, selected };
      },
    },

    {
      controlName: 'DrumGrid > Move notes',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page, { requireNotAtStart: true });
        const before = await getLegacySelectedNote(page);
        if (!before?.id) throw new Error('Expected a selected note');

        await dragSelectedNoteByPixels(page, { noteId: before.id, dx: 60, dy: 0 });
        await waitForSelectedNoteTicksToChange(page, before);
        const after = await getLegacySelectedNote(page);

        return { before, after };
      },
    },

    {
      controlName: 'DrumGrid > Resize notes',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);
        if (!before?.id) throw new Error('Expected a selected note');

        const beforeLen = Number((before as any)?.tickLength ?? 0);
        await dragSelectedNoteByPixels(page, { noteId: before.id, startOffsetFromRightPx: 2, dx: 60, dy: 0 });
        await waitForSelectedNoteFieldToChange(page, 'tickLength', beforeLen);
        const after = await getLegacySelectedNote(page);

        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Priority updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);

        const beforeVal = Number(before?.priority ?? 0.5);
        const targetFrac = beforeVal >= 0.7 ? 0.2 : 0.85;
        await clickRangeByTestId(page, 'noteInspector.priority', targetFrac);

        await waitForSelectedNoteFieldToChange(page, 'priority', beforeVal);
        const after = await getLegacySelectedNote(page);
        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Nudge earlier/later (grid step) updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page, { requireNotAtStart: true });
        const before = await getLegacySelectedNote(page);

        const earlier = page.getByTestId('noteInspector.nudge.earlier');
        await expect(earlier).toBeVisible({ timeout: 60_000 });
        await earlier.click({ force: true });

        await waitForSelectedNoteTicksToChange(page, before);
        const afterEarlier = await getLegacySelectedNote(page);

        const later = page.getByTestId('noteInspector.nudge.later');
        await expect(later).toBeVisible({ timeout: 60_000 });
        await later.click({ force: true });

        await waitForSelectedNoteTicksToChange(page, afterEarlier ?? {});
        const after = await getLegacySelectedNote(page);
        return { before, afterEarlier, after };
      },
    },

    {
      controlName: 'Drum Options Panel > Fill Density affects generate payload',
      run: async ({ page }) => {
        await ensureLegacyReady(page);

        await ensureDrumOptionsSectionExpanded(page, /Fill Options/i, 'drumOptions.fills.density.knob');
        const knob = page.getByTestId('drumOptions.fills.density.knob');
        await expect(knob).toBeVisible({ timeout: 60_000 });

        const before = await triggerLegacyFullSongGenerateAndCapture(page);
        const beforeVal = (before as any)?.fillDensity;

        // Note: full-song config clamps fillDensity to <= 0.55, so the default often starts at 0.55.
        // Dragging downward (positive dy) decreases the value; prefer decreases so we can observe change.
        const dYs = [160, 240, 320];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.fills.density.knob', dYs[i]);
          const after = await triggerLegacyFullSongGenerateAndCapture(page);
          const afterVal = (after as any)?.fillDensity;
          if (afterVal !== beforeVal) {
            return { before, after };
          }
        }

        const last = await triggerLegacyFullSongGenerateAndCapture(page);
        throw new Error(
          `Legacy knob did not change payload.fillDensity. Before=${JSON.stringify(beforeVal)} After=${JSON.stringify((last as any)?.fillDensity)}`
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Fine Swing Amount affects generate payload',
      run: async ({ page }) => {
        await ensureLegacyReady(page);

        await ensureDrumOptionsSectionExpanded(page, /Groove Options/i, 'drumOptions.groove.swing.knob');
        const knob = page.getByTestId('drumOptions.groove.swing.knob');
        await expect(knob).toBeVisible({ timeout: 60_000 });

        const before = await triggerLegacyFullSongGenerateAndCapture(page);
        const beforeVal = (before as any)?.swingAmount;

        const dYs = [-80, 80, -140, 140];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.groove.swing.knob', dYs[i]);
          const after = await triggerLegacyFullSongGenerateAndCapture(page);
          const afterVal = (after as any)?.swingAmount;
          if (afterVal !== beforeVal) {
            return { before, after };
          }
        }

        const last = await triggerLegacyFullSongGenerateAndCapture(page);
        throw new Error(
          `Legacy knob did not change payload.swingAmount. Before=${JSON.stringify(beforeVal)} After=${JSON.stringify((last as any)?.swingAmount)}`
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Ghost Note Density affects generate payload',
      run: async ({ page }) => {
        await ensureLegacyReady(page);

        await ensureDrumOptionsSectionExpanded(page, /Additional Controls/i, 'drumOptions.additional.ghostNoteDensity.knob');

        const knob = page.getByTestId('drumOptions.additional.ghostNoteDensity.knob');
        await expect(knob).toBeVisible({ timeout: 60_000 });

        const before = await triggerLegacyFullSongGenerateAndCapture(page);
        const beforeVal = (before as any)?.ghostNoteAmount;

        const dYs = [-80, 80, -140, 140];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.additional.ghostNoteDensity.knob', dYs[i]);
          const after = await triggerLegacyFullSongGenerateAndCapture(page);
          const afterVal = (after as any)?.ghostNoteAmount;
          if (afterVal !== beforeVal) {
            return { before, after };
          }
        }

        const last = await triggerLegacyFullSongGenerateAndCapture(page);
        throw new Error(
          `Legacy knob did not change payload.ghostNoteAmount. Before=${JSON.stringify(beforeVal)} After=${JSON.stringify((last as any)?.ghostNoteAmount)}`
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Velocity (Volume) > Drums updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Velocity \(Volume\)/i, 'drumOptions.velocity.drums.knob');

        const beforeVal = await getLegacyDrumOption(page, 'drum_velocity');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.velocity.drums.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'drum_velocity');
          if (afterVal !== beforeVal) {
            return { before: { drum_velocity: beforeVal }, after: { drum_velocity: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'drum_velocity');
        throw new Error(
          `Velocity (Drums) knob did not change __DTK_STATE__.drumOptions.drum_velocity. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Velocity (Volume) > Cymbals updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Velocity \(Volume\)/i, 'drumOptions.velocity.cymbals.knob');

        const beforeVal = await getLegacyDrumOption(page, 'cymbal_velocity');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.velocity.cymbals.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'cymbal_velocity');
          if (afterVal !== beforeVal) {
            return { before: { cymbal_velocity: beforeVal }, after: { cymbal_velocity: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'cymbal_velocity');
        throw new Error(
          `Velocity (Cymbals) knob did not change __DTK_STATE__.drumOptions.cymbal_velocity. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Instrument Density (Complexity) > Drums updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Instrument Density \(Complexity\)/i, 'drumOptions.density.drums.knob');

        const beforeVal = await getLegacyDrumOption(page, 'drum_density');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.density.drums.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'drum_density');
          if (afterVal !== beforeVal) {
            return { before: { drum_density: beforeVal }, after: { drum_density: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'drum_density');
        throw new Error(
          `Density (Drums) knob did not change __DTK_STATE__.drumOptions.drum_density. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Individual Cymbal Density > Hi-Hat updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Instrument Density \(Complexity\)/i, 'drumOptions.density.drums.knob');
        await ensureDetailsExpanded(page, /Individual Cymbal Density/i);

        const beforeVal = await getLegacyDrumOption(page, 'hihat_density');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.density.hihat.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'hihat_density');
          if (afterVal !== beforeVal) {
            return { before: { hihat_density: beforeVal }, after: { hihat_density: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'hihat_density');
        throw new Error(
          `Density (Hi-Hat) knob did not change __DTK_STATE__.drumOptions.hihat_density. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Instrument Density (Complexity) > Cymbals updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Instrument Density \(Complexity\)/i, 'drumOptions.density.cymbals.knob');

        const beforeVal = await getLegacyDrumOption(page, 'cymbal_density');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.density.cymbals.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'cymbal_density');
          if (afterVal !== beforeVal) {
            return { before: { cymbal_density: beforeVal }, after: { cymbal_density: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'cymbal_density');
        throw new Error(
          `Density (Cymbals) knob did not change __DTK_STATE__.drumOptions.cymbal_density. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Individual Cymbal Density > Ride updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Instrument Density \(Complexity\)/i, 'drumOptions.density.drums.knob');
        await ensureDetailsExpanded(page, /Individual Cymbal Density/i);

        const beforeVal = await getLegacyDrumOption(page, 'ride_density');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.density.ride.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'ride_density');
          if (afterVal !== beforeVal) {
            return { before: { ride_density: beforeVal }, after: { ride_density: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'ride_density');
        throw new Error(
          `Density (Ride) knob did not change __DTK_STATE__.drumOptions.ride_density. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Individual Cymbal Density > Crash updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Instrument Density \(Complexity\)/i, 'drumOptions.density.drums.knob');
        await ensureDetailsExpanded(page, /Individual Cymbal Density/i);

        const beforeVal = await getLegacyDrumOption(page, 'crash_density');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.density.crash.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'crash_density');
          if (afterVal !== beforeVal) {
            return { before: { crash_density: beforeVal }, after: { crash_density: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'crash_density');
        throw new Error(
          `Density (Crash) knob did not change __DTK_STATE__.drumOptions.crash_density. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Velocity (Volume) > Kick updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Velocity \(Volume\)/i, 'drumOptions.velocity.drums.knob');
        await ensureDetailsExpanded(page, /Individual Instrument Volumes/i);

        const beforeVal = await getLegacyDrumOption(page, 'kick_velocity');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.velocity.kick.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'kick_velocity');
          if (afterVal !== beforeVal) {
            return { before: { kick_velocity: beforeVal }, after: { kick_velocity: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'kick_velocity');
        throw new Error(
          `Velocity (Kick) knob did not change __DTK_STATE__.drumOptions.kick_velocity. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Velocity (Volume) > Snare updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Velocity \(Volume\)/i, 'drumOptions.velocity.drums.knob');
        await ensureDetailsExpanded(page, /Individual Instrument Volumes/i);

        const beforeVal = await getLegacyDrumOption(page, 'snare_velocity');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.velocity.snare.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'snare_velocity');
          if (afterVal !== beforeVal) {
            return { before: { snare_velocity: beforeVal }, after: { snare_velocity: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'snare_velocity');
        throw new Error(
          `Velocity (Snare) knob did not change __DTK_STATE__.drumOptions.snare_velocity. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Fill Options > Fill Location updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Fill Options/i, 'drumOptions.fills.fillType');

        const beforeVal = await getLegacyDrumOption(page, 'fill_location');
        const select = page.getByTestId('drumOptions.fills.location');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const candidates = ['auto', 'end', 'middle', 'front'];
        const next = candidates.find((v) => v !== beforeVal) ?? 'auto';
        await select.selectOption(next);

        await page.waitForTimeout(150);
        const afterVal = await getLegacyDrumOption(page, 'fill_location');
        if (afterVal === beforeVal) {
          throw new Error(`Expected fill_location to change. Before=${beforeVal} After=${afterVal}`);
        }
        return { before: { fill_location: beforeVal }, after: { fill_location: afterVal } };
      },
    },

    {
      controlName: 'Drum Options Panel > Fill Options > Fill Frequency updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Fill Options/i, 'drumOptions.fills.fillType');

        const beforeVal = await getLegacyDrumOption(page, 'fill_frequency');
        const input = page.getByTestId('drumOptions.fills.frequency');
        await expect(input).toBeVisible({ timeout: 60_000 });

        await input.fill('');
        await input.type('7');
        await input.blur();

        await page.waitForTimeout(150);
        const afterVal = await getLegacyDrumOption(page, 'fill_frequency');
        if (afterVal === beforeVal) {
          throw new Error(`Expected fill_frequency to change. Before=${beforeVal} After=${afterVal}`);
        }
        return { before: { fill_frequency: beforeVal }, after: { fill_frequency: afterVal } };
      },
    },

    {
      controlName: 'Drum Options Panel > Groove Options > Swing Preset updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Groove Options/i, 'drumOptions.groove.swingPreset');

        const beforeVal = await getLegacyDrumOption(page, 'swing_preset');
        const select = page.getByTestId('drumOptions.groove.swingPreset');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const candidates = ['off', 'light', 'heavy'];
        const next = candidates.find((v) => v !== beforeVal) ?? 'light';
        await select.selectOption(next);

        await page.waitForTimeout(150);
        const afterVal = await getLegacyDrumOption(page, 'swing_preset');
        if (afterVal === beforeVal) {
          throw new Error(`Expected swing_preset to change. Before=${beforeVal} After=${afterVal}`);
        }
        return { before: { swing_preset: beforeVal }, after: { swing_preset: afterVal } };
      },
    },

    {
      controlName: 'Drum Options Panel > Groove Options > Velocity Pattern updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Groove Options/i, 'drumOptions.groove.swingPreset');

        const beforeVal = await getLegacyDrumOption(page, 'vel_preset');
        const select = page.getByTestId('drumOptions.groove.velocityPattern');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const candidates = ['flat', 'accent24', 'funk16'];
        const next = candidates.find((v) => v !== beforeVal) ?? 'flat';
        await select.selectOption(next);

        await page.waitForTimeout(150);
        const afterVal = await getLegacyDrumOption(page, 'vel_preset');
        if (afterVal === beforeVal) {
          throw new Error(`Expected vel_preset to change. Before=${beforeVal} After=${afterVal}`);
        }
        return { before: { vel_preset: beforeVal }, after: { vel_preset: afterVal } };
      },
    },

    {
      controlName: 'Drum Options Panel > Hi-Hat Articulation > Presets update state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Hi-Hat Articulation/i, 'drumOptions.hihat.complexity.knob');

        const before = {
          hihat_pattern: await getLegacyDrumOption(page, 'hihat_pattern'),
          hihat_open_ratio: await getLegacyDrumOption(page, 'hihat_open_ratio'),
          hihat_complexity: await getLegacyDrumOption(page, 'hihat_complexity'),
        };

        const candidates = ['standard', 'funk', 'latin'];
        const presetId = candidates.find((v) => v !== before.hihat_pattern) ?? 'funk';
        const presetBtn = page.getByTestId(`drumOptions.hihat.preset.${presetId}`);
        await expect(presetBtn).toBeVisible({ timeout: 60_000 });
        await presetBtn.click();

        await page.waitForTimeout(150);
        const after = {
          hihat_pattern: await getLegacyDrumOption(page, 'hihat_pattern'),
          hihat_open_ratio: await getLegacyDrumOption(page, 'hihat_open_ratio'),
          hihat_complexity: await getLegacyDrumOption(page, 'hihat_complexity'),
        };

        const changed =
          after.hihat_pattern !== before.hihat_pattern ||
          after.hihat_open_ratio !== before.hihat_open_ratio ||
          after.hihat_complexity !== before.hihat_complexity;
        if (!changed) {
          throw new Error(`Expected hi-hat preset click to change state. Before=${JSON.stringify(before)} After=${JSON.stringify(after)}`);
        }
        return { before, after };
      },
    },

    {
      controlName: 'Drum Options Panel > Hi-Hat Complexity updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Hi-Hat Articulation/i, 'drumOptions.hihat.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'hihat_complexity');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.hihat.complexity.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'hihat_complexity');
          if (afterVal !== beforeVal) {
            return { before: { hihat_complexity: beforeVal }, after: { hihat_complexity: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'hihat_complexity');
        throw new Error(
          `Hi-Hat Complexity knob did not change __DTK_STATE__.drumOptions.hihat_complexity. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Hi-Hat Pattern updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Hi-Hat Articulation/i, 'drumOptions.hihat.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'hihat_pattern');
        const select = page.getByTestId('drumOptions.hihat.pattern');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const candidates = ['standard', 'disco', 'funk', 'latin', 'techno', 'jazz'];
        const next = candidates.find((v) => v !== beforeVal) ?? 'funk';
        await select.selectOption(next);

        await page.waitForTimeout(150);
        const afterVal = await getLegacyDrumOption(page, 'hihat_pattern');
        if (afterVal === beforeVal) {
          throw new Error(`Expected hihat_pattern to change. Before=${beforeVal} After=${afterVal}`);
        }
        return { before: { hihat_pattern: beforeVal }, after: { hihat_pattern: afterVal } };
      },
    },

    {
      controlName: 'Drum Options Panel > Hi-Hat Open Ratio updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Hi-Hat Articulation/i, 'drumOptions.hihat.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'hihat_open_ratio');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.hihat.openRatio.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'hihat_open_ratio');
          if (afterVal !== beforeVal) {
            return { before: { hihat_open_ratio: beforeVal }, after: { hihat_open_ratio: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'hihat_open_ratio');
        throw new Error(
          `Hi-Hat Open Ratio knob did not change __DTK_STATE__.drumOptions.hihat_open_ratio. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Hi-Hat Ghost Notes updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Hi-Hat Articulation/i, 'drumOptions.hihat.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'hihat_ghost_notes');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.hihat.ghostNotes.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'hihat_ghost_notes');
          if (afterVal !== beforeVal) {
            return { before: { hihat_ghost_notes: beforeVal }, after: { hihat_ghost_notes: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'hihat_ghost_notes');
        throw new Error(
          `Hi-Hat Ghost Notes knob did not change __DTK_STATE__.drumOptions.hihat_ghost_notes. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Ride Cymbal Dynamics > Presets update state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Ride Cymbal Dynamics/i, 'drumOptions.ride.complexity.knob');

        const before = {
          ride_pattern: await getLegacyDrumOption(page, 'ride_pattern'),
          ride_bell_ratio: await getLegacyDrumOption(page, 'ride_bell_ratio'),
          ride_vs_hihat_ratio: await getLegacyDrumOption(page, 'ride_vs_hihat_ratio'),
        };

        const candidates = ['rock', 'jazz', 'fusion', 'latin'];
        const presetId = candidates.find((v) => v !== before.ride_pattern) ?? 'jazz';
        const presetBtn = page.getByTestId(`drumOptions.ride.preset.${presetId}`);
        await expect(presetBtn).toBeVisible({ timeout: 60_000 });
        await presetBtn.click();

        await page.waitForTimeout(150);
        const after = {
          ride_pattern: await getLegacyDrumOption(page, 'ride_pattern'),
          ride_bell_ratio: await getLegacyDrumOption(page, 'ride_bell_ratio'),
          ride_vs_hihat_ratio: await getLegacyDrumOption(page, 'ride_vs_hihat_ratio'),
        };

        const changed =
          after.ride_pattern !== before.ride_pattern ||
          after.ride_bell_ratio !== before.ride_bell_ratio ||
          after.ride_vs_hihat_ratio !== before.ride_vs_hihat_ratio;
        if (!changed) {
          throw new Error(`Expected ride preset click to change state. Before=${JSON.stringify(before)} After=${JSON.stringify(after)}`);
        }
        return { before, after };
      },
    },

    {
      controlName: 'Drum Options Panel > Ride Complexity updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Ride Cymbal Dynamics/i, 'drumOptions.ride.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'ride_complexity');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.ride.complexity.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'ride_complexity');
          if (afterVal !== beforeVal) {
            return { before: { ride_complexity: beforeVal }, after: { ride_complexity: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'ride_complexity');
        throw new Error(
          `Ride Complexity knob did not change __DTK_STATE__.drumOptions.ride_complexity. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Ride Pattern updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Ride Cymbal Dynamics/i, 'drumOptions.ride.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'ride_pattern');
        const select = page.getByTestId('drumOptions.ride.pattern');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const candidates = ['rock', 'jazz', 'fusion', 'latin'];
        const next = candidates.find((v) => v !== beforeVal) ?? 'fusion';
        await select.selectOption(next);

        await page.waitForTimeout(150);
        const afterVal = await getLegacyDrumOption(page, 'ride_pattern');
        if (afterVal === beforeVal) {
          throw new Error(`Expected ride_pattern to change. Before=${beforeVal} After=${afterVal}`);
        }
        return { before: { ride_pattern: beforeVal }, after: { ride_pattern: afterVal } };
      },
    },

    {
      controlName: 'Drum Options Panel > Ride vs Hat updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Ride Cymbal Dynamics/i, 'drumOptions.ride.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'ride_vs_hihat_ratio');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.ride.rideVsHat.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'ride_vs_hihat_ratio');
          if (afterVal !== beforeVal) {
            return { before: { ride_vs_hihat_ratio: beforeVal }, after: { ride_vs_hihat_ratio: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'ride_vs_hihat_ratio');
        throw new Error(
          `Ride vs Hat knob did not change __DTK_STATE__.drumOptions.ride_vs_hihat_ratio. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Bell Ratio updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Ride Cymbal Dynamics/i, 'drumOptions.ride.complexity.knob');

        const beforeVal = await getLegacyDrumOption(page, 'ride_bell_ratio');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.ride.bellRatio.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'ride_bell_ratio');
          if (afterVal !== beforeVal) {
            return { before: { ride_bell_ratio: beforeVal }, after: { ride_bell_ratio: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'ride_bell_ratio');
        throw new Error(
          `Bell Ratio knob did not change __DTK_STATE__.drumOptions.ride_bell_ratio. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Additional Controls > Tom Usage updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Additional Controls/i, 'drumOptions.additional.tomUsage.knob');

        const beforeVal = await getLegacyDrumOption(page, 'tom_usage');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.additional.tomUsage.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'tom_usage');
          if (afterVal !== beforeVal) {
            return { before: { tom_usage: beforeVal }, after: { tom_usage: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'tom_usage');
        throw new Error(
          `Tom Usage knob did not change __DTK_STATE__.drumOptions.tom_usage. Before=${JSON.stringify(beforeVal)} After=${JSON.stringify(
            last,
          )}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Additional Controls > Crash Frequency updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Additional Controls/i, 'drumOptions.additional.tomUsage.knob');

        const beforeVal = await getLegacyDrumOption(page, 'crash_frequency');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.additional.crashFrequency.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'crash_frequency');
          if (afterVal !== beforeVal) {
            return { before: { crash_frequency: beforeVal }, after: { crash_frequency: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'crash_frequency');
        throw new Error(
          `Crash Frequency knob did not change __DTK_STATE__.drumOptions.crash_frequency. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Additional Controls > Dynamic Range updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Additional Controls/i, 'drumOptions.additional.tomUsage.knob');

        const beforeVal = await getLegacyDrumOption(page, 'dynamic_range');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.additional.dynamicRange.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'dynamic_range');
          if (afterVal !== beforeVal) {
            return { before: { dynamic_range: beforeVal }, after: { dynamic_range: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'dynamic_range');
        throw new Error(
          `Dynamic Range knob did not change __DTK_STATE__.drumOptions.dynamic_range. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Low-End Lock > Bass Line Mode updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Low-End Lock/i, 'drumOptions.bass.kickBassSync.knob');

        const beforeVal = await getLegacyDrumOption(page, 'bass_line_mode');
        const select = page.getByTestId('drumOptions.bass.bassLineMode');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const candidates = ['ignore', 'follow', 'complement', 'locked'];
        const next = candidates.find((v) => v !== beforeVal) ?? 'follow';
        await select.selectOption(next);

        await page.waitForTimeout(150);
        const afterVal = await getLegacyDrumOption(page, 'bass_line_mode');

        if (afterVal === beforeVal) {
          throw new Error(
            `Bass Line Mode select did not change __DTK_STATE__.drumOptions.bass_line_mode. Before=${JSON.stringify(
              beforeVal,
            )} After=${JSON.stringify(afterVal)}`,
          );
        }

        return { before: { bass_line_mode: beforeVal }, after: { bass_line_mode: afterVal } };
      },
    },

    {
      controlName: 'Drum Options Panel > Low-End Lock > Kick-Bass Sync updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Low-End Lock/i, 'drumOptions.bass.kickBassSync.knob');

        const beforeVal = await getLegacyDrumOption(page, 'bass_kick_sync');
        const dYs = [-160, 160, -240, 240];
        for (let i = 0; i < dYs.length; i += 1) {
          await v3AdjustKnobByDragTestId(page, 'drumOptions.bass.kickBassSync.knob', dYs[i]);
          const afterVal = await getLegacyDrumOption(page, 'bass_kick_sync');
          if (afterVal !== beforeVal) {
            return { before: { bass_kick_sync: beforeVal }, after: { bass_kick_sync: afterVal } };
          }
        }

        const last = await getLegacyDrumOption(page, 'bass_kick_sync');
        throw new Error(
          `Kick-Bass Sync knob did not change __DTK_STATE__.drumOptions.bass_kick_sync. Before=${JSON.stringify(
            beforeVal,
          )} After=${JSON.stringify(last)}`,
        );
      },
    },

    {
      controlName: 'Drum Options Panel > Low-End Lock > Lock Kick to Bass Downbeats updates state',
      run: async ({ page }) => {
        await ensureLegacyReady(page);
        await ensureDrumOptionsSectionExpanded(page, /Low-End Lock/i, 'drumOptions.bass.kickBassSync.knob');

        const beforeVal = await getLegacyDrumOption(page, 'bass_lock_downbeats');
        const checkbox = page.getByTestId('drumOptions.bass.lockDownbeats');
        await expect(checkbox).toBeVisible({ timeout: 60_000 });

        await checkbox.click();
        await page.waitForTimeout(150);

        const afterVal = await getLegacyDrumOption(page, 'bass_lock_downbeats');
        if (afterVal === beforeVal) {
          throw new Error(
            `Lock Kick to Bass Downbeats checkbox did not change __DTK_STATE__.drumOptions.bass_lock_downbeats. Before=${JSON.stringify(
              beforeVal,
            )} After=${JSON.stringify(afterVal)}`,
          );
        }

        return { before: { bass_lock_downbeats: beforeVal }, after: { bass_lock_downbeats: afterVal } };
      },
    },

    {
      controlName: 'Drum Performance Editor > View filter (ALL/GROOVE/ACCENT/FILL) updates state',
      run: async ({ page }) => {
        await ensureLegacyDrumEditorReady(page);

        const before = await getLegacyDrumEditorState(page);
        const candidates = ['all', 'groove', 'accent', 'fill'];

        let changed: any = null;
        for (let i = 0; i < candidates.length; i += 1) {
          const opt = candidates[i];
          const btn = page.getByTestId(`drumEditor.view.${opt}`);
          await expect(btn).toBeVisible({ timeout: 60_000 });
          await btn.click();
          await page.waitForTimeout(100);
          const after = await getLegacyDrumEditorState(page);
          if (after?.currentAspect !== before?.currentAspect) {
            changed = { before, after };
            break;
          }
        }

        if (!changed) {
          const last = await getLegacyDrumEditorState(page);
          throw new Error(
            `View filter did not change __DTK_STATE__.drumEditor.currentAspect. Before=${JSON.stringify(
              before,
            )} After=${JSON.stringify(last)}`,
          );
        }

        return changed;
      },
    },

    {
      controlName: 'Drum Performance Editor > Grid resolution (16th/32nd/64th) updates state',
      run: async ({ page }) => {
        await ensureLegacyDrumEditorReady(page);

        const before = await getLegacyDrumEditorState(page);
        const candidates = ['16th', '32nd', '64th'];

        let changed: any = null;
        for (let i = 0; i < candidates.length; i += 1) {
          const opt = candidates[i];
          const btn = page.getByTestId(`drumEditor.grid.${opt}`);
          await expect(btn).toBeVisible({ timeout: 60_000 });
          await btn.click();
          await page.waitForTimeout(100);
          const after = await getLegacyDrumEditorState(page);
          if (after?.gridResolution !== before?.gridResolution) {
            changed = { before, after };
            break;
          }
        }

        if (!changed) {
          const last = await getLegacyDrumEditorState(page);
          throw new Error(
            `Grid resolution did not change __DTK_STATE__.drumEditor.gridResolution. Before=${JSON.stringify(
              before,
            )} After=${JSON.stringify(last)}`,
          );
        }

        return changed;
      },
    },

    {
      controlName: 'Note Inspector > Velocity updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);

        const beforeVal = Number(before?.velocity ?? 0);
        const targetFrac = beforeVal >= 80 ? 0.25 : 0.8;
        await clickRangeByTestId(page, 'noteInspector.velocity', targetFrac);

        await waitForSelectedNoteFieldToChange(page, 'velocity', beforeVal);
        const after = await getLegacySelectedNote(page);
        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Timing Offset updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);

        const beforeVal = Number(before?.timingOffsetMs ?? 0);
        const next = beforeVal >= 10 ? -10 : 10;
        await setRangeValueByTestId(page, 'noteInspector.timingOffsetMs', next);

        await waitForSelectedNoteFieldToChange(page, 'timingOffsetMs', beforeVal);
        const after = await getLegacySelectedNote(page);
        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Hat Open Level updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page, { instrumentPrefix: 'hihat' });
        const before = await getLegacySelectedNote(page);

        const beforeVal = Number(before?.hatOpenLevel ?? 0);
        const targetFrac = beforeVal >= 0.5 ? 0.2 : 0.8;
        await clickRangeByTestId(page, 'noteInspector.hatOpenLevel', targetFrac);

        await waitForSelectedNoteFieldToChange(page, 'hatOpenLevel', beforeVal);
        const after = await getLegacySelectedNote(page);
        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Limb updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);
        const beforeVal = String(before?.limbId ?? 'other');

        const select = page.getByTestId('noteInspector.limb');
        await expect(select).toBeVisible({ timeout: 60_000 });
        const next = beforeVal === 'RH' ? 'LH' : 'RH';
        await select.selectOption(next);
        await page.waitForTimeout(100);

        const after = await getLegacySelectedNote(page);
        if (String(after?.limbId ?? 'other') === beforeVal) {
          throw new Error(`Limb did not change. Before=${JSON.stringify(before)} After=${JSON.stringify(after)}`);
        }
        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Hit Style updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);
        const beforeVal = String(before?.hitStyle ?? '');

        const candidates = ['single', 'double', 'bounce'];
        const next = candidates.find((c) => c !== beforeVal) ?? 'double';
        const radio = page.getByTestId(`noteInspector.hitStyle.${next}`);
        await expect(radio).toBeVisible({ timeout: 60_000 });
        await radio.check().catch(async () => {
          await radio.click({ force: true });
        });
        await page.waitForTimeout(100);

        const after = await getLegacySelectedNote(page);
        if (String(after?.hitStyle ?? '') === beforeVal) {
          throw new Error(
            `Hit Style did not change. Before=${JSON.stringify(before)} After=${JSON.stringify(after)}`,
          );
        }
        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Lock updates selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);
        const beforeVal = !!before?.locked;

        const checkbox = page.getByTestId('noteInspector.lock');
        await expect(checkbox).toBeVisible({ timeout: 60_000 });
        await checkbox.click({ force: true });

        await waitForSelectedNoteFieldToChange(page, 'locked', beforeVal);
        const after = await getLegacySelectedNote(page);
        return { before, after };
      },
    },

    {
      controlName: 'Note Inspector > Flags (ghost/accent/flam/drag) update selected note',
      run: async ({ page }) => {
        await ensureLegacyFirstNoteSelected(page);
        const before = await getLegacySelectedNote(page);

        const ghost = page.getByTestId('noteInspector.flag.ghost');
        await expect(ghost).toBeVisible({ timeout: 60_000 });
        await ghost.click({ force: true });

        await waitForSelectedNoteFieldToChange(page, 'isGhost', !!before?.isGhost);
        const after = await getLegacySelectedNote(page);
        return { before, after };
      },
    },
    {
      controlName: 'UI: Manual Arrangement modal opens and cancels',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);

        const { modalHeading } = await openManualArrangementModal(page);

        const cancelBtn = page.getByRole('button', { name: /^Cancel$/i }).first();
        await expect(cancelBtn).toBeVisible({ timeout: 60_000 });
        await cancelBtn.click();

        await expect(modalHeading).toBeHidden({ timeout: 60_000 });

        return {
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'Manual Arrangement > Global Tempo (BPM) input edits value',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot } = await openManualArrangementModal(page);

        const tempoInput = modalNumberInputByLabel(modalRoot, /Global Tempo \(BPM\)/i);
        await expect(tempoInput).toBeVisible({ timeout: 60_000 });

        const beforeValue = await tempoInput.inputValue();
        const nextTempo = 137;
        await tempoInput.fill(String(nextTempo));
        await tempoInput.press('Tab');

        await expect(tempoInput).toHaveValue(String(nextTempo), { timeout: 60_000 });

        const cancelBtn = modalRoot.getByRole('button', { name: /^Cancel$/i }).first();
        await expect(cancelBtn).toBeVisible({ timeout: 60_000 });
        await cancelBtn.click();

        return {
          beforeValue,
          afterValue: nextTempo,
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'Manual Arrangement > Time Signature edits (beats + unit)',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot } = await openManualArrangementModal(page);

        const beatsInput = modalNumberInputByLabel(modalRoot, /^Time Signature$/i);
        const unitSelect = modalSelectByLabel(modalRoot, /^Time Signature$/i);
        await expect(beatsInput).toBeVisible({ timeout: 60_000 });
        await expect(unitSelect).toBeVisible({ timeout: 60_000 });

        const beforeBeats = await beatsInput.inputValue();
        const beforeUnit = await unitSelect.inputValue();

        await beatsInput.fill('3');
        await beatsInput.press('Tab');
        await expect(beatsInput).toHaveValue('3', { timeout: 60_000 });

        await unitSelect.selectOption({ value: '8' });
        await expect(unitSelect).toHaveValue('8', { timeout: 60_000 });

        const cancelBtn = modalRoot.getByRole('button', { name: /^Cancel$/i }).first();
        await expect(cancelBtn).toBeVisible({ timeout: 60_000 });
        await cancelBtn.click();

        return {
          before: { beats: beforeBeats, unit: beforeUnit },
          after: { beats: '3', unit: '8' },
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'Manual Arrangement > Add Section adds a row',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot } = await openManualArrangementModal(page);

        const songSectionsHeader = modalRoot.getByRole('heading', { name: /Song Sections/i }).first();
        await expect(songSectionsHeader).toBeVisible({ timeout: 60_000 });

        const sectionCards = () => modalRoot.locator('div.p-3.bg-slate-900.rounded.border');
        const beforeCount = await sectionCards().count();

        const addBtn = modalRoot.getByRole('button', { name: /\+\s*Add Section/i }).first();
        await expect(addBtn).toBeVisible({ timeout: 60_000 });
        await addBtn.click();
        await expect(sectionCards()).toHaveCount(beforeCount + 1, { timeout: 60_000 });

        const cancelBtn = modalRoot.getByRole('button', { name: /^Cancel$/i }).first();
        await expect(cancelBtn).toBeVisible({ timeout: 60_000 });
        await cancelBtn.click();

        return {
          beforeCount,
          afterCount: await sectionCards().count(),
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'Manual Arrangement Entry > Section Type dropdown',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot, modalHeading } = await openManualArrangementModal(page);

        const typeSelect = modalRoot.getByTestId('manual-arrangement.section.1.type');
        await expect(typeSelect).toBeVisible({ timeout: 60_000 });

        const before = await typeSelect.inputValue();
        const next = before === 'chorus' ? 'verse' : 'chorus';
        await typeSelect.selectOption({ value: next });
        await expect(typeSelect).toHaveValue(next, { timeout: 60_000 });

        const applyBtn = modalRoot.getByRole('button', { name: /^Apply Arrangement$/i }).first();
        await expect(applyBtn).toBeVisible({ timeout: 60_000 });
        await applyBtn.click();
        await expect(modalHeading).toBeHidden({ timeout: 60_000 });

        const state = await snapshotDtkState(page);
        const sections = Array.isArray(state?.sections) ? state.sections : [];
        expect(sections.length).toBeGreaterThan(0);
        expect(String((sections[0] as any)?.label || '')).toBe(next);

        return { before, after: next, dtkState: state };
      },
    },
    {
      controlName: 'Manual Arrangement Entry > Start Measure',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot, modalHeading } = await openManualArrangementModal(page);

        const tempoInput = modalNumberInputByLabel(modalRoot, /Global Tempo \(BPM\)/i);
        await expect(tempoInput).toBeVisible({ timeout: 60_000 });
        const bpm = Number(await tempoInput.inputValue().catch(() => '120')) || 120;

        const beatsInput = modalNumberInputByLabel(modalRoot, /^Time Signature$/i);
        const unitSelect = modalSelectByLabel(modalRoot, /^Time Signature$/i);
        const beats = Number(await beatsInput.inputValue().catch(() => '4')) || 4;
        const _unit = Number(await unitSelect.inputValue().catch(() => '4')) || 4;

        const startMeasureInput = modalRoot.getByTestId('manual-arrangement.section.1.startMeasure');
        await expect(startMeasureInput).toBeVisible({ timeout: 60_000 });

        const before = Number(await startMeasureInput.inputValue());
        const next = before === 3 ? 2 : 3;
        await startMeasureInput.fill(String(next));
        await startMeasureInput.press('Tab');
        await expect(startMeasureInput).toHaveValue(String(next), { timeout: 60_000 });

        const applyBtn = modalRoot.getByRole('button', { name: /^Apply Arrangement$/i }).first();
        await expect(applyBtn).toBeVisible({ timeout: 60_000 });
        await applyBtn.click();
        await expect(modalHeading).toBeHidden({ timeout: 60_000 });

        const secondsPerBeat = 60.0 / bpm;
        const secondsPerMeasure = secondsPerBeat * beats;
        const expectedStart = (next - 1) * secondsPerMeasure;

        const state = await snapshotDtkState(page);
        const sections = Array.isArray(state?.sections) ? state.sections : [];
        expect(sections.length).toBeGreaterThan(0);
        const actualStart = Number((sections[0] as any)?.start);
        expect(Number.isFinite(actualStart)).toBeTruthy();
        expect(approxEq(actualStart, expectedStart, 1e-3)).toBeTruthy();

        return { before, after: next, expectedStart, actualStart, dtkState: state };
      },
    },
    {
      controlName: 'Manual Arrangement Entry > # Measures',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot, modalHeading } = await openManualArrangementModal(page);

        const tempoInput = modalNumberInputByLabel(modalRoot, /Global Tempo \(BPM\)/i);
        await expect(tempoInput).toBeVisible({ timeout: 60_000 });
        const bpm = Number(await tempoInput.inputValue().catch(() => '120')) || 120;

        const beatsInput = modalNumberInputByLabel(modalRoot, /^Time Signature$/i);
        const unitSelect = modalSelectByLabel(modalRoot, /^Time Signature$/i);
        const beats = Number(await beatsInput.inputValue().catch(() => '4')) || 4;
        const _unit = Number(await unitSelect.inputValue().catch(() => '4')) || 4;

        const startMeasureInput = modalRoot.getByTestId('manual-arrangement.section.1.startMeasure');
        const numMeasuresInput = modalRoot.getByTestId('manual-arrangement.section.1.numMeasures');
        await expect(startMeasureInput).toBeVisible({ timeout: 60_000 });
        await expect(numMeasuresInput).toBeVisible({ timeout: 60_000 });

        const startMeasure = Number(await startMeasureInput.inputValue().catch(() => '1')) || 1;
        const before = Number(await numMeasuresInput.inputValue());
        const next = before === 8 ? 4 : 8;
        await numMeasuresInput.fill(String(next));
        await numMeasuresInput.press('Tab');
        await expect(numMeasuresInput).toHaveValue(String(next), { timeout: 60_000 });

        const applyBtn = modalRoot.getByRole('button', { name: /^Apply Arrangement$/i }).first();
        await expect(applyBtn).toBeVisible({ timeout: 60_000 });
        await applyBtn.click();
        await expect(modalHeading).toBeHidden({ timeout: 60_000 });

        const secondsPerBeat = 60.0 / bpm;
        const secondsPerMeasure = secondsPerBeat * beats;
        const expectedStart = (startMeasure - 1) * secondsPerMeasure;
        const expectedEnd = expectedStart + next * secondsPerMeasure;

        const state = await snapshotDtkState(page);
        const sections = Array.isArray(state?.sections) ? state.sections : [];
        expect(sections.length).toBeGreaterThan(0);
        const actualEnd = Number((sections[0] as any)?.end);
        expect(Number.isFinite(actualEnd)).toBeTruthy();
        expect(approxEq(actualEnd, expectedEnd, 1e-3)).toBeTruthy();

        return { before, after: next, expectedEnd, actualEnd, dtkState: state };
      },
    },
    {
      controlName: 'Manual Arrangement Entry > Different tempo for this section',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot, modalHeading } = await openManualArrangementModal(page);

        const enabledToggle = modalRoot.getByTestId('manual-arrangement.section.1.tempoOverrideEnabled');
        await expect(enabledToggle).toBeVisible({ timeout: 60_000 });

        await enabledToggle.check();

        const tempoOverride = modalRoot.getByTestId('manual-arrangement.section.1.tempo');
        await expect(tempoOverride).toBeVisible({ timeout: 60_000 });

        const before = Number(await tempoOverride.inputValue().catch(() => '0')) || null;
        const next = 150;
        await tempoOverride.fill(String(next));
        await tempoOverride.press('Tab');
        await expect(tempoOverride).toHaveValue(String(next), { timeout: 60_000 });

        const applyBtn = modalRoot.getByRole('button', { name: /^Apply Arrangement$/i }).first();
        await expect(applyBtn).toBeVisible({ timeout: 60_000 });
        await applyBtn.click();
        await expect(modalHeading).toBeHidden({ timeout: 60_000 });

        const state = await snapshotDtkState(page);
        const sections = Array.isArray(state?.sections) ? state.sections : [];
        expect(sections.length).toBeGreaterThan(0);
        expect(Number((sections[0] as any)?.tempo)).toBe(next);

        return { before, after: next, dtkState: state };
      },
    },
    {
      controlName: 'Manual Arrangement > Apply Arrangement updates sections + BPM',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);
        const { modalRoot, modalHeading } = await openManualArrangementModal(page);

        const tempoInput = modalNumberInputByLabel(modalRoot, /Global Tempo \(BPM\)/i);
        await expect(tempoInput).toBeVisible({ timeout: 60_000 });
        const nextTempo = 141;
        await tempoInput.fill(String(nextTempo));
        await tempoInput.press('Tab');
        await expect(tempoInput).toHaveValue(String(nextTempo), { timeout: 60_000 });

        const sectionCards = () => modalRoot.locator('div.p-3.bg-slate-900.rounded.border');
        const addBtn = modalRoot.getByRole('button', { name: /\+\s*Add Section/i }).first();
        await expect(addBtn).toBeVisible({ timeout: 60_000 });
        const beforeModalCount = await sectionCards().count();
        await addBtn.click();
        await expect(sectionCards()).toHaveCount(beforeModalCount + 1, { timeout: 60_000 });

        const applyBtn = modalRoot.getByRole('button', { name: /^Apply Arrangement$/i }).first();
        await expect(applyBtn).toBeVisible({ timeout: 60_000 });
        await applyBtn.click();
        await expect(modalHeading).toBeHidden({ timeout: 60_000 });

        const heading = page.getByRole('heading', { name: /Musical Arrangement/i }).first();
        await expect(heading).toBeVisible({ timeout: 60_000 });
        const panel = heading.locator('xpath=ancestor::div[contains(@class,"bg-slate-800")][1]');
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const header = panel.locator('div.cursor-pointer').first();
        const addSectionBtn = panel.getByRole('button', { name: /Add Section/i }).first();

        const initiallyVisible = await addSectionBtn.isVisible().catch(() => false);
        if (initiallyVisible) {
          await header.click();
          await expect(addSectionBtn).toBeHidden({ timeout: 60_000 });
        }

        await header.click();
        await expect(addSectionBtn).toBeVisible({ timeout: 60_000 });

        await header.click();
        await expect(addSectionBtn).toBeHidden({ timeout: 60_000 });

        return {
          initiallyExpanded: initiallyVisible,
        };
      },
    },
    {
      controlName: 'Musical Arrangement > Select Section',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);

        const heading = page.getByRole('heading', { name: /Musical Arrangement/i }).first();
        await expect(heading).toBeVisible({ timeout: 60_000 });
        const panel = heading.locator('xpath=ancestor::div[contains(@class,"bg-slate-800")][1]');
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const header = panel.locator('div.cursor-pointer').first();
        const addBtn = panel.getByRole('button', { name: /Add Section/i }).first();
        if (!(await addBtn.isVisible().catch(() => false))) {
          await header.click();
          await expect(addBtn).toBeVisible({ timeout: 60_000 });
        }

        const sectionRows = () => panel.locator('div.border').filter({ hasText: /\d+\./ });

        // Ensure we have at least 2 sections to select between (DOM-based).
        for (let i = 0; i < 4; i++) {
          const n = await sectionRows().count();
          if (n >= 2) break;
          await addBtn.click();
          await expect(sectionRows()).toHaveCount(n + 1, { timeout: 60_000 });
        }

        const row0 = sectionRows().nth(0);
        const row1 = sectionRows().nth(1);
        await expect(row0).toBeVisible({ timeout: 60_000 });
        await expect(row1).toBeVisible({ timeout: 60_000 });

        await row0.click();
        await expect(row0).toHaveClass(/border-blue-500/, { timeout: 60_000 });

        await row1.click();
        await expect(row1).toHaveClass(/border-blue-500/, { timeout: 60_000 });

        return {
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'Musical Arrangement > Rename Section',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);

        const heading = page.getByRole('heading', { name: /Musical Arrangement/i }).first();
        await expect(heading).toBeVisible({ timeout: 60_000 });
        const panel = heading.locator('xpath=ancestor::div[contains(@class,"bg-slate-800")][1]');
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const header = panel.locator('div.cursor-pointer').first();
        const addBtn = panel.getByRole('button', { name: /Add Section/i }).first();
        if (!(await addBtn.isVisible().catch(() => false))) {
          await header.click();
          await expect(addBtn).toBeVisible({ timeout: 60_000 });
        }

        const sectionRows = () => panel.locator('div.border').filter({ hasText: /\d+\./ });
        if ((await sectionRows().count()) < 1) {
          await addBtn.click();
          await expect(sectionRows()).toHaveCount(1, { timeout: 60_000 });
        }

        const row0 = sectionRows().first();
        await expect(row0).toBeVisible({ timeout: 60_000 });

        // The rename button is rendered as an emoji label; use text-based locator.
        const renameBtn = row0.locator('button', { hasText: '✏️' }).first();
        await expect(renameBtn).toBeVisible({ timeout: 60_000 });
        await renameBtn.click();

        // When editing, the row no longer contains the "1." text used by sectionRows() filter.
        // Locate the edit input directly within the panel.
        const input = panel.locator('input[type="text"]').first();
        await expect(input).toBeVisible({ timeout: 60_000 });

        const newLabel = `verse_${Date.now()}`;
        await input.fill(newLabel);
        await input.press('Enter');

        // Verify row now contains the new label (label is uppercased in UI).
        await expect(panel).toContainText(new RegExp(newLabel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'), {
          timeout: 60_000,
        });

        return {
          renamedTo: newLabel,
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'Musical Arrangement > Delete Section',
      run: async ({ page }) => {
        await gotoHomeAndWaitForDtkState(page);

        const heading = page.getByRole('heading', { name: /Musical Arrangement/i }).first();
        await expect(heading).toBeVisible({ timeout: 60_000 });
        const panel = heading.locator('xpath=ancestor::div[contains(@class,"bg-slate-800")][1]');
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const header = panel.locator('div.cursor-pointer').first();
        const addBtn = panel.getByRole('button', { name: /Add Section/i }).first();
        if (!(await addBtn.isVisible().catch(() => false))) {
          await header.click();
          await expect(addBtn).toBeVisible({ timeout: 60_000 });
        }

        const sectionRows = () => panel.locator('div.border').filter({ hasText: /\d+\./ });

        // Ensure we have at least 2 sections (cannot delete last section).
        for (let i = 0; i < 4; i++) {
          const n = await sectionRows().count();
          if (n >= 2) break;
          await addBtn.click();
          await expect(sectionRows()).toHaveCount(n + 1, { timeout: 60_000 });
        }

        const beforeCount = await sectionRows().count();
        expect(beforeCount).toBeGreaterThanOrEqual(2);

        const row0 = sectionRows().first();
        await expect(row0).toBeVisible({ timeout: 60_000 });

        page.once('dialog', async (d: any) => {
          await d.accept();
        });

        const deleteBtn = row0.locator('button', { hasText: '🗑️' }).first();
        await expect(deleteBtn).toBeVisible({ timeout: 60_000 });
        await deleteBtn.click();

        await expect(sectionRows()).toHaveCount(beforeCount - 1, { timeout: 60_000 });

        const afterCount = await sectionRows().count();

        return {
          beforeCount,
          afterCount,
          dtkState: await snapshotDtkState(page),
        };
      },
    },
    {
      controlName: 'V3 UI: Export .mid controls visible',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        await triggerV3GenerateAndCapture(page);

        const exportBtn = page.getByRole('button', { name: /Export\s*\.mid/i }).first();
        await expect(exportBtn).toBeVisible({ timeout: 60_000 });

        // Plugin selector should be present in the export strip.
        const pluginSelect = page.locator('select').filter({ has: page.locator('option', { hasText: /Jamstix/i }) }).first();
        await expect(pluginSelect).toBeVisible({ timeout: 60_000 });

        return {
          exportButtonDisabled: await exportBtn.isDisabled().catch(() => null),
        };
      },
    },
    {
      controlName: 'V3 UI: Style affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const panel = v3GlobalDefaultsPanel(page);
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const styleInput = panel.getByLabel('Style').first();
        await expect(styleInput).toBeVisible({ timeout: 60_000 });

        const before = await triggerV3GenerateAndCapture(page);

        const nextStyle = `metal_${Date.now()}`;
        await styleInput.fill(nextStyle);

        const after = await triggerV3GenerateAndCapture(page);

        expect(String(after?.style || '')).toContain(nextStyle);
        expect(String(after?.style || '')).not.toBe(String(before?.style || ''));

        return { beforeStyle: before?.style, afterStyle: after?.style };
      },
    },
    {
      controlName: 'V3 UI: Humanize toggle affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const panel = v3GlobalDefaultsPanel(page);
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const humanizeField = panel.locator('label').filter({ hasText: /^Humanize\b/i }).first();
        await expect(humanizeField).toBeVisible({ timeout: 60_000 });
        const humanizeToggle = humanizeField.locator('input[type="checkbox"]').first();
        await expect(humanizeToggle).toBeVisible({ timeout: 60_000 });

        await humanizeToggle.setChecked(false);
        const reqOff = await triggerV3GenerateAndCapture(page);

        await humanizeToggle.setChecked(true);
        const reqOn = await triggerV3GenerateAndCapture(page);

        expect(Boolean(reqOff?.humanize)).toBe(false);
        expect(Boolean(reqOn?.humanize)).toBe(true);

        return { off: reqOff?.humanize, on: reqOn?.humanize };
      },
    },
    {
      controlName: 'V3 UI: Intensity affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const panel = v3GlobalDefaultsPanel(page);
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const { before, after } = await v3NudgeKnobUntilPayloadChangesByTestId({
          page,
          testId: 'v3.global.intensity.knob',
          payloadKey: 'intensity',
        });

        expect(typeof after?.intensity === 'number' ? after.intensity : NaN).not.toBeNaN();
        expect(after?.intensity).not.toBe(before?.intensity);

        return { beforeIntensity: before?.intensity, afterIntensity: after?.intensity };
      },
    },
    {
      controlName: 'V3 UI: Variation affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const panel = v3GlobalDefaultsPanel(page);
        await expect(panel).toBeVisible({ timeout: 60_000 });

        const { before, after } = await v3NudgeKnobUntilPayloadChangesByTestId({
          page,
          testId: 'v3.global.variation.knob',
          payloadKey: 'variation',
        });

        expect(typeof after?.variation === 'number' ? after.variation : NaN).not.toBeNaN();
        expect(after?.variation).not.toBe(before?.variation);

        return { beforeVariation: before?.variation, afterVariation: after?.variation };
      },
    },
    {
      controlName: 'V3 UI: Build Scope affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const scopeBox = page.getByText(/^Scope$/i).locator('xpath=ancestor::div[contains(@class,"border")][1]').first();
        await expect(scopeBox).toBeVisible({ timeout: 60_000 });

        const selectedSectionRadio = scopeBox.getByRole('radio', { name: /Selected section/i }).first();
        const fullSongRadio = scopeBox.getByRole('radio', { name: /Full song/i }).first();
        await expect(selectedSectionRadio).toBeVisible({ timeout: 60_000 });
        await expect(fullSongRadio).toBeVisible({ timeout: 60_000 });

        await fullSongRadio.check();
        const reqFull = await triggerV3GenerateAndCapture(page);

        await selectedSectionRadio.check();
        const reqSel = await triggerV3GenerateAndCapture(page);

        expect(reqFull?.buildScope).toBe('full_song');
        expect(reqSel?.buildScope).toBe('selected_section');

        return { fullSong: reqFull?.buildScope, selectedSection: reqSel?.buildScope };
      },
    },
    {
      controlName: 'V3 UI: Generation Mode affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const select = page.getByTestId('v3.global.generationMode');
        await expect(select).toBeVisible({ timeout: 60_000 });

        const before = await triggerV3GenerateAndCapture(page);

        const opts = await select.locator('option').all();
        const values: string[] = [];
        for (const o of opts) {
          const v = await o.getAttribute('value');
          if (v) values.push(v);
        }

        const beforeMode = String(before?.generationMode || '');
        const next = values.find((v) => v !== beforeMode) || values[0];
        if (!next) throw new Error('No generation mode options found');

        await select.selectOption(next);

        const after = await triggerV3GenerateAndCapture(page);
        expect(String(after?.generationMode || '')).toBe(String(next));
        expect(String(after?.generationMode || '')).not.toBe(beforeMode);

        return { before: before?.generationMode, after: after?.generationMode, next };
      },
    },
    {
      controlName: 'V3 UI: Humanize Amount affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const { before, after } = await v3NudgeKnobUntilPayloadChangesByTestId({
          page,
          testId: 'v3.global.humanizeAmount.knob',
          payloadKey: 'humanizeAmount',
        });

        expect(typeof after?.humanizeAmount === 'number' ? after.humanizeAmount : NaN).not.toBeNaN();
        expect(after?.humanizeAmount).not.toBe(before?.humanizeAmount);

        return { before: before?.humanizeAmount, after: after?.humanizeAmount };
      },
    },
    {
      controlName: 'V3 UI: Swing Amount affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const { before, after } = await v3NudgeKnobUntilPayloadChangesByTestId({
          page,
          testId: 'v3.global.swingAmount.knob',
          payloadKey: 'swingAmount',
        });

        expect(typeof after?.swingAmount === 'number' ? after.swingAmount : NaN).not.toBeNaN();
        expect(after?.swingAmount).not.toBe(before?.swingAmount);

        return { before: before?.swingAmount, after: after?.swingAmount };
      },
    },
    {
      controlName: 'V3 UI: Ghost Note Amount affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);

        const { before, after } = await v3NudgeKnobUntilPayloadChangesByTestId({
          page,
          testId: 'v3.global.ghostNoteAmount.knob',
          payloadKey: 'ghostNoteAmount',
        });

        expect(typeof after?.ghostNoteAmount === 'number' ? after.ghostNoteAmount : NaN).not.toBeNaN();
        expect(after?.ghostNoteAmount).not.toBe(before?.ghostNoteAmount);

        return { before: before?.ghostNoteAmount, after: after?.ghostNoteAmount };
      },
    },
    {
      controlName: 'V3 UI: Fill Type (section override) affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        await v3SelectFirstSection(page);

        const fillsOverride = page.getByTestId('v3.section.inherit.fills.override');
        await expect(fillsOverride).toBeVisible({ timeout: 60_000 });
        await fillsOverride.check();

        const fillType = page.getByTestId('v3.section.fills.fillType');
        await expect(fillType).toBeVisible({ timeout: 60_000 });

        const before = await triggerV3GenerateAndCapture(page);
        const beforeVal = String(before?.fillType || '');

        const opts = await fillType.locator('option').all();
        const values: string[] = [];
        for (const o of opts) {
          const v = await o.getAttribute('value');
          if (v) values.push(v);
        }
        const next = values.find((v) => v !== beforeVal) || values[0];
        if (!next) throw new Error('No fill type options found');

        await fillType.selectOption(next);
        const after = await triggerV3GenerateAndCapture(page);

        expect(String(after?.fillType || '')).toBe(String(next));
        expect(String(after?.fillType || '')).not.toBe(beforeVal);

        return { before: before?.fillType, after: after?.fillType, next };
      },
    },
    {
      controlName: 'V3 UI: Fill Density (section override) affects generate payload',
      run: async ({ page }) => {
        await ensureV3ScratchReady(page);
        await v3EnsureBuildScopeSelectedSection(page);
        await v3SelectFirstSection(page);

        const fillsOverride = page.getByTestId('v3.section.inherit.fills.override');
        await expect(fillsOverride).toBeVisible({ timeout: 60_000 });
        await fillsOverride.check();

        const { before, after } = await v3NudgeKnobUntilPayloadChangesByTestId({
          page,
          testId: 'v3.section.fills.density.knob',
          payloadKey: 'fillDensity',
        });

        expect(typeof after?.fillDensity === 'number' ? after.fillDensity : NaN).not.toBeNaN();
        expect(after?.fillDensity).not.toBe(before?.fillDensity);

        return { before: before?.fillDensity, after: after?.fillDensity };
      },
    },
  ];

  for (const def of controls) {
    test(def.controlName, async ({ page }, testInfo) => {
      await runControlValidation(def, { page, testInfo });
    });
  }
});
