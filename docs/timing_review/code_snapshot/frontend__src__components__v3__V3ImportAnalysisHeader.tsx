import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useV3Store } from "../../state/v3/store";
import { WaveformView } from "../WaveformView";
import { alignSections, analyzeTempo, fetchWaveform, generateDrums, sectionizeSmart, uploadFile } from "../../api/api";
import type { ArrangementSection, TempoPt } from "../../midi/types";
import type { DrumGenerationConfig } from "../../types/drumTrack";
import { importSMF } from "../../midi/io";
import { useMidi } from "../../midi/midiStore";
import type { V3ScratchRow, V3WorkflowMode } from "../../state/v3/types";

type BusyStage = "idle" | "upload" | "waveform" | "tempo" | "sectionize" | "align" | "generate";

function toTempoMap(resp: any): TempoPt[] {
  if (Array.isArray(resp?.tempoCurve) && resp.tempoCurve.length) {
    return resp.tempoCurve
      .map((p: any) => ({ tSec: Number(p?.time) || 0, bpm: Number(p?.bpm) || 120 }))
      .filter((p: TempoPt) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm));
  }
  if (Array.isArray(resp?.beats) && resp.beats.length >= 4) {
    const beats = resp.beats
      .map((t: any) => Number(t))
      .filter((t: number) => Number.isFinite(t))
      .sort((a: number, b: number) => a - b);

    // Build a curve by estimating local BPM from beat-to-beat intervals using a sliding window.
    const windowBeats = 8;
    const pts: TempoPt[] = [];
    for (let i = 0; i + windowBeats < beats.length; i += Math.max(1, Math.floor(windowBeats / 2))) {
      const ts = beats.slice(i, i + windowBeats + 1);
      const dts: number[] = [];
      for (let j = 0; j + 1 < ts.length; j++) {
        const dt = ts[j + 1] - ts[j];
        if (Number.isFinite(dt) && dt > 1e-3 && dt < 10) dts.push(dt);
      }
      if (!dts.length) continue;
      dts.sort((a, b) => a - b);
      const medianDt = dts[Math.floor(dts.length / 2)];
      const bpm = 60 / Math.max(1e-6, medianDt);
      pts.push({ tSec: ts[Math.floor(ts.length / 2)] || 0, bpm });
    }

    if (pts.length) return pts;
  }
  if (typeof resp?.bpm === "number") {
    return [{ tSec: 0, bpm: resp.bpm }];
  }
  if (typeof resp?.tempo === "number") {
    return [{ tSec: 0, bpm: resp.tempo }];
  }
  return [{ tSec: 0, bpm: 120 }];
}

function toSections(raw: any, fallbackCount = 0): ArrangementSection[] {
  const out: ArrangementSection[] = [];
  const list = raw?.sections || raw?.aligned || raw || [];
  if (Array.isArray(list)) {
    list.forEach((s: any, idx: number) => {
      const startSec = Number(s?.startSec ?? s?.start ?? 0);
      const endSec = Number(s?.endSec ?? s?.end ?? 0);
      if (!Number.isFinite(startSec) || !Number.isFinite(endSec)) return;
      if (endSec <= startSec) return;
      const label = String(s?.label || `Section ${idx + 1}`);
      out.push({ label, startSec, endSec, conf: s?.conf });
    });
  }
  if (!out.length && fallbackCount > 0) {
    for (let i = 0; i < fallbackCount; i++) {
      out.push({ label: `Section ${i + 1}`, startSec: i * 8, endSec: (i + 1) * 8 });
    }
  }
  return out;
}

function normalizePeaks(peaks: any): number[] {
  if (!Array.isArray(peaks)) return [];
  let max = 0;
  const nums = peaks
    .map((v: any) => {
      const n = Math.abs(Number(v) || 0);
      if (Number.isFinite(n) && n > max) max = n;
      return n;
    })
    .map((n: number) => (Number.isFinite(n) ? n : 0));

  if (!nums.length) return [];
  const scale = max > 1 ? 1 / max : 1;
  return nums.map((n) => Math.max(0, Math.min(1, n * scale)));
}

function clamp01(v: number): number {
  return Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0));
}

function clampInt(v: number, lo: number, hi: number): number {
  const n = Math.floor(Number.isFinite(v) ? v : 0);
  return Math.max(lo, Math.min(hi, n));
}

function v3SectionId(idx: number, s: { startSec: number; endSec: number }): string {
  return `v3-${idx}-${Number(s.startSec || 0).toFixed(3)}-${Number(s.endSec || 0).toFixed(3)}`;
}

function beatsAtTimeFromBeatTimes(beatTimes: number[], tSec: number): number {
  if (!Array.isArray(beatTimes) || beatTimes.length < 2) return 0;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);
  if (t <= beatTimes[0]) return 0;

  let lo = 0;
  let hi = beatTimes.length - 1;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (beatTimes[mid] < t) lo = mid + 1;
    else hi = mid;
  }
  const idx = lo;
  if (idx <= 0) return 0;
  if (idx >= beatTimes.length) return beatTimes.length - 1;
  const prev = idx - 1;
  const t0 = beatTimes[prev];
  const t1 = beatTimes[idx];
  if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) return prev;
  const frac = Math.max(0, Math.min(1, (t - t0) / (t1 - t0)));
  return prev + frac;
}

function beatsAtTimeFromTempoMap(tempoMap: Array<{ tSec: number; bpm: number }>, fallbackBpm: number, tSec: number): number {
  const pts = Array.isArray(tempoMap)
    ? tempoMap
        .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
        .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
        .sort((a, b) => a.tSec - b.tSec)
    : [];

  const bpm0 = Number.isFinite(fallbackBpm) && fallbackBpm > 0 ? fallbackBpm : 120;
  const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);

  if (!pts.length) return (t * bpm0) / 60;
  if (pts.length === 1) return (t * pts[0].bpm) / 60;

  let beats = 0;
  let prevT = pts[0].tSec;
  let prevBpm = pts[0].bpm;
  if (t <= prevT) return 0;

  for (let i = 1; i < pts.length; i++) {
    const cur = pts[i];
    if (t <= cur.tSec) {
      beats += ((t - prevT) * prevBpm) / 60;
      return beats;
    }
    beats += ((cur.tSec - prevT) * prevBpm) / 60;
    prevT = cur.tSec;
    prevBpm = cur.bpm;
  }

  beats += ((t - prevT) * prevBpm) / 60;
  return beats;
}

function barRangeForSection(args: {
  section: ArrangementSection;
  idx: number;
  beatsPerBar: number;
  beatTimes?: number[];
  tempoMap?: Array<{ tSec: number; bpm: number }>;
  fallbackBpm: number;
}): { id: string; label: string; startBar: number; endBar: number } {
  const { section, idx, beatsPerBar, beatTimes, tempoMap, fallbackBpm } = args;
  const bpb = Math.max(1, Number(beatsPerBar) || 4);

  const startSec = Number(section.startSec) || 0;
  const endSec = Number(section.endSec) || 0;
  let startBeats = 0;
  let endBeats = 0;

  if (Array.isArray(beatTimes) && beatTimes.length >= 2) {
    startBeats = beatsAtTimeFromBeatTimes(beatTimes, startSec);
    endBeats = beatsAtTimeFromBeatTimes(beatTimes, endSec);
  } else {
    startBeats = beatsAtTimeFromTempoMap(tempoMap || [], fallbackBpm, startSec);
    endBeats = beatsAtTimeFromTempoMap(tempoMap || [], fallbackBpm, endSec);
  }

  const startBar = Math.max(0, Math.floor(startBeats / bpb));
  const endBar = Math.max(startBar, Math.floor((Math.max(startBeats, endBeats - 1e-6)) / bpb));
  return {
    id: v3SectionId(idx, section),
    label: section.label || `Section ${idx + 1}`,
    startBar,
    endBar,
  };
}

function temposFromBeatTimes(beatTimes: number[], beatsPerBar: number): number[] {
  if (!Array.isArray(beatTimes) || beatTimes.length < 2) return [];
  if (!(beatsPerBar > 0)) return [];

  const beatCount = beatTimes.length - 1;
  const bars = Math.floor(beatCount / beatsPerBar);
  if (bars < 1) return [];

  const tempos: number[] = new Array(bars);
  for (let bar = 0; bar < bars; bar++) {
    const b0 = bar * beatsPerBar;
    const b1 = (bar + 1) * beatsPerBar;
    const t0 = beatTimes[b0];
    const t1 = beatTimes[b1];
    if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) {
      throw new Error(`Invalid beat grid: beatTimes[${b0}]..beatTimes[${b1}]`);
    }
    const secPerBeat = (t1 - t0) / beatsPerBar;
    if (!(secPerBeat > 1e-6)) {
      throw new Error(`Invalid beat grid: non-positive sec/beat at bar ${bar}`);
    }
    tempos[bar] = 60 / secPerBeat;
  }
  return tempos;
}

export function V3ImportAnalysisHeader() {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const waveformWrapRef = useRef<HTMLDivElement | null>(null);
  const scratchStripRef = useRef<HTMLDivElement | null>(null);
  const [waveformWidth, setWaveformWidth] = useState(920);
  const [useNormalized, setUseNormalized] = useState(false);

  const [scratchDrag, setScratchDrag] = useState<null | {
    boundaryIdx: number;
    left: number;
    width: number;
    totalBars: number;
    boundaryBar: number;
    startBars: number[];
  }>(null);

  const importState = useV3Store((s) => s.importState);
  const arrangement = useV3Store((s) => s.arrangement);
  const globalDefaults = useV3Store((s) => s.globalDefaults);
  const setInspectorView = useV3Store((s) => s.setInspectorView);
  const setDrummerPickerTarget = useV3Store((s) => s.setDrummerPickerTarget);
  const setDrummerPickerOpen = useV3Store((s) => s.setDrummerPickerOpen);
  const barEdits = useV3Store((s) => s.barEdits);
  const workflowMode = useV3Store((s) => s.workflowMode);
  const scratchArrangement = useV3Store((s) => s.scratchArrangement);
  const selectedSectionId = useV3Store((s) => s.selection.selectedSectionId);
  const sectionOverrides = useV3Store((s) => s.sectionOverrides);

  const setImportState = useV3Store((s) => s.setImportState);
  const resetImport = useV3Store((s) => s.resetImport);
  const setTempoMap = useV3Store((s) => s.setTempoMap);
  const setBeatTimes = useV3Store((s) => s.setBeatTimes);
  const setTimeSig = useV3Store((s) => s.setTimeSig);
  const setSections = useV3Store((s) => s.setSections);
  const setGeneratedDrumTrack = useV3Store((s) => s.setGeneratedDrumTrack);
  const setWorkflowMode = useV3Store((s) => s.setWorkflowMode);
  const setScratchArrangement = useV3Store((s) => s.setScratchArrangement);
  const setSelectedSectionId = useV3Store((s) => s.setSelectedSectionId);
  const setGlobalDefaults = useV3Store((s) => s.setGlobalDefaults);
  const setEditorTab = useV3Store((s) => s.setEditorTab);
  const generatedDrumTrack = useV3Store((s) => s.generatedDrumTrack);
  const autoGenerateNonce = useV3Store((s) => Number(s.ui.autoGenerateNonce || 0));
  const bumpAutoGenerateNonce = useV3Store((s) => s.bumpAutoGenerateNonce);
  const coach = useV3Store((s) => s.coach);

  const onReset = useCallback(() => {
    resetImport();
    try {
      useMidi.getState().clearAll();
    } catch {
      // ignore
    }
    setGeneratedDrumTrack(null);
    setGlobalDefaults({ publicDrummerId: "", drummer: "", presetStack: [] as any });
    setInspectorView("global");
  }, [resetImport, setGeneratedDrumTrack, setGlobalDefaults, setInspectorView]);

  const [drummerOptions, setDrummerOptions] = useState<Array<{ id: string; display_name: string }>>([]);
  const [drummerError, setDrummerError] = useState<string | null>(null);

  const [grooveModalOpen, setGrooveModalOpen] = useState(false);
  const [grooveQuery, setGrooveQuery] = useState("");
  const [grooveTag, setGrooveTag] = useState("");
  const [grooveLoading, setGrooveLoading] = useState(false);
  const [grooveResults, setGrooveResults] = useState<any[]>([]);
  const [grooveLastRequest, setGrooveLastRequest] = useState<string>("");
  const [grooveLastCount, setGrooveLastCount] = useState<number | null>(null);
  const [grooveLastError, setGrooveLastError] = useState<string>("");
  const [grooveSourceMode, setGrooveSourceMode] = useState<"egmd" | "dtk_standard">("egmd");
  const [egmdFeelPreset, setEgmdFeelPreset] = useState<
    "any"
    | "straight_backbeat"
    | "four_on_floor"
    | "half_time_sparse"
    | "syncopated"
    | "busy"
  >("straight_backbeat");
  const [egmdComplexityTier, setEgmdComplexityTier] = useState<"simple" | "intermediate" | "complex">("simple");
  const [requireTagMatch, setRequireTagMatch] = useState(true);
  const [egmdStyleOptions, setEgmdStyleOptions] = useState<string[]>([]);
  const [egmdStyleGroup, setEgmdStyleGroup] = useState<string>("");
  const [egmdStyleFallbackActive, setEgmdStyleFallbackActive] = useState(false);
  const [playingGrooveId, setPlayingGrooveId] = useState<string | null>(null);
  const grooveAudioRef = useRef<HTMLAudioElement | null>(null);

  const [scratchTempoConfirmed, setScratchTempoConfirmed] = useState(false);
  const [scratchNeedsGenerate, setScratchNeedsGenerate] = useState(false);
  const [scratchBpmText, setScratchBpmText] = useState<string>("");

  useEffect(() => {
    if (workflowMode !== "scratch") return;
    const bpm = Math.round(Number(arrangement.tempoMap?.[0]?.bpm || 120));
    setScratchBpmText(String(bpm));
  }, [arrangement.tempoMap, workflowMode]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const apiBase = useV3Store.getState().env.apiBase || "";
        const mode = String(grooveSourceMode || "egmd");
        const res = await fetch(`${apiBase}/api/grooves/style-groups?sources=${encodeURIComponent(mode)}&limit=200`);
        if (!res.ok) return;
        const json = await res.json();
        const items = Array.isArray((json as any)?.items) ? (json as any).items : [];
        const normalized = items
          .map((s: any) => String(s || "").trim().toLowerCase())
          .filter((s: string) => !!s);
        if (cancelled) return;
        setEgmdStyleOptions(normalized);
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [grooveSourceMode]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setDrummerError(null);
        const res = await fetch(`/api/drummers`);
        if (!res.ok) throw new Error(`Failed to fetch drummers (${res.status})`);
        const data = await res.json();
        const list = Array.isArray(data?.drummers) ? data.drummers : [];
        const mapped = list
          .map((d: any) => ({ id: String(d?.id || ""), display_name: String(d?.display_name || d?.id || "") }))
          .filter((d: any) => d.id);
        if (!cancelled) setDrummerOptions(mapped);
      } catch (e: any) {
        if (!cancelled) setDrummerError(e?.message || String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const searchGrooves = useCallback(
    async (queryIn?: string, tagIn?: string, styleGroupIn?: string) => {
      const apiBase = useV3Store.getState().env.apiBase || "";
      const q = String(queryIn ?? grooveQuery).trim();
      const tag = String(tagIn ?? grooveTag).trim();
      const sg = String(styleGroupIn ?? egmdStyleGroup).trim();
      const isEgmd = String(grooveSourceMode || "egmd").trim().toLowerCase() === "egmd";
      setGrooveLoading(true);
      setGrooveLastError("");
      setEgmdStyleFallbackActive(false);
      try {
        const params = new URLSearchParams();
        if (q) params.set("q", q);
        if (tag) params.set("tags", tag);
        params.set("sources", isEgmd ? "egmd" : "dtk_standard");
        if (sg) params.set("style_group", sg);
        if (isEgmd) {
          // 3-level complexity (musician-friendly) without brittle hard filtering.
          // Simple: show the least complex options.
          // Intermediate: show general options (still sorted simple->complex).
          // Complex: show the most complex options.
          if (egmdComplexityTier === "complex") {
            params.set("sort", "complexity_desc");
          } else {
            params.set("sort", "complexity_asc");
          }

          // Soft caps (avoid empty results). These are intentionally generous.
          if (egmdComplexityTier === "simple") {
            // Option B: simple orchestration (kick+snare with steady hats/ride allowed)
            params.set("kick_snare_share_min", "0.22");
            params.set("snare_share_max", "0.22");
            params.set("tom_share_max", "0.16");
            params.set("cymbal_share_max", "0.85");
            // Guardrail: some EGMD clips still qualify on orchestration shares but are musically busy.
            // Put an upper bound on overall complexity + density.
            params.set("complexity_max", "0.60");
            params.set("hits_per_bar_max", "20");
          } else if (egmdComplexityTier === "complex") {
            params.set("complexity_min", "0.55");
          }

          // Drum-terminology presets (more intuitive than a raw complexity value).
          if (egmdFeelPreset === "straight_backbeat") {
            // EGMD grooves often contain additional snare events (ghosts/ornaments), so the
            // backbeat ratio is typically much lower than you'd expect from a strict 2&4 filter.
            params.set("snare_backbeat_ratio_min", "0.12");
            params.set("offbeat_ratio_max", "0.75");
            params.set("active_instruments_max", "5");
          } else if (egmdFeelPreset === "four_on_floor") {
            params.set("snare_backbeat_ratio_min", "0.5");
            params.set("offbeat_ratio_max", "0.60");
            params.set("active_instruments_max", "4");
            params.set("hits_per_bar_max", "20");
          } else if (egmdFeelPreset === "half_time_sparse") {
            params.set("snare_backbeat_ratio_min", "0.35");
            params.set("offbeat_ratio_max", "0.55");
            params.set("active_instruments_max", "4");
            params.set("hits_per_bar_max", "18");
          } else if (egmdFeelPreset === "syncopated") {
            params.set("offbeat_ratio_min", "0.45");
          } else if (egmdFeelPreset === "busy") {
            params.set("complexity_min", "0.45");
          }
        }
        // Pull more than we display so frontend de-dupe can still yield 24 options.
        params.set("limit", "50");
        const path = `/api/grooves/search?${params.toString()}`;
        setGrooveLastRequest(path);
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 20000);
        const res = await fetch(`${apiBase}${path}`, { signal: controller.signal });
        window.clearTimeout(timeoutId);
        if (!res.ok) throw new Error(`Groove search failed (${res.status})`);
        const json = await res.json();
        let items = Array.isArray(json?.items) ? json.items : [];
        if (isEgmd && sg && items.length === 0) {
          // If the style-group is empty under current filters, try a relaxed pass that
          // still preserves the requested style_group (avoid cross-style leakage).
          try {
            const relaxedStyleParams = new URLSearchParams(params);
            relaxedStyleParams.set("style_group", sg);
            if (egmdComplexityTier === "simple") {
              relaxedStyleParams.set("complexity_max", "0.75");
              relaxedStyleParams.set("hits_per_bar_max", "24");
              relaxedStyleParams.set("snare_share_max", "0.26");
              relaxedStyleParams.set("cymbal_share_max", "0.90");
              relaxedStyleParams.set("tom_share_max", "0.22");
            }
            if (egmdFeelPreset === "straight_backbeat") {
              relaxedStyleParams.set("snare_backbeat_ratio_min", "0.10");
              relaxedStyleParams.set("offbeat_ratio_max", "0.85");
              relaxedStyleParams.set("active_instruments_max", "6");
            }
            relaxedStyleParams.set("limit", "50");
            const relaxedPath = `/api/grooves/search?${relaxedStyleParams.toString()}`;
            setGrooveLastRequest(relaxedPath);
            const controllerRelaxed = new AbortController();
            const timeoutRelaxed = window.setTimeout(() => controllerRelaxed.abort(), 20000);
            const rRelaxed = await fetch(`${apiBase}${relaxedPath}`, { signal: controllerRelaxed.signal });
            window.clearTimeout(timeoutRelaxed);
            if (rRelaxed.ok) {
              const jRelaxed = await rRelaxed.json();
              const relaxedItems = Array.isArray(jRelaxed?.items) ? jRelaxed.items : [];
              if (relaxedItems.length > 0) {
                items = relaxedItems;
              }
            }
          } catch {
            // ignore
          }
        }

        if (isEgmd && sg && items.length === 0) {
          // Final attempt: preserve style_group but remove feel/complexity caps entirely.
          // This avoids false negatives for styles (e.g. funk) where the default caps are too strict.
          try {
            const styleOnlyParams = new URLSearchParams();
            if (q) styleOnlyParams.set("q", q);
            if (tag) styleOnlyParams.set("tags", tag);
            styleOnlyParams.set("sources", "egmd");
            styleOnlyParams.set("style_group", sg);
            styleOnlyParams.set("limit", "50");
            const styleOnlyPath = `/api/grooves/search?${styleOnlyParams.toString()}`;
            setGrooveLastRequest(styleOnlyPath);
            const controllerStyleOnly = new AbortController();
            const timeoutStyleOnly = window.setTimeout(() => controllerStyleOnly.abort(), 20000);
            const rStyleOnly = await fetch(`${apiBase}${styleOnlyPath}`, { signal: controllerStyleOnly.signal });
            window.clearTimeout(timeoutStyleOnly);
            if (rStyleOnly.ok) {
              const jStyleOnly = await rStyleOnly.json();
              const styleOnlyItems = Array.isArray(jStyleOnly?.items) ? jStyleOnly.items : [];
              if (styleOnlyItems.length > 0) {
                items = styleOnlyItems;
              }
            }
          } catch {
            // ignore
          }
        }

        if (isEgmd && sg && items.length === 0) {
          const fallbackParams = new URLSearchParams();
          if (q) fallbackParams.set("q", q);
          if (tag) fallbackParams.set("tags", tag);
          fallbackParams.set("sources", "egmd");

          if (egmdComplexityTier === "complex") {
            fallbackParams.set("sort", "complexity_desc");
          } else {
            fallbackParams.set("sort", "complexity_asc");
          }

          if (egmdComplexityTier === "simple") {
            fallbackParams.set("kick_snare_share_min", "0.22");
            fallbackParams.set("snare_share_max", "0.22");
            fallbackParams.set("tom_share_max", "0.16");
            fallbackParams.set("cymbal_share_max", "0.85");
            fallbackParams.set("complexity_max", "0.60");
            fallbackParams.set("hits_per_bar_max", "20");
          } else if (egmdComplexityTier === "complex") {
            fallbackParams.set("complexity_min", "0.55");
          }

          if (egmdFeelPreset === "straight_backbeat") {
            fallbackParams.set("snare_backbeat_ratio_min", "0.12");
            fallbackParams.set("offbeat_ratio_max", "0.75");
            fallbackParams.set("active_instruments_max", "5");
          } else if (egmdFeelPreset === "four_on_floor") {
            fallbackParams.set("snare_backbeat_ratio_min", "0.5");
            fallbackParams.set("offbeat_ratio_max", "0.60");
            fallbackParams.set("active_instruments_max", "4");
            fallbackParams.set("hits_per_bar_max", "20");
          } else if (egmdFeelPreset === "half_time_sparse") {
            fallbackParams.set("snare_backbeat_ratio_min", "0.35");
            fallbackParams.set("offbeat_ratio_max", "0.55");
            fallbackParams.set("active_instruments_max", "4");
            fallbackParams.set("hits_per_bar_max", "18");
          } else if (egmdFeelPreset === "syncopated") {
            fallbackParams.set("offbeat_ratio_min", "0.45");
          } else if (egmdFeelPreset === "busy") {
            fallbackParams.set("complexity_min", "0.45");
          }
          fallbackParams.set("limit", "50");
          const fallbackPath = `/api/grooves/search?${fallbackParams.toString()}`;
          setGrooveLastRequest(fallbackPath);
          try {
            const controller2 = new AbortController();
            const timeoutId2 = window.setTimeout(() => controller2.abort(), 20000);
            const r2 = await fetch(`${apiBase}${fallbackPath}`, { signal: controller2.signal });
            window.clearTimeout(timeoutId2);
            if (r2.ok) {
              const j2 = await r2.json();
              items = Array.isArray(j2?.items) ? j2.items : [];
              setEgmdStyleFallbackActive(true);
            }
          } catch {
            // ignore
          }
        }

        // Stable de-dupe (the backend can return multiple entries for the same underlying phrase/file).
        // Prefer phrase_id / audio_path / midi_path; fall back to id/title.
        const seen = new Set<string>();
        const deduped: any[] = [];
        for (let i = 0; i < items.length; i++) {
          const it = items[i];
          const source = String(it?.source || "").trim().toLowerCase();
          const phraseId = String((it as any)?.phrase_id || (it as any)?.egmd_phrase_id || "").trim();
          const audioPath = String((it as any)?.audio_path || "").trim();
          const midiPath = String((it as any)?.midi_path || "").trim();
          const id = String(it?.id || "").trim();
          const title = String(it?.title || it?.name || "").trim();

          const key = phraseId
            ? `${source}|phrase:${phraseId}`
            : audioPath
              ? `${source}|audio:${audioPath}`
              : midiPath
                ? `${source}|midi:${midiPath}`
                : id
                  ? `${source}|id:${id}`
                  : `${source}|title:${title}|idx:${i}`;

          if (seen.has(key)) continue;
          seen.add(key);
          deduped.push(it);
        }

        items = deduped.slice(0, 24);
        setGrooveLastCount(items.length);
        setGrooveResults(items);
      } catch (e: any) {
        setGrooveResults([]);
        const msg =
          e?.name === "AbortError"
            ? "Groove search timed out. Try again, or loosen filters."
            : e?.message || String(e);
        setGrooveLastCount(0);
        setGrooveLastError(msg);
        setImportState({ error: msg });
      } finally {
        setGrooveLoading(false);
      }
    },
    [egmdComplexityTier, egmdFeelPreset, egmdStyleGroup, grooveQuery, grooveSourceMode, grooveTag, setImportState],
  );

  useEffect(() => {
    if (!grooveModalOpen) {
      try {
        grooveAudioRef.current?.pause?.();
      } catch {
        // ignore
      }
      grooveAudioRef.current = null;
      setPlayingGrooveId(null);
    }
  }, [grooveModalOpen]);

  const filteredGrooveResults = useMemo(() => {
    let list = grooveResults || [];
    const src = String(grooveSourceMode || "egmd").trim().toLowerCase();
    list = list.filter((item) => String(item?.source || "").trim().toLowerCase() === src);
    if (egmdStyleGroup && !egmdStyleFallbackActive) {
      list = list.filter(
        (item) =>
          String(item?.style_group || "").trim().toLowerCase() === String(egmdStyleGroup || "").trim().toLowerCase(),
      );
    }
    if (!requireTagMatch) return list;
    const t = String(grooveTag || "").trim().toLowerCase();
    if (!t) return list;
    return list.filter((item) =>
      Array.isArray(item?.tags) ? item.tags.map((x: any) => String(x || "").toLowerCase()).includes(t) : false,
    );
  }, [egmdStyleFallbackActive, egmdStyleGroup, grooveResults, grooveSourceMode, grooveTag, requireTagMatch]);

  const displayedGrooveResults = useMemo(() => {
    // If a style is explicitly selected, do NOT show unfiltered results (that causes cross-style leakage).
    if (egmdStyleGroup && !egmdStyleFallbackActive) return filteredGrooveResults;
    if (filteredGrooveResults.length > 0) return filteredGrooveResults;
    if ((grooveResults || []).length > 0) return grooveResults;
    return [];
  }, [egmdStyleFallbackActive, egmdStyleGroup, filteredGrooveResults, grooveResults]);

  const toggleGrooveAudio = useCallback(async (grooveId: string) => {
    const id = String(grooveId || "").trim();
    if (!id) return;

    // Stop if already playing.
    if (playingGrooveId === id) {
      try {
        grooveAudioRef.current?.pause?.();
      } catch {
        // ignore
      }
      grooveAudioRef.current = null;
      setPlayingGrooveId(null);
      return;
    }

    try {
      // Stop any current.
      try {
        grooveAudioRef.current?.pause?.();
      } catch {
        // ignore
      }
      grooveAudioRef.current = null;

      // If there's no audio preview, fall back to MIDI audition via the drum sampler.
      try {
        const card = displayedGrooveResults.find((x: any) => String(x?.id || "") === id);
        const hasAudio = Boolean(card?.has_audio);
        if (!hasAudio) {
          const apiBase = useV3Store.getState().env.apiBase || "";
          const r = await fetch(`${apiBase}/api/grooves/${encodeURIComponent(id)}/audition`);
          if (!r.ok) throw new Error("Groove audition not available for this item.");
          const j: any = await r.json();
          const items = Array.isArray(j?.items) ? j.items : [];
          const durationSec = Number(j?.durationSec ?? 0) || 0;
          if (!items.length || durationSec <= 0) throw new Error("Groove audition not available for this item.");

          const notes = items
            .map((it: any) => ({
              barIndex: 0,
              tickInBar: 0,
              instrumentId: String(it?.instrumentId || ""),
              velocity: Number(it?.velocity ?? 100) || 100,
              // WebDAWAppV3 audition path uses tSec directly.
              tSec: Number(it?.tSec ?? 0) || 0,
            }))
            .filter((n: any) => n.instrumentId && Number.isFinite(n.tSec));

          if (!notes.length) throw new Error("Groove audition not available for this item.");

          useV3Store.getState().requestAuditionBarPreview(
            "groove_modal",
            0,
            0,
            Math.max(0.25, durationSec),
            notes,
          );
          setPlayingGrooveId(id);
          window.setTimeout(() => {
            if (useV3Store.getState().auditionRequest?.mode === "bar") {
              useV3Store.getState().stopAudition();
            }
            setPlayingGrooveId(null);
          }, Math.max(250, Math.round(Math.max(0.25, durationSec) * 1000)));
          return;
        }
      } catch (e: any) {
        setImportState({ error: e?.message || String(e) });
        setPlayingGrooveId(null);
        grooveAudioRef.current = null;
        return;
      }

      const audio = new Audio(`/api/grooves/${encodeURIComponent(id)}/audio`);
      audio.onended = () => {
        setPlayingGrooveId(null);
        grooveAudioRef.current = null;
      };
      audio.onerror = () => {
        setImportState({ error: "Groove audio not available for this item." });
        setPlayingGrooveId(null);
        grooveAudioRef.current = null;
      };

      grooveAudioRef.current = audio;
      setPlayingGrooveId(id);
      await audio.play();
    } catch (e: any) {
      setImportState({ error: e?.message || String(e) });
      setPlayingGrooveId(null);
      grooveAudioRef.current = null;
    }
  }, [displayedGrooveResults, playingGrooveId, setImportState]);

  const sectionOptions = useMemo(() => {
    return (arrangement.sections || []).map((s, idx) => ({
      id: v3SectionId(idx, s),
      label: s.label || `Section ${idx + 1}`,
    }));
  }, [arrangement.sections]);

  const effectiveSelectedSectionId = useMemo(() => {
    if (!sectionOptions.length) return null;
    const exists = selectedSectionId && sectionOptions.some((o) => o.id === selectedSectionId);
    return exists ? selectedSectionId : sectionOptions[0].id;
  }, [sectionOptions, selectedSectionId]);

  const workflowLabel = useMemo(() => (workflowMode === "scratch" ? "New Track Creation" : "Audio guided"), [workflowMode]);

  useEffect(() => {
    if (!sectionOptions.length) return;
    if (effectiveSelectedSectionId && effectiveSelectedSectionId !== selectedSectionId) {
      setSelectedSectionId(effectiveSelectedSectionId);
    }
  }, [effectiveSelectedSectionId, sectionOptions.length, selectedSectionId, setSelectedSectionId]);

  useEffect(() => {
    const el = waveformWrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const w = Math.floor(el.clientWidth);
      if (w > 0) setWaveformWidth(w);
    });
    ro.observe(el);
    const w0 = Math.floor(el.clientWidth);
    if (w0 > 0) setWaveformWidth(w0);
    return () => ro.disconnect();
  }, []);

  const peakStats = useMemo(() => {
    const peaks = importState.waveform?.peaks;
    if (!peaks?.length) return null;
    let min = Infinity;
    let max = -Infinity;
    let sum = 0;
    let nz = 0;
    for (const v of peaks) {
      const n = Number(v) || 0;
      if (n < min) min = n;
      if (n > max) max = n;
      sum += n;
      if (n > 0) nz++;
    }
    const avg = sum / peaks.length;
    return { min, max, avg, nz };
  }, [importState.waveform?.peaks]);

  const stereoStats = useMemo(() => {
    const l = importState.waveform?.peaksL;
    const r = importState.waveform?.peaksR;
    if (!l?.length || !r?.length) return null;
    return { l: l.length, r: r.length };
  }, [importState.waveform?.peaksL, importState.waveform?.peaksR]);

  const displayedPeaks = useMemo(() => {
    const peaks = importState.waveform?.peaks;
    if (!peaks?.length) return [];
    return useNormalized ? normalizePeaks(peaks) : peaks;
  }, [importState.waveform?.peaks, useNormalized]);

  const peakPreview = useMemo(() => {
    const peaks = displayedPeaks;
    if (!peaks?.length) return null;
    return peaks.slice(0, 12).map((v) => (Number(v) || 0).toFixed(3)).join(", ");
  }, [displayedPeaks]);

  const canRun = useMemo(
    () => workflowMode === "audio" && !!importState.fileKey && importState.busyStage === "idle",
    [importState.fileKey, importState.busyStage, workflowMode]
  );

  const generateDisabledReasons = useMemo(() => {
    const reasons: string[] = [];
    if (importState.busyStage !== "idle") reasons.push("busy");
    if (!arrangement.sections?.length) reasons.push("sectionize");
    if (workflowMode === "audio") {
      if (!importState.waveform?.duration || importState.waveform.duration <= 0) reasons.push("load audio");
    }
    return reasons;
  }, [arrangement.sections?.length, importState.busyStage, importState.waveform?.duration, workflowMode]);

  const canGenerate = useMemo(() => {
    if (importState.busyStage !== "idle") return false;
    if (!arrangement.sections?.length) return false;
    if (workflowMode === "audio") {
      if (!importState.waveform?.duration || importState.waveform.duration <= 0) return false;
    }
    return true;
  }, [arrangement.sections?.length, importState.busyStage, importState.waveform?.duration, workflowMode]);

  const timeSigOptions = useMemo(() => {
    return {
      numerators: [2, 3, 4, 5, 6, 7, 9, 12],
      denominators: [2, 4, 8, 16],
    };
  }, []);

  const tempoStats = useMemo(() => {
    const pts = arrangement.tempoMap || [];
    if (!pts.length) return null;
    const bpms = pts.map((p) => Number((p as any)?.bpm) || 0).filter((b) => Number.isFinite(b) && b > 0);
    if (!bpms.length) return null;
    let min = Infinity;
    let max = -Infinity;
    let sum = 0;
    for (const b of bpms) {
      if (b < min) min = b;
      if (b > max) max = b;
      sum += b;
    }
    const avg = sum / bpms.length;
    const range = max - min;
    const stable = range <= 1.5;
    return { first: bpms[0], avg, min, max, range, stable, points: bpms.length };
  }, [arrangement.tempoMap]);

  const beatGridCount = useMemo(() => {
    const bt = (arrangement as any).beatTimes as number[] | undefined;
    if (!Array.isArray(bt) || bt.length < 2) return 0;
    return bt.length;
  }, [arrangement]);

  const onPickFile = useCallback(async (file: File) => {
    resetImport();
    setBeatTimes(null);
    setImportState({ busyStage: "upload", error: null, fileName: file.name });
    try {
      if (workflowMode !== "audio") {
        setWorkflowMode("audio" as V3WorkflowMode);
      }
      const up = await uploadFile(file);
      const key = up?.key;
      if (!key) throw new Error("Upload succeeded but no key returned");
      setImportState({ fileKey: key, busyStage: "waveform" });

      if (up?.waveform?.peaks?.length) {
        setImportState({
          waveform: {
            peaks: up.waveform.peaks,
            peaksL: up.waveform.peaksL,
            peaksR: up.waveform.peaksR,
            sr: up.waveform.sr,
            duration: up.waveform.duration,
          },
          busyStage: "idle",
        });
        return;
      }

      const wf = await fetchWaveform(key, 3000);
      setImportState({
        waveform: {
          peaks: wf.peaks || [],
          peaksL: wf.peaksL,
          peaksR: wf.peaksR,
          sr: wf.sr,
          duration: wf.duration,
        },
        busyStage: "idle",
      });
    } catch (e: any) {
      setImportState({ error: e?.message || String(e), busyStage: "idle" });
    }
  }, [resetImport, setBeatTimes, setImportState, setWorkflowMode, workflowMode]);

  const buildScratchSong = useCallback((opts?: { rows?: V3ScratchRow[]; preserveTimeSigConfirmed?: boolean; preserveSelectedIndex?: number | null; bpm?: number }) => {
    const resolvedBpm = (opts?.bpm ?? arrangement.tempoMap?.[0]?.bpm) || 120;
    if (!(resolvedBpm > 0)) {
      throw new Error("Invalid BPM for scratch song");
    }
    const beatsPerBar = arrangement.timeSig?.[0] || 4;
    const secondsPerBeat = 60 / resolvedBpm;
    const secondsPerBar = secondsPerBeat * beatsPerBar;

    const sourceRows = opts?.rows ?? scratchArrangement ?? [];
    const cleaned = (sourceRows || [])
      .map((row) => ({
        label: String((row as any)?.label || "section").toLowerCase(),
        bars: Math.max(1, Math.floor(Number((row as any)?.bars || 1))),
      }))
      .filter((row) => row.bars > 0);

    if (!cleaned.length) {
      throw new Error("Scratch arrangement must contain at least one section row");
    }

    let t = 0;
    const nextSections: ArrangementSection[] = cleaned.map((row, idx) => {
      const dur = row.bars * secondsPerBar;
      const startSec = t;
      const endSec = t + dur;
      t = endSec;
      return {
        label: row.label,
        startSec,
        endSec,
        conf: 1.0,
      };
    });

    const totalBars = cleaned.reduce((sum, r) => sum + r.bars, 0);
    const beatTimes = Array.from({ length: totalBars * beatsPerBar + 1 }).map((_, i) => i * secondsPerBeat);

    setSections(nextSections);
    setTempoMap([{ tSec: 0, bpm: resolvedBpm }]);
    setBeatTimes(beatTimes);

    setImportState({
      fileKey: null,
      fileName: null,
      waveform: null,
      error: null,
      timeSigConfirmed: true,
      busyStage: "idle",
    });
    setWorkflowMode("scratch" as V3WorkflowMode);

    const preservedIdx = typeof opts?.preserveSelectedIndex === "number" ? opts!.preserveSelectedIndex : 0;
    const nextIdx = Math.max(0, Math.min(nextSections.length - 1, preservedIdx));
    const nextId = nextSections.length ? v3SectionId(nextIdx, nextSections[nextIdx]) : null;
    setSelectedSectionId(nextId);
  }, [arrangement.tempoMap, arrangement.timeSig, scratchArrangement, setBeatTimes, setImportState, setSections, setSelectedSectionId, setTempoMap, setWorkflowMode]);

  const rebuildScratchPreservingSelection = useCallback(
    (rows: V3ScratchRow[]) => {
      const idx = (arrangement.sections || []).findIndex((s, i) => v3SectionId(i, s) === selectedSectionId);
      const preserveIdx = idx >= 0 ? idx : 0;
      buildScratchSong({ rows, preserveTimeSigConfirmed: true, preserveSelectedIndex: preserveIdx });
    },
    [arrangement.sections, buildScratchSong, selectedSectionId]
  );

  const commitScratchBpm = useCallback(
    (rawText: string) => {
      const raw = Number(String(rawText || "").trim());
      if (!Number.isFinite(raw)) return;
      const bpm = Math.max(20, Math.min(320, raw));
      setTempoMap([{ tSec: 0, bpm }]);
      setScratchTempoConfirmed(true);
      setImportState({ timeSigConfirmed: true });
      setScratchNeedsGenerate(true);
      try {
        const idx = (arrangement.sections || []).findIndex((s, i) => v3SectionId(i, s) === selectedSectionId);
        const preserveIdx = idx >= 0 ? idx : 0;
        buildScratchSong({
          rows: scratchArrangement || [],
          preserveTimeSigConfirmed: true,
          preserveSelectedIndex: preserveIdx,
          bpm,
        });
      } catch (err: any) {
        setImportState({ error: err?.message || String(err) });
      }
    },
    [arrangement.sections, buildScratchSong, scratchArrangement, selectedSectionId, setImportState, setTempoMap]
  );

  useEffect(() => {
    if (!scratchDrag) return;

    const prevUserSelect = document.body.style.userSelect;
    document.body.style.userSelect = "none";

    const onMove = (e: PointerEvent) => {
      if (!scratchDrag) return;
      if (importState.busyStage !== "idle") return;

      const x = e.clientX - scratchDrag.left;
      const frac = scratchDrag.width > 0 ? x / scratchDrag.width : 0;
      const targetBar = clampInt(Math.round(frac * scratchDrag.totalBars), 0, scratchDrag.totalBars);
      let delta = targetBar - scratchDrag.boundaryBar;

      const startA = scratchDrag.startBars[scratchDrag.boundaryIdx] ?? 1;
      const startB = scratchDrag.startBars[scratchDrag.boundaryIdx + 1] ?? 1;

      // Enforce min 1 bar each.
      const minDelta = -(startA - 1);
      const maxDelta = startB - 1;
      delta = clampInt(delta, minDelta, maxDelta);

      const nextBars = scratchDrag.startBars.slice();
      nextBars[scratchDrag.boundaryIdx] = Math.max(1, startA + delta);
      nextBars[scratchDrag.boundaryIdx + 1] = Math.max(1, startB - delta);

      const nextRows = (scratchArrangement || []).map((r, i) => ({
        label: String((r as any)?.label ?? "section"),
        bars: Math.max(1, Math.floor(Number(nextBars[i] ?? (r as any)?.bars ?? 1))),
      })) as V3ScratchRow[];

      setScratchArrangement(nextRows);
      try {
        rebuildScratchPreservingSelection(nextRows);
      } catch (err: any) {
        setImportState({ error: err?.message || String(err) });
      }
    };

    const onUp = () => {
      setScratchDrag(null);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
      document.body.style.userSelect = prevUserSelect;
    };
  }, [importState.busyStage, rebuildScratchPreservingSelection, scratchArrangement, scratchDrag, setImportState, setScratchArrangement]);

  const onAnalyzeTempo = useCallback(async () => {
    if (!importState.fileKey) return;
    setImportState({ busyStage: "tempo", error: null });
    try {
      const res = await analyzeTempo(importState.fileKey);
      const tempoMap = toTempoMap(res);
      setTempoMap(tempoMap);

      if (res?.timeSig?.length === 2) {
        setTimeSig(res.timeSig[0], res.timeSig[1]);
      }

      if (Array.isArray((res as any)?.beats) && (res as any).beats.length >= 2) {
        const beats = (res as any).beats
          .map((t: any) => Number(t))
          .filter((t: number) => Number.isFinite(t));
        if (beats.length >= 2) {
          const offset = Number(beats[0]) || 0;
          const normalized = beats
            .map((t: number) => t - offset)
            .filter((t: number) => Number.isFinite(t));
          setBeatTimes(normalized);
        }
      }

      setImportState({ busyStage: "idle", timeSigConfirmed: true });
    } catch (e: any) {
      setImportState({ error: e?.message || String(e), busyStage: "idle" });
    }
  }, [importState.fileKey, setBeatTimes, setImportState, setTempoMap, setTimeSig]);

  const onSectionize = useCallback(async () => {
    if (!importState.fileKey) return;
    setImportState({ busyStage: "sectionize", error: null });
    try {
      const bpm = arrangement.tempoMap?.[0]?.bpm || 120;
      const res = await sectionizeSmart(importState.fileKey, bpm);
      const sections = toSections(res);
      if (sections.length) setSections(sections);
      setImportState({ busyStage: "idle" });
    } catch (e: any) {
      setImportState({ error: e?.message || String(e), busyStage: "idle" });
    }
  }, [arrangement.tempoMap, importState.fileKey, setImportState, setSections]);

  const onAlign = useCallback(async () => {
    if (!importState.fileKey) return;
    if (!arrangement.sections.length) return;
    setImportState({ busyStage: "align", error: null });
    try {
      const payload = arrangement.sections.map((s) => ({ start: s.startSec, end: s.endSec }));
      const res = await alignSections(importState.fileKey, payload);
      const aligned = res?.sections || [];
      const next: ArrangementSection[] = arrangement.sections.map((s, i) => {
        const a = aligned[i];
        if (!a) return s;
        return { ...s, startSec: Number(a.start) || s.startSec, endSec: Number(a.end) || s.endSec };
      });
      setSections(next);

      // Align currently returns a coarse tempo scalar; do NOT flatten an existing tempo map / beat grid.
      // Only apply as a fallback when we have no meaningful tempo data yet.
      if (
        typeof res?.tempo === "number" &&
        (!arrangement.beatTimes || arrangement.beatTimes.length < 2) &&
        (!arrangement.tempoMap || arrangement.tempoMap.length <= 1)
      ) {
        setTempoMap([{ tSec: 0, bpm: res.tempo }]);
      }
      setImportState({ busyStage: "idle" });
    } catch (e: any) {
      setImportState({ error: e?.message || String(e), busyStage: "idle" });
    }
  }, [arrangement.beatTimes, arrangement.sections, arrangement.tempoMap, importState.fileKey, setImportState, setSections, setTempoMap]);

  const onGenerate = useCallback(async () => {
    setImportState({ busyStage: "generate", error: null });
    try {
      if (!arrangement.sections?.length) {
        throw new Error("At least one arrangement section is required before generating");
      }

      let durationSec = 0;
      if (workflowMode === "audio") {
        durationSec = Number(importState.waveform?.duration || 0);
        if (!Number.isFinite(durationSec) || durationSec <= 0) {
          throw new Error("Missing/invalid audio duration; load audio first");
        }
      } else {
        durationSec = arrangement.sections.reduce((mx, s) => Math.max(mx, Number(s.endSec) || 0), 0);
        if (!Number.isFinite(durationSec) || durationSec <= 0) {
          throw new Error("Scratch arrangement produced invalid duration; rebuild scratch song");
        }
      }

      const fallbackBpm = arrangement.tempoMap?.[0]?.bpm || 120;
      const beatsPerBar = arrangement.timeSig?.[0] || 4;

      const bars = (() => {
        if (Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2) {
          const beatCount = arrangement.beatTimes.length - 1;
          return Math.max(1, Math.floor(beatCount / Math.max(1, beatsPerBar)));
        }
        const bpm = Number(fallbackBpm) || 120;
        const beats = (Math.max(0, durationSec) * Math.max(1e-6, bpm)) / 60;
        return Math.max(1, Math.ceil(beats / Math.max(1, beatsPerBar)));
      })();

      let tempos: number[] = [];
      if (Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2) {
        tempos = temposFromBeatTimes(arrangement.beatTimes, beatsPerBar);
        if (!tempos.length) {
          throw new Error("Beat grid is present but does not contain a full bar; cannot generate");
        }
      }

      const selectedDrummer = String(globalDefaults.publicDrummerId || globalDefaults.drummer || "").trim();
      if (!selectedDrummer) {
        setInspectorView("global");
        setDrummerPickerTarget({ scope: "global" });
        setDrummerPickerOpen(true);
        setImportState({ error: "Select a drummer profile before generating.", busyStage: "idle" });
        return;
      }

      let startMeasure = 0;
      let endMeasure = bars - 1;
      let sectionId: string = "full-song";

      if (globalDefaults.buildScope === "selected_section") {
        const activeSectionId = effectiveSelectedSectionId;
        if (!activeSectionId) {
          throw new Error("Build scope is selected section, but no section is selected");
        }
        const idx = (arrangement.sections || []).findIndex((s, i) => v3SectionId(i, s) === activeSectionId);
        if (idx < 0) {
          throw new Error("Selected section is not present in the current arrangement");
        }
        const sec = arrangement.sections[idx];
        const startSec = Number(sec.startSec) || 0;
        const endSec = Number(sec.endSec) || 0;
        if (!(endSec > startSec)) {
          throw new Error("Selected section has invalid start/end");
        }

        let startBeats = 0;
        let endBeats = 0;
        if (Array.isArray(arrangement.beatTimes) && arrangement.beatTimes.length >= 2) {
          startBeats = beatsAtTimeFromBeatTimes(arrangement.beatTimes, startSec);
          endBeats = beatsAtTimeFromBeatTimes(arrangement.beatTimes, endSec);
        } else {
          startBeats = beatsAtTimeFromTempoMap(arrangement.tempoMap || [], fallbackBpm, startSec);
          endBeats = beatsAtTimeFromTempoMap(arrangement.tempoMap || [], fallbackBpm, endSec);
        }
        const bpb = Math.max(1, Number(beatsPerBar) || 4);
        const sBar = Math.max(0, Math.floor(startBeats / bpb));
        const eBar = Math.max(sBar, Math.floor((Math.max(startBeats, endBeats - 1e-6)) / bpb));
        startMeasure = Math.max(0, Math.min(bars - 1, sBar));
        endMeasure = Math.max(startMeasure, Math.min(bars - 1, eBar));
        sectionId = activeSectionId;
      }

      const cfg: DrumGenerationConfig = {
        sectionId,
        startMeasure,
        endMeasure,
        tempos,
        timeSignature: [arrangement.timeSig?.[0] || 4, arrangement.timeSig?.[1] || 4],
        style: globalDefaults.style || "rock",
        drummer: selectedDrummer,
        publicDrummerId: selectedDrummer,
        globalPresetStack: (() => {
          const sec = (sectionOverrides as any)?.[String(sectionId)];
          const inheritGlobal = sec?.inheritGlobalPresets !== false;
          if (!inheritGlobal) return [];
          return Array.isArray((globalDefaults as any)?.presetStack) ? ((globalDefaults as any).presetStack as any) : [];
        })(),
        sectionPresetStack: (() => {
          const sec = (sectionOverrides as any)?.[String(sectionId)];
          return Array.isArray(sec?.presetStack) ? sec.presetStack : [];
        })(),
        chorusRidePreference: Number(globalDefaults.chorusRidePreference ?? 0),
        cymbalFocusMode: globalDefaults.cymbalFocusMode,
        hatsToRideBlend: Number(globalDefaults.hatsToRideBlend ?? 0),
        hatsToRideThreshold: Number(globalDefaults.hatsToRideThreshold ?? 0.6),
        rideBellPercent: Number(globalDefaults.rideBellPercent ?? 0.2),
        footHatPulseSubdivision: globalDefaults.footHatPulseSubdivision,
        footHatPulseApply: globalDefaults.footHatPulseApply,
        forceFillBars: (() => {
          const secKey = String(sectionId);
          const edits = (barEdits as any)?.[secKey] || {};
          return Object.keys(edits)
            .map((k: any) => Number(k))
            .filter((bi: number) => Number.isFinite(bi) && !!(edits[bi]?.forceFill));
        })(),
        suppressFillBars: (() => {
          const secKey = String(sectionId);
          const edits = (barEdits as any)?.[secKey] || {};
          return Object.keys(edits)
            .map((k: any) => Number(k))
            .filter((bi: number) => Number.isFinite(bi) && !!(edits[bi]?.suppressFill));
        })(),
        selectedGrooveId: globalDefaults.selectedGrooveId,
        grooveUse: globalDefaults.grooveUse,
        fillGrooveId: globalDefaults.fillGrooveId,
        // Do NOT force EGMD here; the backend will interpret groove ids via the catalog.
        // If the user selected a groove from a specific source, we persist that in globalDefaults.grooveSource.
        grooveSource: globalDefaults.grooveSource,
        grooveMode: globalDefaults.grooveMode,
        styleGroup: globalDefaults.styleGroup || globalDefaults.style,
        egmdPhraseId: (globalDefaults as any).egmdPhraseId,
        egmdMidiPath: (globalDefaults as any).egmdMidiPath,
        egmdFillMidiPath: (globalDefaults as any).egmdFillMidiPath,
        intensity: Number(globalDefaults.intensity ?? 0.7),
        variation: Number(globalDefaults.variation ?? 0.8),
        generationMode: globalDefaults.generationMode,
        humanize: !!globalDefaults.humanize,
        fillLocations: [],
        fillType: (globalDefaults.fillControls?.fillType || "auto") as string,
        fillDensity: Number(globalDefaults.fillControls?.density ?? 0.7),
        humanizeAmount: Number(globalDefaults.humanizeAmount ?? 0.7),
        ghostNoteAmount: Number(globalDefaults.ghostNoteAmount ?? 0.7),
        swingAmount: Number(globalDefaults.swingAmount ?? 0),
        buildScope: globalDefaults.buildScope || (workflowMode === "scratch" ? "selected_section" : "full_song"),
        songStyle: undefined,
        songSections: (() => {
          // Song Mode activation (required by Drum Builder v2.0): provide a simple section roadmap.
          // Scratch mode: authoritative from scratchArrangement.
          if (workflowMode === "scratch") {
            const rows = Array.isArray(scratchArrangement) ? scratchArrangement : [];
            return rows
              .map((r) => ({ name: String((r as any)?.label || "section"), bars: Math.max(0, Math.round(Number((r as any)?.bars || 0))) }))
              .filter((s) => s.bars > 0);
          }

          // Audio mode: derive bar spans from arrangement sections.
          const secs = Array.isArray(arrangement.sections) ? arrangement.sections : [];
          if (!secs.length) return undefined;
          const beatsPerBar = arrangement.timeSig?.[0] || 4;
          const fallbackBpm = arrangement.tempoMap?.[0]?.bpm || 120;
          const out = secs
            .map((s, idx) => {
              const r = barRangeForSection({
                section: s,
                idx,
                beatsPerBar,
                beatTimes: arrangement.beatTimes,
                tempoMap: arrangement.tempoMap,
                fallbackBpm,
              });
              const bars = Math.max(0, r.endBar - r.startBar + 1);
              return { name: String((s as any)?.label || `section_${idx + 1}`), bars };
            })
            .filter((s) => s.bars > 0);
          return out.length ? out : undefined;
        })(),
        guideEnabled: !!globalDefaults.guideEnabled,
        guideInstrument: globalDefaults.guideInstrument,
      };

      try {
        console.debug("[V3 DrumGen] request", {
          sectionId,
          drummer: cfg.drummer,
          publicDrummerId: cfg.publicDrummerId,
          style: cfg.style,
          styleGroup: cfg.styleGroup,
          selectedGrooveId: cfg.selectedGrooveId,
          fillGrooveId: cfg.fillGrooveId,
          grooveUse: cfg.grooveUse,
          grooveSource: cfg.grooveSource,
          grooveMode: cfg.grooveMode,
          egmdPhraseId: (cfg as any).egmdPhraseId,
          globalPresetStackLen: Array.isArray(cfg.globalPresetStack) ? cfg.globalPresetStack.length : 0,
          sectionPresetStackLen: Array.isArray(cfg.sectionPresetStack) ? cfg.sectionPresetStack.length : 0,
          globalPresetStack: cfg.globalPresetStack,
          sectionPresetStack: cfg.sectionPresetStack,
        });
      } catch {
        // ignore
      }

      const resp = await generateDrums(cfg);
      const respOk = (resp as any)?.ok;
      const respErr = (resp as any)?.error;
      if (respOk === false) {
        throw new Error(respErr ? String(respErr) : "Drum generation failed (ok=false)");
      }
      if (respErr) {
        // If the backend uses an error-first shape but still returns HTTP 200.
        throw new Error(String(respErr));
      }

      try {
        const md = (resp as any)?.metadata ?? null;
        const debugSnapshot: any = {
          payloadSectionId: cfg.sectionId ?? null,
          payloadGrooveSource: (cfg as any)?.grooveSource ?? null,
          payloadGrooveMode: (cfg as any)?.grooveMode ?? null,
          payloadEgmdPhraseId: (cfg as any)?.egmdPhraseId ?? null,
          payloadEgmdMidiPath: (cfg as any)?.egmdMidiPath ?? null,
          hasDrumTrack: Boolean((resp as any)?.drum_track),
          drumTrackNotes: Array.isArray((resp as any)?.drum_track?.notes) ? (resp as any).drum_track.notes.length : 0,
          hasLegacyNotes: Array.isArray((resp as any)?.midi_notes),
          legacyNotesCount: Array.isArray((resp as any)?.midi_notes) ? (resp as any).midi_notes.length : 0,
          builderVersion: md?.builder_version ?? md?.builderVersion ?? null,
          performanceFromLlm: md?.performance_from_llm ?? md?.performanceFromLlm ?? null,
          egmdExactMode: md?.egmd_exact_mode ?? null,
          egmdPhraseUsed: md?.egmdPhrase ?? null,
          egmdMidiPathUsed: md?.egmd_midi_path ?? null,
          grooveSourceUsed: md?.groove_source ?? null,
          grooveModeUsed: md?.groove_mode ?? null,
          internalEventsCount: md?.internal_events_count ?? null,
          internalEventsFingerprint: md?.internal_events_fingerprint ?? null,
          internalEventsBreakdown: md?.internal_events_breakdown ?? null,
          egmdMidiBreakdown: md?.egmd_midi_breakdown ?? null,
          finalTrackBreakdown: md?.final_track_breakdown ?? null,
          breakdownDiff: md?.breakdown_diff ?? null,
        };
        console.log("🥁 DCSM debug:", debugSnapshot);
        try {
          const json = JSON.stringify(debugSnapshot);
          console.log("🥁 DCSM debug json:", json);
        } catch {
          // ignore
        }
      } catch {
        // ignore
      }

      const midiB64 =
        (resp as any)?.midi_base64 ??
        (resp as any)?.midi_smf_base64 ??
        (resp as any)?.midi_b64 ??
        (resp as any)?.base64;
      if (!midiB64) {
        const keys = resp && typeof resp === "object" ? Object.keys(resp as any).slice(0, 50).join(", ") : String(resp);
        throw new Error(`Generation succeeded but no MIDI base64 returned (expected one of: midi_base64, midi_smf_base64, midi_b64, base64). Response keys: ${keys}`);
      }

      const drumTrack = (resp as any)?.drum_track;
      if (!drumTrack) {
        throw new Error("Generation succeeded but no drum_track returned (required for Drum Performance Grid)");
      }

      try {
        (drumTrack as any).__dtkGenMetadata = (resp as any)?.metadata;
      } catch {
        // ignore
      }

      try {
        const notes = Array.isArray((drumTrack as any)?.notes) ? ((drumTrack as any).notes as any[]) : [];
        const noteSig = notes
          .map((n) => {
            const bi = Number((n as any)?.barIndex ?? 0) || 0;
            const ti = Number((n as any)?.tickInBar ?? 0) || 0;
            const inst = String((n as any)?.instrumentId || (n as any)?.midiPitch || "");
            const vel = Number((n as any)?.velocity ?? (n as any)?.vel ?? 0) || 0;
            return `${bi}:${ti}:${inst}:${vel}`;
          })
          .sort()
          .join("|");
        const fingerprint = `${notes.length}:${noteSig.length}:${noteSig.slice(0, 120)}`;

        const byInst: Record<string, number> = {};
        for (const n of notes) {
          const k = String((n as any)?.instrumentId || (n as any)?.midiPitch || "unknown");
          byInst[k] = (byInst[k] || 0) + 1;
        }
        const topInst = Object.entries(byInst)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 8);
        console.debug("[V3 DrumGen] result", {
          sectionId,
          notesLen: notes.length,
          ppq: (drumTrack as any)?.resolution_ppq,
          style_id: (drumTrack as any)?.style_id,
          topInst,
          fingerprint,
          metadata: (resp as any)?.metadata,
        });

        try {
          const w = window as any;
          const prev = w.__v3LastGen;
          const cur = {
            sectionId,
            drummer: cfg.drummer,
            publicDrummerId: cfg.publicDrummerId,
            globalPresetStack: cfg.globalPresetStack,
            sectionPresetStack: cfg.sectionPresetStack,
            fingerprint,
          };
          if (prev && prev.fingerprint === fingerprint) {
            const prevStacks = JSON.stringify({ g: prev.globalPresetStack || [], s: prev.sectionPresetStack || [] });
            const curStacks = JSON.stringify({ g: cur.globalPresetStack || [], s: cur.sectionPresetStack || [] });
            if (prevStacks !== curStacks) {
              console.warn("[V3 DrumGen] fingerprint unchanged despite preset stack change", { prev, cur });
            }
          }
          w.__v3LastGen = cur;
        } catch {
          // ignore
        }
      } catch {
        // ignore
      }
      setGeneratedDrumTrack(drumTrack);
      setScratchNeedsGenerate(false);

      const binStr = window.atob(String(midiB64));
      const bytes = new Uint8Array(binStr.length);
      for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);
      const arrayBuffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;

      useMidi.getState().clearAll();
      await importSMF(arrayBuffer, true);

      setEditorTab("piano_roll");

      setImportState({ busyStage: "idle" });
    } catch (e: any) {
      setImportState({ error: e?.message || String(e), busyStage: "idle" });
    }
  }, [arrangement.beatTimes, arrangement.sections, arrangement.tempoMap, arrangement.timeSig, effectiveSelectedSectionId, globalDefaults, importState.waveform?.duration, sectionOverrides, setEditorTab, setGeneratedDrumTrack, setImportState, workflowMode]);

  useEffect(() => {
    if (!autoGenerateNonce) return;
    if (importState.busyStage !== "idle") return;
    if (!canGenerate) return;

    // Fire and forget; onGenerate handles errors into importState.
    void onGenerate();
  }, [autoGenerateNonce]);

  const stageLabel: Record<BusyStage, string> = {
    idle: "Idle",
    upload: "Uploading",
    waveform: "Waveform",
    tempo: "Analyzing tempo",
    sectionize: "Sectionizing",
    align: "Aligning",
    generate: "Generating drums",
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-xs font-semibold text-slate-200 tracking-wide">Import / Analysis</div>
          <div className="text-[11px] text-slate-500 mt-0.5 truncate">
            {importState.fileKey ? `File: ${importState.fileName || importState.fileKey}` : "No file loaded"}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 px-2 py-1 rounded border border-slate-800 bg-slate-950">
            <div className="text-[11px] text-slate-400">Mode</div>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1 text-[11px] text-slate-200">
                <input
                  type="radio"
                  name="v3-workflow-mode"
                  checked={workflowMode === "audio"}
                  disabled={importState.busyStage !== "idle"}
                  onChange={() => {
                    setWorkflowMode("audio" as V3WorkflowMode);
                    setImportState({ error: null });
                  }}
                />
                Audio guided
              </label>
              <label className="flex items-center gap-1 text-[11px] text-slate-200">
                <input
                  type="radio"
                  name="v3-workflow-mode"
                  checked={workflowMode === "scratch"}
                  disabled={importState.busyStage !== "idle"}
                  onChange={() => {
                    setWorkflowMode("scratch" as V3WorkflowMode);
                    setImportState({ error: null });
                  }}
                />
                New Track Creation
              </label>
            </div>
          </div>

          <button
            type="button"
            className="px-3 py-1.5 rounded bg-emerald-600 text-white text-xs disabled:opacity-50"
            onClick={() => fileRef.current?.click()}
            disabled={importState.busyStage !== "idle" || workflowMode !== "audio"}
          >
            Load audio
          </button>
          <button
            type="button"
            className="px-3 py-1.5 rounded bg-slate-800 text-slate-100 text-xs disabled:opacity-50"
            onClick={onAnalyzeTempo}
            disabled={!canRun}
          >
            Analyze tempo
          </button>
          <button
            type="button"
            className="px-3 py-1.5 rounded bg-slate-800 text-slate-100 text-xs disabled:opacity-50"
            onClick={onSectionize}
            disabled={!canRun}
          >
            Sectionize
          </button>
          <button
            type="button"
            className="px-3 py-1.5 rounded bg-slate-800 text-slate-100 text-xs disabled:opacity-50"
            onClick={onAlign}
            disabled={!canRun || !arrangement.sections.length}
          >
            Align
          </button>

          {workflowMode === "scratch" && (
            <button
              type="button"
              className="px-3 py-1.5 rounded bg-indigo-600 text-white text-xs disabled:opacity-50"
              onClick={() => {
                try {
                  buildScratchSong();
                } catch (e: any) {
                  setImportState({ error: e?.message || String(e) });
                }
              }}
              disabled={importState.busyStage !== "idle"}
            >
              Build New Track
            </button>
          )}

          <div className="flex items-center gap-1 px-2 py-1 rounded border border-slate-800 bg-slate-950">
            <div className="text-[11px] text-slate-400">Scope</div>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1 text-[11px] text-slate-200">
                <input
                  type="radio"
                  name="v3-build-scope"
                  checked={globalDefaults.buildScope === "selected_section"}
                  disabled={importState.busyStage !== "idle" || workflowMode !== "scratch"}
                  onChange={() => setGlobalDefaults({ buildScope: "selected_section" })}
                />
                Selected section
              </label>
              <label className="flex items-center gap-1 text-[11px] text-slate-200">
                <input
                  type="radio"
                  name="v3-build-scope"
                  checked={globalDefaults.buildScope === "full_song"}
                  disabled={importState.busyStage !== "idle" || workflowMode !== "scratch"}
                  onChange={() => setGlobalDefaults({ buildScope: "full_song" })}
                />
                Full song
              </label>
            </div>
          </div>

          <button
            type="button"
            className={
              "px-3 py-1.5 rounded text-white text-xs disabled:opacity-60 " +
              (canGenerate ? "bg-amber-600 shadow-[0_0_0_2px_rgba(245,158,11,0.18)]" : "bg-slate-700")
            }
            onClick={onGenerate}
            disabled={!canGenerate}
          >
            Generate (v3)
          </button>
          <button
            type="button"
            className="px-3 py-1.5 rounded bg-slate-900 text-slate-300 text-xs border border-slate-700 disabled:opacity-50"
            onClick={onReset}
            disabled={importState.busyStage !== "idle"}
          >
            Reset
          </button>
        </div>
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="audio/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onPickFile(f);
          e.currentTarget.value = "";
        }}
      />

      <div className="px-4 py-3 grid grid-cols-12 gap-4 items-start">
        <div className="col-span-4">
          <div className="text-[11px] text-slate-400">Status</div>
          <div className="mt-1 text-sm font-semibold text-slate-200">{stageLabel[importState.busyStage]}</div>
          {importState.error && (
            <div className="mt-2 text-[11px] text-rose-400">{importState.error}</div>
          )}

          {coach?.lastAnalysis ? (
            <div className="mt-3">
              <div className="text-[11px] text-slate-400">
                <div className="text-slate-500">Coach</div>
                {((coach.lastAnalysis as any)?.section_id || (coach.lastAnalysis as any)?.section_label) ? (
                  <div className="mt-1 text-slate-500">
                    Target: {String((coach.lastAnalysis as any)?.section_id || "all")}
                    {(coach.lastAnalysis as any)?.section_label ? ` • ${String((coach.lastAnalysis as any).section_label)}` : ""}
                  </div>
                ) : null}
                {typeof (coach.lastTrackMetrics as any)?.overall_score === "number" ? (
                  <div className="mt-1 text-slate-300">
                    Overall: {Math.round(((coach.lastTrackMetrics as any).overall_score || 0) * 100)}% (track)
                  </div>
                ) : null}
                {Array.isArray((coach.lastAnalysis as any)?.suggestions) ? (
                  <div className="mt-1 space-y-0.5">
                    {(coach.lastAnalysis as any).suggestions.slice(0, 3).map((s: any, i: number) => (
                      <div key={i} className="text-slate-300">
                        {String(s)}
                      </div>
                    ))}
                  </div>
                ) : null}
                {(coach.lastAnalysis as any)?.config_patch ? <div className="mt-1 text-slate-500">Patch ready</div> : null}
                {coach?.snapshot?.before ? (
                  <div className="mt-1 text-slate-500">
                    A/B: before {coach.snapshot.before.metrics ? Math.round((coach.snapshot.before.metrics.overall_score || 0) * 100) : "?"}%
                    {coach.snapshot.after?.metrics
                      ? ` → after ${Math.round((coach.snapshot.after.metrics.overall_score || 0) * 100)}%`
                      : coach.snapshotPendingAfter
                        ? " → after (pending)"
                        : ""}
                  </div>
                ) : null}
                {(coach.lastAnalysis as any)?.error ? (
                  <div className="mt-1 text-rose-400">{String((coach.lastAnalysis as any).error)}</div>
                ) : null}
              </div>
            </div>
          ) : null}

          <div className="mt-3 text-[11px] text-slate-500">
            Workflow: {workflowLabel}
            {" "}| 
            Tempo points: {arrangement.tempoMap.length}
            {beatGridCount ? ` • Beat grid: ${beatGridCount}` : " • Beat grid: none"}
            {" "}| Time sig: {arrangement.timeSig[0]}/{arrangement.timeSig[1]} | Sections: {arrangement.sections.length}
          </div>

          {workflowMode === "scratch" && arrangement.sections.length ? (
            <div className="mt-2 text-[11px] text-slate-400">
              <div className="text-[11px] text-slate-400">Selected section</div>
              <select
                className="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                value={effectiveSelectedSectionId || ""}
                onChange={(e) => setSelectedSectionId(e.target.value || null)}
                disabled={importState.busyStage !== "idle"}
              >
                {sectionOptions.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          {workflowMode === "scratch" ? (
            <div className="mt-3 grid grid-cols-2 gap-2">
              <label className="block">
                <div className="text-[11px] text-slate-400">Style</div>
                <input
                  className="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                  value={globalDefaults.style || ""}
                  onChange={(e) => setGlobalDefaults({ style: e.target.value })}
                  disabled={importState.busyStage !== "idle"}
                  placeholder="rock"
                />
              </label>
              <label className="block">
                <div className="text-[11px] text-slate-400">Drummer</div>
                <select
                  className="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                  value={globalDefaults.publicDrummerId || globalDefaults.drummer || ""}
                  onChange={(e) => {
                    const id = e.target.value;
                    setGlobalDefaults({ publicDrummerId: id, drummer: id });
                    setScratchNeedsGenerate(true);
                  }}
                  disabled={importState.busyStage !== "idle"}
                >
                  <option value="">Select drummer profile…</option>
                  {drummerOptions.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.display_name}
                    </option>
                  ))}
                </select>
              </label>
              {drummerError ? (
                <div className="col-span-2 text-[11px] text-rose-400">{drummerError}</div>
              ) : null}
            </div>
          ) : null}

          {tempoStats && (
            <div className="mt-2 text-[11px] text-slate-400">
              <div>
                Tempo: {tempoStats.first.toFixed(1)} bpm
                {tempoStats.points > 1 ? (
                  <>
                    {" "}• avg {tempoStats.avg.toFixed(1)} • min {tempoStats.min.toFixed(1)} • max {tempoStats.max.toFixed(1)}
                  </>
                ) : null}
              </div>
              {tempoStats.points > 1 && (
                <div className={tempoStats.stable ? "text-emerald-300/90" : "text-amber-300/90"}>
                  Tempo stability: {tempoStats.stable ? "stable" : `unstable (±${(tempoStats.range / 2).toFixed(1)} bpm)`}
                </div>
              )}
            </div>
          )}

          {!canGenerate && generateDisabledReasons.length > 0 && (
            <div className="mt-2 text-[11px] text-amber-300/90">
              To enable Generate: {generateDisabledReasons.join(" • ")}
            </div>
          )}

          {peakStats && (
            <div className="mt-2 text-[11px] text-slate-500">
              Peaks: min {peakStats.min.toFixed(3)} max {peakStats.max.toFixed(3)} avg {peakStats.avg.toFixed(3)} nonzero {peakStats.nz}/{importState.waveform?.peaks.length}
            </div>
          )}
          {stereoStats && (
            <div className="mt-1 text-[11px] text-slate-600">
              Stereo lanes: L {stereoStats.l} / R {stereoStats.r}
            </div>
          )}

          {importState.waveform?.peaks?.length ? (
            <label className="mt-3 flex items-center gap-2 text-[11px] text-slate-400 select-none">
              <input type="checkbox" checked={useNormalized} onChange={(e) => setUseNormalized(e.target.checked)} />
              Normalize peaks
            </label>
          ) : null}

          {peakPreview && (
            <div className="mt-2 text-[11px] text-slate-600 break-words">{peakPreview}</div>
          )}
        </div>

        <div className="col-span-8" ref={waveformWrapRef}>
          {workflowMode === "scratch" ? (
            <div className="mb-2 rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="text-[11px] text-slate-300 font-semibold">New Track Creation</div>
              <div className="mt-1 text-[11px] text-slate-500">
                Define the song form as sections with bar counts.
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-2">
                <div className="text-[11px] text-slate-400">BPM</div>
                <input
                  className={
                    "w-20 bg-slate-900 border rounded px-2 py-1 text-[11px] text-slate-100 " +
                    (scratchTempoConfirmed ? "border-emerald-600" : "border-amber-600")
                  }
                  value={scratchBpmText}
                  onChange={(e) => {
                    setScratchBpmText(e.target.value);
                  }}
                  onBlur={() => commitScratchBpm(scratchBpmText)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.currentTarget.blur();
                    }
                  }}
                  onClick={(e) => e.stopPropagation()}
                  disabled={importState.busyStage !== "idle"}
                />

                <div
                  className={
                    "ml-2 flex items-center gap-1 px-2 py-1 rounded border bg-slate-950 " +
                    (scratchTempoConfirmed ? "border-emerald-700" : "border-amber-700")
                  }
                >
                  <div className="text-[11px] text-slate-400">Time Sig</div>
                  <select
                    className="bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-[11px]"
                    value={arrangement.timeSig?.[0] || 4}
                    onChange={(e) => {
                      const n = Number(e.target.value) || 4;
                      setTimeSig(n, arrangement.timeSig?.[1] || 4);
                      setImportState({ timeSigConfirmed: true });
                      setScratchTempoConfirmed(true);
                      setScratchNeedsGenerate(true);
                    }}
                    disabled={importState.busyStage !== "idle"}
                  >
                    {timeSigOptions.numerators.map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                  <div className="text-[11px] text-slate-500">/</div>
                  <select
                    className="bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-[11px]"
                    value={arrangement.timeSig?.[1] || 4}
                    onChange={(e) => {
                      const d = Number(e.target.value) || 4;
                      setTimeSig(arrangement.timeSig?.[0] || 4, d);
                      setImportState({ timeSigConfirmed: true });
                      setScratchTempoConfirmed(true);
                      setScratchNeedsGenerate(true);
                    }}
                    disabled={importState.busyStage !== "idle"}
                  >
                    {timeSigOptions.denominators.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>

                  <div
                    className={
                      "ml-2 text-[10px] px-1.5 py-0.5 rounded border " +
                      (scratchTempoConfirmed
                        ? "border-emerald-700 text-emerald-300 bg-emerald-900/10"
                        : "border-amber-700 text-amber-300 bg-amber-900/10")
                    }
                  >
                    {scratchTempoConfirmed ? "Confirmed" : "Set BPM / Time Sig"}
                  </div>
                </div>

                <div className="text-[11px] text-slate-500">
                  Total bars: {(scratchArrangement || []).reduce((sum, r) => sum + Math.max(1, Number((r as any)?.bars || 1)), 0)}
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2">
                <label className="block">
                  <div className="text-[11px] text-slate-400">Groove Source</div>
                  <select
                    className="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                    value={String(globalDefaults.grooveUse || "use_as_groove")}
                    onChange={(e) => setGlobalDefaults({ grooveUse: e.target.value as any })}
                    disabled={importState.busyStage !== "idle"}
                  >
                    <option value="use_as_groove">Use selected groove</option>
                    <option value="use_as_fill">Use selected fill</option>
                  </select>
                </label>
                <div className="block">
                  <div className="text-[11px] text-slate-400">Basic Drum Style</div>
                  <button
                    type="button"
                    className="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 hover:border-slate-500"
                    onClick={() => setGrooveModalOpen(true)}
                    disabled={importState.busyStage !== "idle"}
                  >
                    Choose groove / fill…
                  </button>
                </div>
                <div className="col-span-2 text-[11px] text-slate-500">
                  Groove: {globalDefaults.selectedGrooveId || "(none)"} • Fill: {globalDefaults.fillGrooveId || "(none)"}
                </div>

                <div className="col-span-2 text-[10px] text-slate-600 break-words">
                  StyleGroup: {String(globalDefaults.styleGroup || "-")} • GrooveMode: {String(globalDefaults.grooveMode || "-")} • GrooveSource:{" "}
                  {String(globalDefaults.grooveSource || "-")} • EGMD Phrase: {String((globalDefaults as any).egmdPhraseId ?? "-")}
                </div>

                <div className="col-span-2 text-[10px] text-slate-600 break-words">
                  Selected EGMD MIDI:{" "}
                  {String((globalDefaults as any).egmdMidiPath ?? "-")}
                  {String((globalDefaults as any).egmdFillMidiPath ? ` • fill: ${String((globalDefaults as any).egmdFillMidiPath)}` : "")}
                </div>

                <div className="col-span-2 text-[10px] text-slate-600 break-words">
                  Last Gen EGMD Phrase:{" "}
                  {String((generatedDrumTrack as any)?.__dtkGenMetadata?.egmdPhrase?.phrase_id ?? "-")}
                  {String((generatedDrumTrack as any)?.__dtkGenMetadata?.egmdPhrase?.midi_path ? ` • ${String((generatedDrumTrack as any)?.__dtkGenMetadata?.egmdPhrase?.midi_path)}` : "")}
                </div>

                {workflowMode === "scratch" && scratchNeedsGenerate ? (
                  <div className="col-span-2 text-[11px] text-amber-300/90">
                    Changes pending. Click <span className="font-semibold">Generate (v3)</span> to apply.
                  </div>
                ) : null}
              </div>

              <div className="mt-3 space-y-2">
                {(scratchArrangement || []).map((row, idx) => {
                  const sec = (arrangement.sections || [])[idx];
                  const rowId = sec ? v3SectionId(idx, sec) : null;
                  const selected = rowId && selectedSectionId === rowId;

                  const beatsPerBar = arrangement.timeSig?.[0] || 4;
                  const fallbackBpm = arrangement.tempoMap?.[0]?.bpm || 120;
                  const barInfo = sec
                    ? barRangeForSection({
                        section: sec,
                        idx,
                        beatsPerBar,
                        beatTimes: arrangement.beatTimes,
                        tempoMap: arrangement.tempoMap,
                        fallbackBpm,
                      })
                    : null;

                  return (
                    <div
                      key={idx}
                      className={
                        "w-full text-left grid grid-cols-12 gap-2 items-center rounded p-1 border " +
                        (selected ? "border-amber-400/60 bg-amber-500/10" : "border-transparent hover:border-slate-700")
                      }
                      onClick={() => {
                        if (importState.busyStage !== "idle") return;
                        if (rowId) setSelectedSectionId(rowId);
                      }}
                    >
                    <input
                      className="col-span-7 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                      value={String((row as any)?.label ?? "")}
                      onChange={(e) => {
                        e.stopPropagation();
                        const next = (scratchArrangement || []).slice();
                        next[idx] = { ...(next[idx] as V3ScratchRow), label: e.target.value };
                        setScratchArrangement(next);
                        try {
                          rebuildScratchPreservingSelection(next);
                        } catch (err: any) {
                          setImportState({ error: err?.message || String(err) });
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      disabled={importState.busyStage !== "idle"}
                      placeholder="section label"
                    />
                    <input
                      className="col-span-3 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                      value={String((row as any)?.bars ?? 1)}
                      onChange={(e) => {
                        e.stopPropagation();
                        const v = Math.max(1, Math.floor(Number(e.target.value || 1)));
                        const next = (scratchArrangement || []).slice();
                        next[idx] = { ...(next[idx] as V3ScratchRow), bars: v };
                        setScratchArrangement(next);
                        try {
                          rebuildScratchPreservingSelection(next);
                        } catch (err: any) {
                          setImportState({ error: err?.message || String(err) });
                        }
                      }}
                      onClick={(e) => e.stopPropagation()}
                      disabled={importState.busyStage !== "idle"}
                      placeholder="bars"
                    />
                    <button
                      type="button"
                      className="col-span-2 px-2 py-1 rounded bg-slate-900 text-slate-200 text-[11px] border border-slate-700 hover:border-slate-500"
                      onClick={(e) => {
                        e.stopPropagation();
                        const next = (scratchArrangement || []).slice();
                        next.splice(idx, 1);
                        const rows = next.length ? next : [{ label: "section", bars: 8 }];
                        setScratchArrangement(rows);
                        try {
                          rebuildScratchPreservingSelection(rows);
                        } catch (err: any) {
                          setImportState({ error: err?.message || String(err) });
                        }
                      }}
                      disabled={importState.busyStage !== "idle"}
                    >
                      Remove
                    </button>
                    <div className="col-span-12 px-1 pb-1 text-[10px] text-slate-500">
                      {barInfo ? `Bars: ${barInfo.startBar + 1}-${barInfo.endBar + 1}` : "Bars: (build to compute)"}
                    </div>
                  </div>
                  );
                })}

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="px-3 py-1.5 rounded bg-slate-900 text-slate-200 text-xs border border-slate-700 hover:border-slate-500"
                    onClick={() => {
                      const next = [...(scratchArrangement || []), { label: "section", bars: 8 }];
                      setScratchArrangement(next);
                      try {
                        rebuildScratchPreservingSelection(next);
                      } catch (err: any) {
                        setImportState({ error: err?.message || String(err) });
                      }
                    }}
                    disabled={importState.busyStage !== "idle"}
                  >
                    Add row
                  </button>
                  <div className="text-[11px] text-slate-500">
                    Total rows: {(scratchArrangement || []).length}
                  </div>
                </div>
              </div>
            </div>
          ) : null}

          {workflowMode === "scratch" && arrangement.sections.length ? (
            <div className="mb-2 rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="text-[11px] text-slate-400">Arrangement (bars)</div>
              {(() => {
                const beatsPerBar = arrangement.timeSig?.[0] || 4;
                const fallbackBpm = arrangement.tempoMap?.[0]?.bpm || 120;
                const regions = (arrangement.sections || []).map((s, idx) =>
                  barRangeForSection({
                    section: s,
                    idx,
                    beatsPerBar,
                    beatTimes: arrangement.beatTimes,
                    tempoMap: arrangement.tempoMap,
                    fallbackBpm,
                  })
                );
                const totalBarsFromBeatTimes = Array.isArray(arrangement.beatTimes)
                  ? Math.max(0, Math.floor((arrangement.beatTimes.length - 1) / Math.max(1, beatsPerBar)))
                  : 0;
                const totalBarsFromRegions = regions.reduce((mx, r) => Math.max(mx, r.endBar + 1), 0);
                const totalBars = Math.max(1, totalBarsFromBeatTimes, totalBarsFromRegions);

                return (
                  <>
                    <div ref={scratchStripRef} className="mt-2 relative h-10 rounded bg-slate-900 overflow-hidden">
                      {regions.map((r) => {
                        const left = clamp01(r.startBar / totalBars);
                        const right = clamp01((r.endBar + 1) / totalBars);
                        const w = Math.max(0, right - left);
                        if (w <= 0) return null;
                        const selected = selectedSectionId === r.id;
                        return (
                          <button
                            key={r.id}
                            type="button"
                            className={
                              "absolute top-0 bottom-0 rounded-sm border text-left " +
                              (selected
                                ? "border-amber-400/60 bg-amber-500/15"
                                : "border-cyan-400/30 bg-cyan-500/15 hover:border-cyan-300/60")
                            }
                            style={{ left: `${(left * 100).toFixed(3)}%`, width: `${(w * 100).toFixed(3)}%` }}
                            title={`${r.label}: bars ${r.startBar + 1}-${r.endBar + 1}`}
                            onClick={() => setSelectedSectionId(r.id)}
                            disabled={importState.busyStage !== "idle"}
                          >
                            <div className="px-1 h-full flex items-center text-[10px] text-cyan-200/90 truncate">
                              {r.label}
                            </div>
                          </button>
                        );
                      })}

                      {regions.slice(0, -1).map((r, idx) => {
                        const boundaryBar = r.endBar + 1;
                        const x = clamp01(boundaryBar / totalBars);
                        const active = scratchDrag?.boundaryIdx === idx;
                        return (
                          <div
                            key={`divider-${idx}`}
                            className={
                              "absolute top-0 bottom-0 w-1 cursor-col-resize " +
                              (active ? "bg-amber-300/60" : "bg-slate-300/20 hover:bg-slate-200/50")
                            }
                            style={{ left: `${(x * 100).toFixed(3)}%`, transform: "translateX(-50%)" }}
                            onPointerDown={(e) => {
                              if (importState.busyStage !== "idle") return;
                              const el = scratchStripRef.current;
                              if (!el) return;
                              const rect = el.getBoundingClientRect();
                              const startBars = (scratchArrangement || []).map((row) => Math.max(1, Math.floor(Number((row as any)?.bars ?? 1))));
                              setScratchDrag({
                                boundaryIdx: idx,
                                left: rect.left,
                                width: Math.max(1, rect.width),
                                totalBars,
                                boundaryBar,
                                startBars,
                              });
                              try {
                                (e.currentTarget as any).setPointerCapture?.(e.pointerId);
                              } catch {
                                // ignore
                              }
                              e.preventDefault();
                              e.stopPropagation();
                            }}
                          />
                        );
                      })}

                      {scratchDrag ? (
                        <div className="absolute top-0 right-2 h-full flex items-center text-[10px] text-slate-200/90 bg-slate-950/60 px-2 rounded">
                          Resize: {scratchDrag.startBars[scratchDrag.boundaryIdx]} | {scratchDrag.startBars[scratchDrag.boundaryIdx + 1]}
                        </div>
                      ) : null}
                    </div>
                    <div className="mt-1 text-[11px] text-slate-500">{regions.length} sections • {totalBars} bars</div>
                  </>
                );
              })()}
            </div>
          ) : null}

          {importState.waveform?.duration && arrangement.sections.length ? (
            <div className="mb-2 rounded-lg border border-slate-800 bg-slate-950 p-2">
              <div className="text-[11px] text-slate-400">Arrangement (sections)</div>
              <div className="mt-2 relative h-8 rounded bg-slate-900 overflow-hidden">
                {arrangement.sections.map((s, idx) => {
                  const dur = Number(importState.waveform?.duration || 0);
                  const left = dur > 0 ? clamp01((Number(s.startSec) || 0) / dur) : 0;
                  const right = dur > 0 ? clamp01((Number(s.endSec) || 0) / dur) : 0;
                  const w = Math.max(0, right - left);
                  if (w <= 0) return null;
                  return (
                    <div
                      key={`${s.label}-${idx}`}
                      className="absolute top-0 bottom-0 rounded-sm border border-cyan-400/30 bg-cyan-500/15"
                      style={{ left: `${(left * 100).toFixed(3)}%`, width: `${(w * 100).toFixed(3)}%` }}
                      title={`${s.label}: ${s.startSec.toFixed(2)}s - ${s.endSec.toFixed(2)}s`}
                    >
                      <div className="px-1 h-full flex items-center text-[10px] text-cyan-200/90 truncate">
                        {s.label || `Section ${idx + 1}`}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="mt-1 text-[11px] text-slate-500">{arrangement.sections.length} sections • duration {importState.waveform.duration.toFixed(2)}s</div>
            </div>
          ) : null}
          {displayedPeaks?.length ? (
            <WaveformView
              peaks={displayedPeaks}
              peaksL={useNormalized ? (importState.waveform?.peaksL ? normalizePeaks(importState.waveform.peaksL) : undefined) : importState.waveform?.peaksL}
              peaksR={useNormalized ? (importState.waveform?.peaksR ? normalizePeaks(importState.waveform.peaksR) : undefined) : importState.waveform?.peaksR}
              durationSec={importState.waveform?.duration}
            />
          ) : (
            <div className="rounded-lg border border-dashed border-slate-800 bg-slate-950 p-6 text-[11px] text-slate-500">
              {workflowMode === "audio" ? "Load audio to view waveform." : "New Track Creation: no waveform."}
            </div>
          )}
        </div>
      </div>

      {grooveModalOpen && (
        <div className="fixed inset-0 z-[70]">
          <div className="absolute inset-0 bg-black/60" onClick={() => setGrooveModalOpen(false)} role="presentation" />
          <div className="absolute inset-0 flex items-center justify-center p-4">
            <div className="w-full max-w-2xl max-h-[90vh] overflow-hidden rounded-lg border border-indigo-700/40 bg-slate-900 shadow-2xl flex flex-col">
              <div className="flex items-center justify-between px-4 py-3 border-b border-indigo-700/30 bg-indigo-900/10">
                <div>
                  <div className="text-sm font-semibold text-slate-100">Basic Drum Style</div>
                  <div className="text-xs text-slate-400">Choose a basic drum style for generation.</div>
                </div>
                <button className="text-slate-400 hover:text-slate-100" onClick={() => setGrooveModalOpen(false)} type="button">
                  ✕
                </button>
              </div>

              <div className="p-4 space-y-3 overflow-auto flex-1">
                <input
                  value={grooveQuery}
                  onChange={(e) => setGrooveQuery(e.target.value)}
                  placeholder="Search grooves (e.g. four on the floor, bonham, paradiddle)"
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white"
                />

                <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
                  <span className="text-slate-400">Source</span>
                  <select
                    className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                    value={grooveSourceMode}
                    onChange={(e) => {
                      const next = String(e.target.value || "egmd") as any;
                      setGrooveSourceMode(next);
                      setEgmdStyleGroup("");
                      void searchGrooves(grooveQuery, grooveTag, "");
                    }}
                  >
                    <option value="egmd">EGMD</option>
                    <option value="dtk_standard">DTK Standard</option>
                  </select>
                </label>

                {String(grooveSourceMode || "egmd").trim().toLowerCase() === "egmd" ? (
                  <div className="rounded border border-slate-800 bg-slate-950/40 p-2 space-y-2">
                    <div className="grid grid-cols-2 gap-2 items-center">
                      <div className="text-[11px] text-slate-300">Groove feel</div>
                      <select
                        className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                        value={egmdFeelPreset}
                        onChange={(e) => setEgmdFeelPreset(e.target.value as any)}
                      >
                        <option value="straight_backbeat">Straight backbeat</option>
                        <option value="four_on_floor">Four on the floor</option>
                        <option value="half_time_sparse">Half-time / sparse</option>
                        <option value="syncopated">Syncopated</option>
                        <option value="busy">Busier grooves</option>
                        <option value="any">Any</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-2 items-center">
                      <div className="text-[11px] text-slate-300">Complexity</div>
                      <select
                        className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                        value={egmdComplexityTier}
                        onChange={(e) => setEgmdComplexityTier(e.target.value as any)}
                      >
                        <option value="simple">Simple</option>
                        <option value="intermediate">Intermediate</option>
                        <option value="complex">Complex</option>
                      </select>
                    </div>
                  </div>
                ) : null}

                <div>
                  <div className="text-[11px] text-slate-400">Style</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button
                      key="__all__"
                      type="button"
                      disabled={false}
                      className={`text-xs px-2 py-1 rounded border ${
                        !egmdStyleGroup
                          ? "bg-emerald-600 border-emerald-500 text-white"
                          : "bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"
                      }`}
                      onClick={() => {
                        setEgmdStyleGroup("");
                        void searchGrooves(grooveQuery, grooveTag, "");
                      }}
                    >
                      All
                    </button>
                    {!egmdStyleOptions.length ? (
                      <div className="text-[11px] text-slate-500 px-2 py-1">Loading styles…</div>
                    ) : null}
                    {egmdStyleOptions.map((sg) => (
                      <button
                        key={sg}
                        type="button"
                        disabled={false}
                        className={`text-xs px-2 py-1 rounded border ${
                          egmdStyleGroup === sg
                            ? "bg-emerald-600 border-emerald-500 text-white"
                            : "bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"
                        }`}
                        onClick={() => {
                          const next = egmdStyleGroup === sg ? "" : String(sg || "");
                          setEgmdStyleGroup(next);
                          void searchGrooves(grooveQuery, grooveTag, next);
                        }}
                      >
                        {sg}
                      </button>
                    ))}
                  </div>
                </div>

                <label className="flex items-center gap-2 text-[11px] text-slate-300 select-none">
                  <input
                    type="checkbox"
                    checked={requireTagMatch}
                    onChange={(e) => setRequireTagMatch(e.target.checked)}
                  />
                  Require tag match
                  <span className="text-slate-500">
                    ({grooveTag ? `tag: ${grooveTag}` : "no tag selected"})
                  </span>
                </label>

                <div className="flex items-center gap-2">
                  <div className="text-[11px] text-slate-400">Tag</div>
                  <input
                    value={grooveTag}
                    onChange={(e) => setGrooveTag(e.target.value)}
                    placeholder="optional tag (e.g. shuffle)"
                    className="flex-1 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="px-3 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold disabled:opacity-50"
                    disabled={grooveLoading}
                    onClick={() => void searchGrooves(grooveQuery, grooveTag, egmdStyleGroup)}
                  >
                    {grooveLoading ? "Searching…" : "Search"}
                  </button>

                  <button
                    type="button"
                    className="ml-auto text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700"
                    onClick={() => {
                      setGrooveQuery("");
                      setGrooveTag("");
                      setGrooveResults([]);
                    }}
                  >
                    Clear
                  </button>
                </div>

                <div className="text-[11px] text-slate-500">
                  {grooveLoading
                    ? "Searching…"
                    : grooveResults.length
                      ? `${filteredGrooveResults.length} / ${grooveResults.length} result${grooveResults.length === 1 ? "" : "s"}`
                      : "No results yet. Click Search."}
                </div>

                {egmdStyleFallbackActive ? (
                  <div className="text-[11px] text-amber-300/90">
                    No matches for style <span className="font-semibold">{String(egmdStyleGroup || "(none)")}</span>; showing all EGMD results.
                  </div>
                ) : null}

                {grooveResults.length > 0 && filteredGrooveResults.length === 0 && !egmdStyleFallbackActive ? (
                  <div className="text-[11px] text-amber-300/90">
                    Filters hid all matches; showing all returned results.
                  </div>
                ) : null}

                <div className="text-[10px] text-slate-600 space-y-0.5">
                  {grooveLastRequest ? <div>Last request: {grooveLastRequest}</div> : null}
                  {typeof grooveLastCount === "number" ? <div>Last response items: {grooveLastCount}</div> : null}
                  {grooveLastError ? <div className="text-rose-400">Last error: {grooveLastError}</div> : null}
                </div>

              {displayedGrooveResults.length > 0 ? (
                <div className="mt-3 space-y-2 pr-1">
                  {displayedGrooveResults.map((item) => {
                    const id = String(item?.id || "");
                    if (!id) return null;
                    const title = String(item?.title || "");
                    const source = String(item?.source || "unknown");
                    const srcLower = source.trim().toLowerCase();
                    const isEgmd = srcLower === "egmd";
                    const sourceLabel = isEgmd ? "EGMD" : (srcLower === "dtk_standard" ? "DTK" : source);
                    const tags = Array.isArray(item?.tags) ? item.tags : [];
                    const t = String(grooveTag || "").trim().toLowerCase();
                    const tagMatch = !!t && tags.map((x: any) => String(x || "").toLowerCase()).includes(t);
                    const hasAudio = !!item?.has_audio;
                    const isPlaying = playingGrooveId === id;
                    const isGrooveSelected = String(globalDefaults.selectedGrooveId || "") === id;
                    const isFillSelected = String(globalDefaults.fillGrooveId || "") === id;
                    const cs = Number((item as any)?.complexity_score);
                    const phraseId = (item as any)?.phrase_id ?? (item as any)?.egmd_phrase_id ?? (item as any)?.phraseId;
                    const styleGroup = String((item as any)?.style_group || "").trim();

                    return (
                      <div key={id} className="bg-slate-800/60 border border-slate-700 rounded p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-slate-100 truncate">{title || id}</div>
                            <div className="text-[11px] text-slate-500">
                              {sourceLabel}
                              {isEgmd && Number.isFinite(cs) ? ` • cx ${cs.toFixed(2)}` : ""}
                            </div>

                            {isEgmd && (styleGroup || phraseId != null) ? (
                              <div className="text-[11px] text-slate-500">
                                {styleGroup ? `style: ${styleGroup}` : ""}
                                {styleGroup && phraseId != null ? " · " : ""}
                                {phraseId != null ? `phrase: ${String(phraseId)}` : ""}
                              </div>
                            ) : null}

                            <div className="mt-1 flex items-center gap-2 text-[11px]">
                              {t ? (
                                <span
                                  className={
                                    "px-1.5 py-0.5 rounded border " +
                                    (tagMatch
                                      ? "bg-emerald-600/20 border-emerald-500/40 text-emerald-100"
                                      : "bg-slate-900 border-slate-700 text-slate-400")
                                  }
                                >
                                  {tagMatch ? "tag match" : "no tag match"}
                                </span>
                              ) : null}
                              <span
                                className={
                                  "px-1.5 py-0.5 rounded border " +
                                  (hasAudio
                                    ? "bg-indigo-600/20 border-indigo-500/40 text-indigo-100"
                                    : "bg-slate-900 border-slate-700 text-slate-400")
                                }
                              >
                                {hasAudio ? "audio" : "no audio"}
                              </span>
                            </div>

                            {(item?.tempo_bpm || item?.meter || item?.bars) && (
                              <div className="text-[11px] text-slate-500">
                                {item?.tempo_bpm ? `${Math.round(Number(item.tempo_bpm))} BPM` : ""}
                                {item?.meter ? ` · ${String(item.meter)}` : ""}
                                {item?.bars ? ` · ${String(item.bars)} bars` : ""}
                              </div>
                            )}

                            <div className="mt-1 flex flex-wrap gap-1">
                              {(tags || []).slice(0, 10).map((tag: string) => (
                                <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-200">
                                  {tag}
                                </span>
                              ))}
                            </div>
                          </div>

                          <div className="flex flex-col gap-2 shrink-0">
                            <button
                              type="button"
                              className={
                                "text-xs px-2 py-1 rounded border " +
                                (isPlaying
                                  ? "bg-amber-600/20 border-amber-500/40 text-amber-100"
                                  : "bg-slate-900 border-slate-700 text-slate-200 hover:bg-slate-800")
                              }
                              title={hasAudio ? "Play preview" : "Try preview (audio may be unavailable)"}
                              onClick={() => void toggleGrooveAudio(id)}
                            >
                              {isPlaying ? "Stop" : "Play"}
                            </button>

                            <button
                              type="button"
                              className={
                                "text-xs px-2 py-1 rounded border " +
                                (isGrooveSelected
                                  ? "bg-emerald-600 border-emerald-500 text-white"
                                  : "bg-slate-900 border-slate-700 text-slate-200 hover:bg-slate-800")
                              }
                              onClick={() => {
                                setGlobalDefaults({
                                  selectedGrooveId: id,
                                  grooveUse: "use_as_groove",
                                  grooveSource: isEgmd ? "egmd_phrases" : (srcLower || undefined),
                                  grooveMode: isEgmd ? "exact" : undefined,
                                  styleGroup: item?.style_group ? String(item.style_group) : undefined,
                                  egmdPhraseId: isEgmd && item?.phrase_id != null ? Number(item.phrase_id) : undefined,
                                  egmdMidiPath: isEgmd && (item as any)?.midi_path ? String((item as any).midi_path) : undefined,
                                });
                                setScratchNeedsGenerate(true);
                              }}
                              disabled={importState.busyStage !== "idle"}
                            >
                              {isGrooveSelected ? "Selected" : "Use as groove"}
                            </button>

                            <button
                              type="button"
                              className={
                                "text-xs px-2 py-1 rounded border " +
                                (isFillSelected ? "bg-rose-600 border-rose-500 text-white" : "bg-rose-700/80 border-rose-600 text-white hover:bg-rose-600")
                              }
                              onClick={() => {
                                setGlobalDefaults({
                                  fillGrooveId: id,
                                  grooveUse: "use_as_fill",
                                  grooveSource: isEgmd ? "egmd_phrases" : (srcLower || undefined),
                                  grooveMode: isEgmd ? "exact" : undefined,
                                  styleGroup: item?.style_group ? String(item.style_group) : undefined,
                                  egmdPhraseId: isEgmd && item?.phrase_id != null ? Number(item.phrase_id) : undefined,
                                  egmdFillMidiPath: isEgmd && (item as any)?.midi_path ? String((item as any).midi_path) : undefined,
                                });
                                setScratchNeedsGenerate(true);
                              }}
                              disabled={importState.busyStage !== "idle"}
                            >
                              {isFillSelected ? "Selected" : "Use as fill"}
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : null}

              </div>

              <div className="flex items-center justify-end p-3 border-t border-slate-700 bg-slate-800 shrink-0">
                <button
                  type="button"
                  className="px-3 py-2 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 text-sm"
                  onClick={() => {
                    setGlobalDefaults({
                      selectedGrooveId: undefined,
                      fillGrooveId: undefined,
                      grooveSource: undefined,
                      grooveMode: undefined,
                      styleGroup: undefined,
                      egmdPhraseId: undefined,
                      egmdMidiPath: undefined,
                      egmdFillMidiPath: undefined,
                    });
                    setScratchNeedsGenerate(true);
                    setGrooveModalOpen(false);
                  }}
                >
                  Clear selection
                </button>

                <button
                  type="button"
                  className="ml-auto px-3 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold"
                  onClick={() => setGrooveModalOpen(false)}
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
