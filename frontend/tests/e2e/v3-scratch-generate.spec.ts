import { test, expect } from "@playwright/test";

function makeStubDrumGenResponse(args?: { bars?: number; ppq?: number }) {
  const ppq = args?.ppq ?? 960;
  const bars = args?.bars ?? 8;
  const ticksPerBeat = ppq;
  const beatsPerBar = 4;
  const ticksPerBar = ticksPerBeat * beatsPerBar;

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
      aspect: "groove",
      limbId: instrumentId === "kick" ? "RF" : instrumentId.startsWith("snare") ? "LH" : "RH",
      priority: 0.6,
      microTimingMs: 0,
      hatOpenLevel: 0,
      hitStyle: "single",
      locked: false,
      isGhost: false,
      isAccent: false,
      isFlam: false,
      isDrag: false,
      phraseMarker: null,
      rudimentId: null,
    });
  };

  for (let bar = 0; bar < bars; bar += 1) {
    // hats on 8ths
    for (let b = 0; b < beatsPerBar * 2; b += 1) {
      push(bar, Math.floor((b * ticksPerBeat) / 2), "hihat_closed", 42, 74);
    }
    // kick on 1 and 3
    push(bar, 0, "kick", 36, 106);
    push(bar, 2 * ticksPerBeat, "kick", 36, 106);
    // snare on 2 and 4
    push(bar, 1 * ticksPerBeat, "snare_center", 38, 100);
    push(bar, 3 * ticksPerBeat, "snare_center", 38, 100);
  }

  return {
    ok: true,
    drum_track: {
      track_id: "test-track",
      style_id: "rock",
      resolution_ppq: ppq,
      notes,
      performance_spec: {
        styleId: "rock",
        globalFeel: "straight",
        quantizationBase: "16th",
        phrases: [],
      },
    },
    midi_base64: "AA==",
    metadata: {
      builder_version: "v2.0",
      generation_time_ms: 1,
      drummer_used: "test",
      style: "rock",
      mode: "template",
      humanized: false,
      measure_count: bars,
    },
  };
}

test("v3 scratch: build new track -> generate produces diagnostic metrics", async ({ page }) => {
  test.setTimeout(240_000);

  // Enable E2E diagnostics hook
  await page.goto("/v3?e2e=1");

  // Switch to scratch mode (New Track Creation)
  await page.getByTestId("v3.workflow.scratch").check();

  // Ensure BPM/TimeSig confirmed if the UI requires it (best-effort)
  const confirmBtn = page.getByRole("button", { name: /Confirm BPM/i });
  if (await confirmBtn.isVisible().catch(() => false)) {
    await confirmBtn.click();
  }

  // Build the scratch arrangement
  await page.getByTestId("v3.scratch.build").click();

  // Select drummer profile (required) - real backend
  const drummerSelect = page.getByRole("combobox").filter({ hasText: /Select drummer profile/i }).first();
  await expect(drummerSelect).toBeVisible({ timeout: 60_000 });
  await drummerSelect.selectOption({ index: 1 });

  // Generate
  const generateBtn = page.getByTestId("v3.generate");
  await expect(generateBtn).toBeVisible({ timeout: 30_000 });
  await generateBtn.click();

  // Wait for diagnostics hook to be available + populated
  await page.waitForFunction(() => typeof (window as any).__dtk_getDiagnosticsSnapshot === "function");
  await page.waitForFunction(() => {
    const fn = (window as any).__dtk_getDiagnosticsSnapshot;
    if (typeof fn !== "function") return false;
    const snap = fn();
    return !!snap && snap.metrics && typeof snap.metrics.notesCount === "number" && snap.metrics.notesCount > 0;
  });

  const snap = await page.evaluate(() => (window as any).__dtk_getDiagnosticsSnapshot());

  expect(snap.workflowMode).toBe("scratch");
  expect(snap.metrics.notesCount).toBeGreaterThan(0);

  const byInst: Record<string, number> = snap.metrics.byInstrument || {};
  const keys = Object.keys(byInst);

  const kickCount = Number(byInst.kick || byInst.kick_sub || byInst["36"] || 0);
  expect(kickCount).toBeGreaterThan(0);

  const nonZeroKeys = keys.filter((k) => (Number(byInst[k]) || 0) > 0);
  expect(nonZeroKeys.length).toBeGreaterThan(1);
});
