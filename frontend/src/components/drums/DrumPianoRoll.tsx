// frontend/src/components/drums/DrumPianoRoll.tsx

import React, { useMemo, useCallback, useEffect, useState, useRef } from "react";
import {
  DrumTrackForDCSM,
  DrumNoteEvent,
  NoteAspect,
  DrumInstrumentId,
} from "../../types/drumTrack";
import type { DrumPlayerChannelId, DrumPlayerEngine } from "../../audio/drumPlayerEngine";
import { getMidiPitchForInstrument } from "../../utils/drumTrackUtils";
import {
  GridResolution,
  getSubdivisionsPerBar,
  getTicksPerSubdivision,
} from "../../utils/pianoRollGrid";
import { GrooveWeightMap } from "../../types/grooveWeight";
import { LIMB_CONFIG, inferLimbFromInstrument, type LimbId } from "../../constants/limbs";
import { BAR_GRID_THEME } from "../../constants/barGrid";
import { getInstrumentForMidiPitch } from "../../utils/drumTrackUtils";
import { Tooltip } from "../Tooltip";

const SUPPORTED_LIMBS: readonly LimbId[] = ["RH", "LH", "RF", "LF"];

export type DrumSectionRegion = {
  id: string;
  label: string;
  startBar: number;
  endBar: number;
  color?: string;
};

interface DrumPianoRollProps {
  drumTrack: DrumTrackForDCSM | null;
  timeSignature: [number, number];
  bpm?: number;
  tempoMap?: Array<{ tSec: number; bpm: number }>;
  beatTimes?: number[];
  playheadSeconds?: number;
  playing?: boolean;
  gridResolution: GridResolution;
  currentAspect: NoteAspect | "all";
  grooveWeights?: GrooveWeightMap;
  onNoteChange?: (notes: DrumNoteEvent[]) => void;
  onNoteSelect?: (noteIds: string[]) => void;
  selectedNoteIds?: string[];
  selectedBarIndex?: number | null;
  onBarSelect?: (barIndex: number | null) => void;
  barDirectives?: Record<number, { forceFill?: boolean; suppressFill?: boolean }>;
  scrollContainerRef?: React.RefObject<HTMLDivElement>;
  pixelsPerBeat: number;
  visibleStartMeasure?: number;
  visibleMeasureCount?: number;
  totalSongBars?: number;
  drumEngine?: DrumPlayerEngine | null;
  sectionRegions?: DrumSectionRegion[];
  selectedSectionIds?: Set<string> | string[];
  onSectionSelect?: (sectionId: string) => void;
  compact?: boolean;
}

function getSectionOverlayColor(label?: string | null): string {
  const v = (label || "").toLowerCase();
  if (v.includes("verse")) return "#3b82f6";
  if (v.includes("chorus")) return "#22c55e";
  if (v.includes("bridge")) return "#a855f7";
  if (v.includes("intro")) return "#f97316";
  if (v.includes("outro")) return "#ef4444";
  return "#64748b";
}

function mapInstrumentToChannel(instId: DrumInstrumentId): DrumPlayerChannelId | null {
  switch (instId) {
    case "kick":
      return "kick";
    case "snare_center":
    case "snare_ghost":
    case "snare_rim":
      return "snare_top";
    case "hihat_closed":
    case "hihat_open":
    case "hihat_pedal":
      return "hat";
    case "ride_bow":
    case "ride_bell":
    case "ride_edge":
      return "ride";
    case "tom_high":
      return "tom1";
    case "tom_mid":
      return "tom3";
    case "tom_floor":
      return "tom5";
    case "crash_1":
    case "crash_2":
      return "crash";
    default:
      return null;
  }
}

function auditionInstrument(args: { drumEngine?: DrumPlayerEngine | null; instrumentId: DrumInstrumentId; velocity?: number }) {
  const { drumEngine, instrumentId, velocity } = args;
  if (!drumEngine) return;
  const ch = mapInstrumentToChannel(instrumentId);
  if (!ch) return;
  const ctx = drumEngine.audioContext;
  const whenSec = ctx ? ctx.currentTime + 0.01 : undefined;
  drumEngine.playChannelOneShot(ch, {
    whenSec,
    gain: Math.max(0.2, Math.min(1.5, (Number(velocity ?? 100) || 100) / 100)),
  });
}

const instrumentOrder: DrumInstrumentId[] = [
  "kick",
  "snare_center",
  "snare_ghost",
  "snare_rim",
  "hihat_closed",
  "hihat_open",
  "hihat_pedal",
  "ride_bow",
  "ride_bell",
  "ride_edge",
  "tom_high",
  "tom_mid",
  "tom_floor",
  "crash_1",
  "crash_2",
];

const limbLaneOrder: readonly LimbId[] = ["RH", "LH", "RF", "LF"] as const;

const DEFAULT_LIMB_INSTRUMENT: Record<(typeof limbLaneOrder)[number], DrumInstrumentId> = {
  RH: "hihat_closed",
  LH: "snare_center",
  RF: "kick",
  LF: "hihat_pedal",
};

const inferLimbFromMidiPitch = (pitch?: number | null): LimbId | null => {
  if (typeof pitch !== "number" || !Number.isFinite(pitch)) {
    return null;
  }
  const p = Math.round(pitch);
  // Common GM drum pitches
  if (p === 36 || p === 35) return "RF"; // kick
  if (p === 38 || p === 40 || p === 37) return "LH"; // snare / rim
  if (p === 44) return "LF"; // pedal hat
  if (p === 42 || p === 46 || p === 45) return "RH"; // hats
  if (p === 49 || p === 57 || p === 51 || p === 59 || p === 55 || p === 52) return "RH"; // cymbals
  if (p === 41 || p === 43 || p === 47 || p === 48 || p === 50) return "LH"; // toms
  return null;
};

const ACCENT_BY_INSTRUMENT: Partial<Record<DrumInstrumentId, string>> = {
  kick: "#22c55e",
  snare_center: "#f97316",
  snare_ghost: "#f97316",
  snare_rim: "#f97316",
  hihat_closed: "#eab308",
  hihat_open: "#eab308",
  hihat_pedal: "#eab308",
  ride_bow: "#22d3ee",
  ride_bell: "#22d3ee",
  ride_edge: "#22d3ee",
  tom_high: "#a855f7",
  tom_mid: "#a855f7",
  tom_floor: "#a855f7",
  crash_1: "#ec4899",
  crash_2: "#ec4899",
};

const getIconUrlForInstrument = (instrumentId: DrumInstrumentId): string | null => {
  const base = "/drum-icons";
  if (instrumentId === "kick") return `${base}/kick.png`;

  if (
    instrumentId === "snare_center" ||
    instrumentId === "snare_ghost" ||
    instrumentId === "snare_rim"
  ) {
    return `${base}/snare.png`;
  }

  if (instrumentId === "ride_bow" || instrumentId === "ride_bell" || instrumentId === "ride_edge") {
    return `${base}/ride.png`;
  }

  if (instrumentId === "crash_1" || instrumentId === "crash_2") {
    return `${base}/crash.png`;
  }

  if (instrumentId === "tom_high") return `${base}/rack_tom_small.png`;
  if (instrumentId === "tom_mid") return `${base}/rack_tom_medium.png`;
  if (instrumentId === "tom_floor") return `${base}/floor_tom.png`;

  if (instrumentId === "hihat_pedal") return `${base}/hihat_pedal.png`;
  if (instrumentId === "hihat_closed" || instrumentId === "hihat_open") {
    // Inline SVG so we don't depend on a missing public asset.
    const svg =
      instrumentId === "hihat_open"
        ? `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><g fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M8 18c9 6 39 6 48 0"/><path d="M12 10c7 4 33 4 40 0"/><path d="M32 18v36"/><path d="M20 54h24"/><path d="M26 54v-4h12v4"/></g></svg>`
        : `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><g fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M8 16c9 6 39 6 48 0"/><path d="M12 12c7 4 33 4 40 0"/><path d="M32 16v38"/><path d="M20 54h24"/><path d="M26 54v-4h12v4"/><path d="M18 22h28"/></g></svg>`;
    return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
  }

  return null;
};

export const DrumPianoRoll: React.FC<DrumPianoRollProps> = ({
  drumTrack,
  timeSignature,
  bpm,
  tempoMap,
  beatTimes,
  playheadSeconds,
  playing,
  gridResolution,
  currentAspect,
  grooveWeights,
  onNoteChange,
  onNoteSelect,
  selectedNoteIds,
  selectedBarIndex,
  onBarSelect,
  barDirectives,
  scrollContainerRef,
  pixelsPerBeat,
  visibleStartMeasure,
  visibleMeasureCount,
  totalSongBars,
  drumEngine,
  sectionRegions,
  selectedSectionIds,
  onSectionSelect,
  compact,
}) => {
  const hasDrumTrack = Boolean(drumTrack);

  const headerScrollRef = useRef<HTMLDivElement | null>(null);
  const laneScrollRef = useRef<HTMLDivElement | null>(null);
  const laneYScrollRef = useRef<HTMLDivElement | null>(null);
  const labelColRef = useRef<HTMLDivElement | null>(null);
  const gridInnerRef = useRef<HTMLDivElement | null>(null);

  const [laneChannelState, setLaneChannelState] = useState<
    Record<string, { mute: boolean; solo: boolean }>
  >({});

  const [limbInstrumentByLimb, setLimbInstrumentByLimb] = useState<Record<LimbId, DrumInstrumentId>>(
    () => ({ ...DEFAULT_LIMB_INSTRUMENT } as Record<LimbId, DrumInstrumentId>),
  );

  const [limbWarning, setLimbWarning] = useState<{
    title: string;
    message: string;
    pending: { limb: LimbId; barIndex: number; tickInBar: number; instrumentId: DrumInstrumentId } | null;
  } | null>(null);

  useEffect(() => {
    if (!drumEngine) {
      setLaneChannelState({});
      return;
    }

    const update = () => {
      try {
        const next: Record<string, { mute: boolean; solo: boolean }> = {};
        for (const instId of instrumentOrder) {
          const channelId = mapInstrumentToChannel(instId);
          if (!channelId) continue;
          const p = drumEngine.getChannelParams(channelId);
          next[instId] = { mute: Boolean(p.mute), solo: Boolean(p.solo) };
        }
        setLaneChannelState(next);
      } catch {
        setLaneChannelState({});
      }
    };

    update();
    const interval = window.setInterval(update, 200);
    return () => window.clearInterval(interval);
  }, [drumEngine]);

  const resolution_ppq = drumTrack?.resolution_ppq ?? 960;
  const notes = drumTrack?.notes ?? [];
  const drumTrackId = drumTrack?.track_id ?? null;

  const trackBarCount = useMemo(
    () => (notes.length ? 1 + Math.max(...notes.map((n) => n.barIndex ?? 0)) : 0),
    [notes]
  );

  const subdivisionsPerBar = getSubdivisionsPerBar(gridResolution);
  const ticksPerSubdivision = getTicksPerSubdivision(
    resolution_ppq,
    timeSignature,
    gridResolution
  );
  const beatsPerBar = timeSignature[0];
  const ticksPerBar = resolution_ppq * beatsPerBar;
  const barWidthPx = pixelsPerBeat * beatsPerBar;

  const subdivisionsPerBeat = useMemo(() => {
    const denom = Math.max(1, beatsPerBar);
    const v = subdivisionsPerBar / denom;
    if (!Number.isFinite(v)) return 1;
    return Math.max(1, Math.round(v));
  }, [beatsPerBar, subdivisionsPerBar]);

  const subdivisionLabelForIndex = useCallback(
    (subIndexWithinBeat: number): string | null => {
      if (subIndexWithinBeat <= 0) return null;
      if (subdivisionsPerBeat === 4) {
        if (subIndexWithinBeat === 1) return "e";
        if (subIndexWithinBeat === 2) return "&";
        if (subIndexWithinBeat === 3) return "a";
        return null;
      }
      if (subdivisionsPerBeat === 2) {
        if (subIndexWithinBeat === 1) return "&";
        return null;
      }
      return null;
    },
    [subdivisionsPerBeat],
  );

  const [scrollLeft, setScrollLeft] = useState(0);

  const totalBarsSpan = totalSongBars ?? Math.max(trackBarCount || 1, 1);
  const totalWidth = Math.max(1, totalBarsSpan * barWidthPx);

  const selectedSectionIdSet = useMemo(() => {
    if (!selectedSectionIds) return new Set<string>();
    if (Array.isArray(selectedSectionIds)) {
      return new Set(selectedSectionIds.map((v) => String(v)));
    }
    return new Set(Array.from(selectedSectionIds).map((v) => String(v)));
  }, [selectedSectionIds]);

  const normalizedSectionRegions = useMemo(() => {
    const regions = Array.isArray(sectionRegions) ? sectionRegions : [];
    return regions
      .map((r) => {
        const startBar = Math.max(0, Math.min(totalBarsSpan - 1, Math.floor(r.startBar ?? 0)));
        const endBar = Math.max(startBar, Math.min(totalBarsSpan - 1, Math.floor(r.endBar ?? startBar)));
        const label = (r.label || "Section").toString();
        const color = (r.color || getSectionOverlayColor(label)).toString();
        return {
          id: (r.id || `${label}-${startBar}-${endBar}`).toString(),
          label,
          startBar,
          endBar,
          color,
        };
      })
      .filter((r) => Number.isFinite(r.startBar) && Number.isFinite(r.endBar) && r.endBar >= r.startBar);
  }, [sectionRegions, totalBarsSpan]);

  const beatsAtTimeFromBeatTimes = useCallback(
    (tSec: number): number | null => {
      const bt = Array.isArray(beatTimes) ? beatTimes : null;
      if (!bt || bt.length < 2) return null;

      const t = Math.max(0, Number.isFinite(tSec) ? tSec : 0);
      if (t <= bt[0]) return 0;

      // Find first index i with bt[i] >= t.
      // Linear scan is OK for now; we can binary search later if needed.
      let i = 1;
      for (; i < bt.length; i++) {
        const ti = bt[i];
        if (!Number.isFinite(ti)) continue;
        if (t <= ti) break;
      }

      if (i >= bt.length) {
        const last = bt[bt.length - 1];
        const prev = bt[bt.length - 2];
        if (!Number.isFinite(last) || !Number.isFinite(prev) || last <= prev) return bt.length - 1;
        const secPerBeat = last - prev;
        const extra = (t - last) / Math.max(1e-6, secPerBeat);
        return (bt.length - 1) + Math.max(0, extra);
      }

      const t0 = bt[i - 1];
      const t1 = bt[i];
      if (!Number.isFinite(t0) || !Number.isFinite(t1) || t1 <= t0) {
        return i - 1;
      }
      const alpha = (t - t0) / (t1 - t0);
      return (i - 1) + Math.max(0, Math.min(1, alpha));
    },
    [beatTimes],
  );

  const playheadX = useMemo(() => {
    const playSec = typeof playheadSeconds === "number" && Number.isFinite(playheadSeconds) ? playheadSeconds : null;
    if (playSec === null) return null;

    const beatsFromGrid = beatsAtTimeFromBeatTimes(playSec);
    if (beatsFromGrid !== null) {
      if (!Number.isFinite(beatsFromGrid) || beatsFromGrid < 0) return null;
      return beatsFromGrid * pixelsPerBeat;
    }

    const pts = Array.isArray(tempoMap)
      ? tempoMap
          .map((p) => ({ tSec: Number((p as any)?.tSec) || 0, bpm: Number((p as any)?.bpm) || 0 }))
          .filter((p) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
          .sort((a, b) => a.tSec - b.tSec)
      : [];

    const fallbackTempo = typeof bpm === "number" && Number.isFinite(bpm) && bpm > 0 ? bpm : null;
    if (!pts.length && fallbackTempo === null) return null;

    const beatsAtTime = (t: number): number => {
      if (!pts.length) {
        return (t * (fallbackTempo as number)) / 60;
      }
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
    };

    const beats = beatsAtTime(playSec);
    if (!Number.isFinite(beats) || beats < 0) return null;
    return beats * pixelsPerBeat;
  }, [beatsAtTimeFromBeatTimes, bpm, pixelsPerBeat, playheadSeconds, tempoMap]);

  const clampedPlayheadX = useMemo(() => {
    if (playheadX === null) return null;
    const maxX = Math.max(0, totalWidth - 2);
    return Math.max(0, Math.min(maxX, playheadX));
  }, [playheadX, totalWidth]);

  const lastAutoScrollMsRef = useRef<number>(0);

  useEffect(() => {
    if (!playing) return;
    if (clampedPlayheadX === null) return;
    const laneEl = laneScrollRef.current;
    if (!laneEl) return;

    const viewLeft = laneEl.scrollLeft;
    const viewRight = viewLeft + laneEl.clientWidth;
    const margin = Math.max(32, laneEl.clientWidth * 0.2);

    if (clampedPlayheadX < viewLeft + margin || clampedPlayheadX > viewRight - margin) {
      const target = Math.max(0, clampedPlayheadX - laneEl.clientWidth * 0.35);
      const now = performance.now();
      const delta = Math.abs(laneEl.scrollLeft - target);
      if (delta < 8) return;
      if (now - lastAutoScrollMsRef.current < 150) return;
      lastAutoScrollMsRef.current = now;
      try {
        laneEl.scrollTo({ left: target, behavior: "smooth" });
      } catch {
        laneEl.scrollLeft = target;
      }
    }
  }, [clampedPlayheadX, playing]);

  const fallbackStartBar = Math.max(0, visibleStartMeasure ?? 0);
  const viewStartBar = useMemo(() => {
    const derived = barWidthPx > 0 ? Math.floor(scrollLeft / barWidthPx) : 0;
    return Math.max(0, Number.isFinite(derived) ? derived : fallbackStartBar);
  }, [barWidthPx, fallbackStartBar, scrollLeft]);

  const viewBarCount = useMemo(() => {
    const viewportPx = laneScrollRef.current?.clientWidth ?? 0;
    if (!Number.isFinite(viewportPx) || viewportPx <= 0 || !Number.isFinite(barWidthPx) || barWidthPx <= 0) {
      const available = Math.max(1, trackBarCount - fallbackStartBar);
      return Math.max(1, visibleMeasureCount ?? available);
    }
    const barsInView = Math.ceil(viewportPx / barWidthPx) + 2;
    const desired = Math.max(1, barsInView);
    return Number.isFinite(visibleMeasureCount) ? Math.max(desired, visibleMeasureCount!) : desired;
  }, [barWidthPx, fallbackStartBar, trackBarCount, visibleMeasureCount]);

  const windowStartBar = viewStartBar;
  const renderStartBar = Math.max(0, windowStartBar - 1);
  const renderEndBar = windowStartBar + viewBarCount + 1;

  const filteredNotes = useMemo(() => {
    if (currentAspect === "all") return notes;
    return notes.filter((n) => n.aspect === currentAspect);
  }, [notes, currentAspect]);

  const inferredLimbById = useMemo(() => {
    // Inference only helps when limbId is missing/unknown.
    // Rules:
    // - hats/ride/crash -> RH by default
    // - snare/toms -> alternate hands when hits are close in time
    // - kick -> default RF (avoid incorrect LF assignment unless explicitly provided)
    const out: Record<string, LimbId> = {};

    const norm = (n: DrumNoteEvent): string | null => {
      const raw = (n.instrumentId || "").toString().trim().toLowerCase();
      if (raw) return raw;
      if (typeof n.midiPitch === "number") return String(getInstrumentForMidiPitch(n.midiPitch) || "").toLowerCase();
      return null;
    };

    const isHatPedal = (inst: string) => inst === "hihat_pedal" || inst.includes("hat_pedal") || inst.includes("pedal");
    const isKick = (inst: string) => inst === "kick" || inst.startsWith("kick") || inst.includes("bass");
    const isCymbalHat = (inst: string) =>
      inst.includes("hihat") || inst.includes("hat") || inst.includes("ride") || inst.includes("crash") || inst.includes("cymbal");
    const isSnare = (inst: string) => inst.startsWith("snare") || inst.includes("rim") || inst.includes("clap");
    const isTom = (inst: string) => inst.startsWith("tom") || inst.includes("tom");

    const normalizeLimbId = (raw?: DrumNoteEvent["limbId"] | null): LimbId | null => {
      if (!raw) return null;
      const v = String(raw);
      if (v === "LS") return "LH";
      if (v === "RS") return "RH";
      return SUPPORTED_LIMBS.includes(v as LimbId) ? (v as LimbId) : null;
    };

    const timeKey = (n: DrumNoteEvent) => {
      const bar = n.barIndex ?? 0;
      const tick = n.tickInBar ?? 0;
      return bar * ticksPerBar + tick;
    };

    const sorted = [...filteredNotes].sort((a, b) => timeKey(a) - timeKey(b));
    const handThreshold = Math.max(1, Math.round(ticksPerSubdivision * 0.75));

    let lastHand: LimbId = "RH";
    let lastHandTime: number | null = null;
    let lastKickFoot: LimbId = "RF";
    let lastKickTime: number | null = null;

    for (const n of sorted) {
      if (!n?.id) continue;
      const explicit = normalizeLimbId(n.limbId);

      const inst = norm(n);
      if (!inst) continue;
      const t = timeKey(n);

      // If a limb is already provided, use it as a strong hint/seed
      // for subsequent alternation, but still compute an inferred limb
      // so the 4-limb grid can be made consistent even when upstream
      // limbIds are unreliable.
      if (explicit) {
        if (explicit === "RH" || explicit === "LH") {
          lastHand = explicit;
          lastHandTime = t;
        }
        if (explicit === "RF" || explicit === "LF") {
          lastKickFoot = explicit;
          lastKickTime = t;
        }
      }

      if (isHatPedal(inst)) {
        out[n.id] = "LF";
        continue;
      }

      if (isKick(inst)) {
        // Keep kick on RF by default. If upstream provided an explicit LF/RF,
        // we already seeded lastKickFoot above.
        lastKickFoot = explicit === "LF" ? "LF" : "RF";
        lastKickTime = t;
        out[n.id] = lastKickFoot;
        continue;
      }

      // Cymbals/hats default to RH.
      if (isCymbalHat(inst)) {
        out[n.id] = "RH";
        lastHand = "RH";
        lastHandTime = t;
        continue;
      }

      // Snare: default to LH (avoid RH snare assignments).
      if (isSnare(inst)) {
        out[n.id] = "LH";
        lastHand = "LH";
        lastHandTime = t;
        continue;
      }

      // Toms: alternate when close in time.
      if (isTom(inst)) {
        const close = lastHandTime !== null && Math.abs(t - lastHandTime) <= handThreshold;
        if (close) {
          lastHand = lastHand === "RH" ? "LH" : "RH";
        } else {
          // For non-dense hits, default to conventional sticking.
          lastHand = "LH";
        }
        lastHandTime = t;
        out[n.id] = lastHand;
      }
    }

    return out;
  }, [filteredNotes, ticksPerBar, ticksPerSubdivision]);

  const handleNoteClick = useCallback(
    (note: DrumNoteEvent, ev: React.MouseEvent) => {
      ev.stopPropagation();

      try {
        const instRaw = (note.instrumentId || "").toString() as DrumInstrumentId;
        const inferred =
          instrumentOrder.includes(instRaw as any) && instRaw !== "other"
            ? (instRaw as DrumInstrumentId)
            : typeof note.midiPitch === "number"
              ? (getInstrumentForMidiPitch(note.midiPitch) as DrumInstrumentId)
              : null;
        const ch = inferred ? mapInstrumentToChannel(inferred) : null;
        if (ch && drumEngine) {
          const ctx = drumEngine.audioContext;
          const whenSec = ctx ? ctx.currentTime + 0.01 : undefined;
          drumEngine.playChannelOneShot(ch, {
            whenSec,
            gain: Math.max(0.2, Math.min(1.5, (Number((note as any)?.velocity ?? 100) || 100) / 100)),
          });
        }
      } catch {
        // ignore
      }

      if (!onNoteSelect) return;
      if (ev.shiftKey) {
        onNoteSelect([...selectedNoteIds, note.id]);
      } else {
        onNoteSelect([note.id]);
      }
    },
    [drumEngine, instrumentOrder, onNoteSelect, selectedNoteIds]
  );

  const [debugEnabled, setDebugEnabled] = useState(false);
  useEffect(() => {
    try {
      const v = (window.localStorage.getItem("drpDebug") || "").trim();
      setDebugEnabled(v === "1" || v.toLowerCase() === "true");
    } catch {
      setDebugEnabled(false);
    }
  }, []);

  const debugSelectedNote = useMemo(() => {
    if (!debugEnabled) return null;
    const id = selectedNoteIds?.[0];
    if (!id) return null;
    const n = notes.find((x) => x.id === id);
    if (!n) return null;
    const noteBar = n.barIndex ?? 0;
    const tickInBar = n.tickInBar ?? 0;
    const fracInBar = ticksPerBar > 0 ? tickInBar / ticksPerBar : 0;
    const x = noteBar * barWidthPx + fracInBar * barWidthPx;
    return { id, noteBar, tickInBar, x };
  }, [barWidthPx, debugEnabled, notes, selectedNoteIds, ticksPerBar]);

  const laneHeight = compact ? 6 : 28;
  const limbLaneHeight = compact ? 0 : 60;
  const totalLaneContentHeight =
    instrumentOrder.length * laneHeight + (compact ? 0 : limbLaneOrder.length * limbLaneHeight);

  const [layoutDebug, setLayoutDebug] = useState({
    yScrollTop: 0,
    yClientH: 0,
    yScrollH: 0,
    xClientH: 0,
    xScrollH: 0,
    labelTop: 0,
    gridTop: 0,
    labelGridDelta: 0,
    selectedDomX: 0,
    selectedXDelta: 0,
  });

  const debugNoteCounts = useMemo(() => {
    if (!debugEnabled) return null;
    const counts: Record<string, number> = {};
    for (const inst of instrumentOrder) counts[inst] = 0;
    for (const n of filteredNotes) {
      const instRaw = (n.instrumentId || "").toString();
      const hasLane = instrumentOrder.includes(instRaw as DrumInstrumentId);
      const inferred =
        hasLane && instRaw !== "other"
          ? (instRaw as DrumInstrumentId)
          : typeof n.midiPitch === "number"
            ? getInstrumentForMidiPitch(n.midiPitch)
            : "other";
      const key = (inferred || "other").toString();
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }, [debugEnabled, filteredNotes]);

  useEffect(() => {
    if (!debugEnabled) return;
    const yEl = laneYScrollRef.current;
    const xEl = laneScrollRef.current;
    const labelEl = labelColRef.current;
    const gridEl = gridInnerRef.current;
    if (!yEl || !xEl) return;

    let raf = 0;
    const update = () => {
      window.cancelAnimationFrame(raf);
      raf = window.requestAnimationFrame(() => {
        const labelTop = labelEl ? labelEl.getBoundingClientRect().top : 0;
        const gridTop = gridEl ? gridEl.getBoundingClientRect().top : 0;
        let selectedDomX = 0;
        let selectedXDelta = 0;
        if (gridEl && debugSelectedNote?.id) {
          const noteEl = gridEl.querySelector(`[data-note-id="${debugSelectedNote.id}"]`) as HTMLElement | null;
          if (noteEl) {
            const gridRect = gridEl.getBoundingClientRect();
            const noteRect = noteEl.getBoundingClientRect();
            const xInViewport = noteRect.left - gridRect.left;
            const scrollLeft = laneScrollRef.current?.scrollLeft ?? 0;
            // Convert to "content" coordinates to match how notes are positioned (absolute left in the grid content).
            selectedDomX = xInViewport + scrollLeft;
            selectedXDelta = selectedDomX - debugSelectedNote.x;
          }
        }
        setLayoutDebug({
          yScrollTop: yEl.scrollTop,
          yClientH: yEl.clientHeight,
          yScrollH: yEl.scrollHeight,
          xClientH: xEl.clientHeight,
          xScrollH: xEl.scrollHeight,
          labelTop,
          gridTop,
          labelGridDelta: gridTop - labelTop,
          selectedDomX,
          selectedXDelta,
        });
      });
    };

    update();
    yEl.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      yEl.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      window.cancelAnimationFrame(raf);
    };
  }, [debugEnabled]);

  const limbAccentForInstrument = useCallback((instrumentId: string): { limb: LimbId | null; accent?: string } => {
    const limb = inferLimbFromInstrument(instrumentId);
    return {
      limb,
      accent: limb ? LIMB_CONFIG[limb].accentColor : undefined,
    };
  }, []);

  const supportedLimb = useCallback((raw?: DrumNoteEvent["limbId"] | null): LimbId | null => {
    if (!raw) return null;
    const v = String(raw);
    if (v === "LS") return "LH";
    if (v === "RS") return "RH";
    return SUPPORTED_LIMBS.includes(v as LimbId) ? (v as LimbId) : null;
  }, []);

  const fallbackLimbForInstrument = useCallback((instrumentId: DrumInstrumentId | string | null | undefined): LimbId | null => {
    const v = (instrumentId || "").toString() as DrumInstrumentId;
    if (!v) return null;
    if (v === "kick") return "RF";
    if (v === "hihat_pedal") return "LF";
    if (v === "snare_center" || v === "snare_ghost" || v === "snare_rim") return "LH";
    if (v === "hihat_closed" || v === "hihat_open") return "RH";
    if (v === "ride_bow" || v === "ride_bell" || v === "ride_edge") return "RH";
    if (v === "crash_1" || v === "crash_2") return "RH";
    if (v === "tom_high" || v === "tom_mid" || v === "tom_floor") return "LH";
    return null;
  }, []);

  const limbAccentForNote = useCallback((note: DrumNoteEvent): { limb: LimbId | null; accent?: string } => {
    const direct = supportedLimb(note.limbId);
    const pitchFallback = inferLimbFromMidiPitch(note.midiPitch);
    const inferredInstrument = note.instrumentId
      ? note.instrumentId
      : typeof note.midiPitch === "number"
        ? getInstrumentForMidiPitch(note.midiPitch)
        : null;
    const fallback = inferredInstrument ? inferLimbFromInstrument(inferredInstrument) : null;
    const limb = direct ?? fallback ?? pitchFallback;
    return {
      limb,
      accent: limb ? LIMB_CONFIG[limb].accentColor : undefined,
    };
  }, [supportedLimb]);

  const limbForNote = useCallback(
    (note: DrumNoteEvent): LimbId | null => {
      const inferred = inferredLimbById[note.id];
      if (inferred && limbLaneOrder.includes(inferred)) {
        return inferred;
      }

      const direct = supportedLimb(note.limbId);
      if (direct) return direct;

      const pitchFallback = inferLimbFromMidiPitch(note.midiPitch);
      if (pitchFallback && limbLaneOrder.includes(pitchFallback)) {
        return pitchFallback;
      }

      const inferredInstrument = note.instrumentId
        ? note.instrumentId
        : typeof note.midiPitch === "number"
          ? getInstrumentForMidiPitch(note.midiPitch)
          : null;
      if (inferredInstrument) {
        const inferred = inferLimbFromInstrument(inferredInstrument);
        if (inferred && limbLaneOrder.includes(inferred)) {
          return inferred;
        }

        const fallback = fallbackLimbForInstrument(inferredInstrument);
        if (fallback && limbLaneOrder.includes(fallback)) {
          return fallback;
        }
      }
      return null;
    },
    [fallbackLimbForInstrument, inferredLimbById, supportedLimb],
  );

  const limbNotesByLimb: Record<LimbId, DrumNoteEvent[]> = useMemo(() => {
    const map: Record<string, DrumNoteEvent[]> = {};
    for (const limb of limbLaneOrder) {
      map[limb] = [];
    }
    for (const n of filteredNotes) {
      const limb = limbForNote(n);
      if (!limb || !limbLaneOrder.includes(limb)) {
        continue;
      }
      map[limb].push(n);
    }
    return map as Record<LimbId, DrumNoteEvent[]>;
  }, [filteredNotes, limbForNote]);

  const debugLimbCounts = useMemo(() => {
    if (!debugEnabled) return null;
    const limbCounts: Record<string, number> = {};
    for (const limb of limbLaneOrder) limbCounts[limb] = 0;
    let unassigned = 0;
    for (const n of filteredNotes) {
      const limb = limbForNote(n);
      if (!limb) {
        unassigned++;
        continue;
      }
      limbCounts[limb] = (limbCounts[limb] || 0) + 1;
    }
    return { limbCounts, unassigned };
  }, [debugEnabled, filteredNotes, limbForNote]);

  const copyDebugToClipboard = useCallback(async () => {
    if (!debugEnabled) return;
    const payload = {
      laneHeight,
      limbLaneHeight,
      totalLaneContentHeight,
      currentAspect,
      notesLen: notes.length,
      filteredLen: filteredNotes.length,
      layoutDebug,
      noteCounts: debugNoteCounts,
      limbCounts: debugLimbCounts,
    };
    const text = JSON.stringify(payload, null, 2);
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      try {
        window.prompt("Copy debug:", text);
      } catch {
        // ignore
      }
    }
  }, [
    currentAspect,
    debugEnabled,
    debugLimbCounts,
    debugNoteCounts,
    filteredNotes.length,
    laneHeight,
    layoutDebug,
    limbLaneHeight,
    notes.length,
    totalLaneContentHeight,
  ]);

  const toggleLimbHit = useCallback(
    (limb: LimbId, ev: React.MouseEvent) => {
      if (!onNoteChange) return;
      const laneEl = laneScrollRef.current;
      if (!laneEl) return;

      const rect = laneEl.getBoundingClientRect();
      const xPx = ev.clientX - rect.left + laneEl.scrollLeft;
      if (!Number.isFinite(xPx) || xPx < 0) return;

      const barIndex = Math.max(0, Math.floor(xPx / Math.max(1, barWidthPx)));
      const inBarPx = xPx - barIndex * barWidthPx;
      const cellPx = barWidthPx / Math.max(1, subdivisionsPerBar);
      const subIdx = Math.max(0, Math.min(subdivisionsPerBar - 1, Math.floor(inBarPx / Math.max(1, cellPx))));
      const tickInBar = Math.max(0, Math.round(subIdx * ticksPerSubdivision));
      const tickTolerance = Math.max(1, Math.floor(ticksPerSubdivision / 2));

      const existingIdx = notes.findIndex((n) => {
        const nLimb = limbForNote(n);
        if (nLimb !== limb) return false;
        if ((n.barIndex ?? 0) !== barIndex) return false;
        return Math.abs((n.tickInBar ?? 0) - tickInBar) <= tickTolerance;
      });

      if (existingIdx >= 0) {
        const next = notes.filter((_, idx) => idx !== existingIdx);
        onNoteChange(next);
        return;
      }

      const instrumentId = limbInstrumentByLimb[limb] ?? DEFAULT_LIMB_INSTRUMENT[limb] ?? "snare_center";
      const midiPitch = getMidiPitchForInstrument(instrumentId);
      const id = `limb-${limb}-${barIndex}-${tickInBar}-${Math.random().toString(36).slice(2, 7)}`;
      const velocity = 100;
      const aspect = currentAspect === "all" ? "groove" : (currentAspect as NoteAspect);

      const inferred = inferLimbFromInstrument(instrumentId);
      const limbMismatch = inferred && inferred !== limb;
      const overlapIdx = notes.findIndex((n) => {
        const nLimb = limbForNote(n);
        if (nLimb !== limb) return false;
        if ((n.barIndex ?? 0) !== barIndex) return false;
        return Math.abs((n.tickInBar ?? 0) - tickInBar) <= tickTolerance;
      });
      const hasOverlap = overlapIdx >= 0;

      if (limbMismatch || hasOverlap) {
        const inferredLabel = inferred ? LIMB_CONFIG[inferred]?.label ?? inferred : "Unknown";
        const limbLabel = LIMB_CONFIG[limb]?.label ?? limb;
        const reasons: string[] = [];
        if (limbMismatch) {
          reasons.push(`Selected instrument is typically played with ${inferredLabel}, not ${limbLabel}.`);
        }
        if (hasOverlap) {
          reasons.push(`There is already a ${limbLabel} hit at this time.`);
        }
        setLimbWarning({
          title: "Human capability warning",
          message: reasons.join(" "),
          pending: { limb, barIndex, tickInBar, instrumentId },
        });
        return;
      }

      const newNote: DrumNoteEvent = {
        id,
        barIndex,
        tickInBar,
        tickLength: Math.max(1, Math.round(ticksPerSubdivision * 0.95)),
        channel: 9,
        midiPitch,
        velocity,
        instrumentId,
        aspect,
        limbId: limb,
        isGhost: false,
        isAccent: false,
        isFlam: false,
        isDrag: false,
      };

      onNoteChange([...notes, newNote]);
      if (onNoteSelect) {
        onNoteSelect([id]);
      }

      auditionInstrument({ drumEngine, instrumentId, velocity });
    },
    [
      barWidthPx,
      currentAspect,
      drumEngine,
      limbInstrumentByLimb,
      limbForNote,
      notes,
      onNoteChange,
      onNoteSelect,
      subdivisionsPerBar,
      supportedLimb,
      ticksPerSubdivision,
    ],
  );

  const limbInstrumentOptions = useMemo(() => {
    const base = (instrumentOrder || []).filter((id) => id && id !== "other") as DrumInstrumentId[];
    const add = (id: DrumInstrumentId) => {
      if (!base.includes(id)) base.unshift(id);
    };
    for (const limb of limbLaneOrder) {
      const sel = limbInstrumentByLimb[limb];
      if (sel) add(sel);
      add(DEFAULT_LIMB_INSTRUMENT[limb]);
    }
    return base;
  }, [instrumentOrder, limbInstrumentByLimb]);

  const confirmLimbWarning = useCallback(() => {
    if (!limbWarning?.pending) {
      setLimbWarning(null);
      return;
    }
    const pending = limbWarning.pending;
    const ticksPerBarLocal = ticksPerSubdivision * subdivisionsPerBar;
    const newNote: DrumNoteEvent = {
      id: `limb-${pending.limb}-${pending.barIndex}-${pending.tickInBar}-${Math.random().toString(36).slice(2, 7)}`,
      barIndex: pending.barIndex,
      tickInBar: pending.tickInBar,
      tickLength: Math.max(1, Math.round(ticksPerSubdivision * 0.95)),
      channel: 9,
      midiPitch: getMidiPitchForInstrument(pending.instrumentId),
      velocity: 100,
      instrumentId: pending.instrumentId,
      aspect: currentAspect === "all" ? "groove" : (currentAspect as NoteAspect),
      limbId: pending.limb,
      isGhost: false,
      isAccent: false,
      isFlam: false,
      isDrag: false,
    };

    if (Number.isFinite(ticksPerBarLocal) && ticksPerBarLocal > 0) {
      // no-op: keep structure consistent with existing note creation paths
    }

    onNoteChange?.([...notes, newNote]);
    if (onNoteSelect) {
      onNoteSelect([newNote.id]);
    }

    auditionInstrument({ drumEngine, instrumentId: pending.instrumentId, velocity: newNote.velocity });
    setLimbWarning(null);
  }, [currentAspect, drumEngine, limbWarning, notes, onNoteChange, onNoteSelect, subdivisionsPerBar, ticksPerSubdivision]);

  const notesByInstrument: Record<DrumInstrumentId, DrumNoteEvent[]> = useMemo(
    () => {
      const map: Record<string, DrumNoteEvent[]> = {};
      for (const id of instrumentOrder) map[id] = [];
      for (const n of filteredNotes) {
        const instrumentIdRaw = (n.instrumentId || "").toString();
        const hasLane = instrumentOrder.includes(instrumentIdRaw as DrumInstrumentId);
        const inferred =
          hasLane && instrumentIdRaw !== "other"
            ? (instrumentIdRaw as DrumInstrumentId)
            : typeof n.midiPitch === "number"
              ? getInstrumentForMidiPitch(n.midiPitch)
              : "other";
        const key = (inferred || "other") as DrumInstrumentId;
        const arr = map[key] || (map[key] = []);
        arr.push(n);
      }
      return map as Record<DrumInstrumentId, DrumNoteEvent[]>;
    },
    [filteredNotes]
  );

  React.useEffect(() => {
    const headerEl = headerScrollRef.current;
    const laneEl = laneScrollRef.current;
    if (!laneEl || !headerEl) {
      return;
    }
    const syncHeader = () => {
      headerEl.scrollLeft = laneEl.scrollLeft;
    };
    laneEl.addEventListener("scroll", syncHeader, { passive: true });
    return () => {
      laneEl.removeEventListener("scroll", syncHeader);
    };
  }, [totalBarsSpan]);

  useEffect(() => {
    const laneEl = laneScrollRef.current;
    if (!laneEl) return;
    const update = () => {
      setScrollLeft(laneEl.scrollLeft);
    };
    update();
    laneEl.addEventListener("scroll", update, { passive: true });
    return () => laneEl.removeEventListener("scroll", update);
  }, [drumTrackId, barWidthPx]);

  React.useEffect(() => {
    if (scrollContainerRef) {
      (scrollContainerRef as React.MutableRefObject<HTMLDivElement | null>).current = laneScrollRef.current;
    }
    return () => {
      if (scrollContainerRef && scrollContainerRef.current === laneScrollRef.current) {
        (scrollContainerRef as React.MutableRefObject<HTMLDivElement | null>).current = null;
      }
    };
  }, [scrollContainerRef, drumTrackId]);

  if (!hasDrumTrack) {
    return (
      <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
        No drum track generated yet.
      </div>
    );
  }

  return (
    <div className="flex-1 min-w-0 flex flex-col bg-slate-900 text-xs overflow-hidden">
      {limbWarning && (
        <div className="absolute inset-0 z-[100] flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded border border-slate-700 bg-slate-950 shadow-2xl">
            <div className="px-4 py-3 border-b border-slate-800">
              <div className="text-sm font-semibold text-slate-100">{limbWarning.title}</div>
              <div className="text-[11px] text-slate-400 mt-1">{limbWarning.message}</div>
            </div>
            <div className="px-4 py-3 flex items-center justify-end gap-2">
              <button
                type="button"
                className="px-3 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-[11px] text-slate-200"
                onClick={() => setLimbWarning(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-1 rounded border border-amber-600/70 bg-amber-600/20 hover:bg-amber-600/30 text-[11px] text-amber-100"
                onClick={confirmLimbWarning}
              >
                Add Anyway
              </button>
            </div>
          </div>
        </div>
      )}
      {!compact && (
        <>
          {/* Header row */}
          <div className="flex flex-row border-b border-slate-700 min-w-0">
            <div className="w-36 flex-shrink-0 border-r border-slate-700 bg-slate-950 px-2 py-1 text-slate-400">
              <div className="flex items-center justify-between">
                <span>Instrument</span>
                <span className="text-[10px] text-slate-600">DRP-0109</span>
              </div>
              {debugEnabled && (
                <div className="mt-1 text-[10px] leading-snug text-slate-500 font-mono">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-slate-500">debug</div>
                    <button
                      type="button"
                      className="px-2 py-0.5 rounded border border-slate-700 bg-slate-900 text-[10px] text-slate-300 hover:border-slate-500"
                      onClick={() => void copyDebugToClipboard()}
                    >
                      Copy
                    </button>
                  </div>
                  <div>laneH {laneHeight} limbH {limbLaneHeight}</div>
                  <div>contentH {totalLaneContentHeight}</div>
                  <div>aspect {String(currentAspect)} notes {notes.length} filtered {filteredNotes.length}</div>
                  <div>y top {Math.round(layoutDebug.yScrollTop)} ch {layoutDebug.yClientH} sh {layoutDebug.yScrollH}</div>
                  <div>x ch {layoutDebug.xClientH} sh {layoutDebug.xScrollH}</div>
                  <div>delta label→grid {Math.round(layoutDebug.labelGridDelta)}px</div>
                  {debugSelectedNote && (
                    <div>
                      sel bar {debugSelectedNote.noteBar} tick {debugSelectedNote.tickInBar} x {Math.round(debugSelectedNote.x)}
                    </div>
                  )}
                  {debugSelectedNote && (
                    <div>
                      sel domX {Math.round(layoutDebug.selectedDomX)} dx {Math.round(layoutDebug.selectedXDelta)}
                    </div>
                  )}
                  {debugLimbCounts && (
                    <div>
                      <div>
                        limbs RH:{debugLimbCounts.limbCounts.RH ?? 0} LH:{debugLimbCounts.limbCounts.LH ?? 0} RF:{debugLimbCounts.limbCounts.RF ?? 0} LF:{debugLimbCounts.limbCounts.LF ?? 0}
                      </div>
                      <div>unassigned {debugLimbCounts.unassigned}</div>
                    </div>
                  )}
                  {debugNoteCounts && (
                    <div className="max-h-24 overflow-hidden">
                      {instrumentOrder.map((id) => (
                        <div key={`cnt-${id}`}>
                          {id}:{debugNoteCounts[id] ?? 0}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0 relative overflow-x-auto" ref={headerScrollRef}>
              <div className="relative" style={{ width: `${totalWidth}px`, height: 36 }}>
                {normalizedSectionRegions.map((r) => {
                  const left = r.startBar * barWidthPx;
                  const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
                  const isSelected = selectedSectionIdSet.has(String(r.id));
                  return (
                    <div
                      key={`section-hdr-${r.id}`}
                      className="absolute top-0 bottom-0"
                      style={{
                        left,
                        width,
                        background: r.color,
                        opacity: isSelected ? 0.26 : 0.10,
                        pointerEvents: "none",
                        zIndex: 1,
                      }}
                    />
                  );
                })}

                {normalizedSectionRegions.map((r) => {
                  if (!selectedSectionIdSet.has(String(r.id))) return null;
                  const left = r.startBar * barWidthPx;
                  const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
                  return (
                    <div
                      key={`section-hdr-outline-${r.id}`}
                      className="absolute top-0 bottom-0"
                      style={{
                        left,
                        width,
                        border: "2px solid rgba(217,70,239,0.55)",
                        boxShadow: "0 0 10px rgba(217,70,239,0.18)",
                        pointerEvents: "none",
                        zIndex: 4,
                      }}
                    />
                  );
                })}

                {normalizedSectionRegions.map((r) => {
                  const left = r.startBar * barWidthPx;
                  const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
                  return (
                    <Tooltip
                      key={`section-hdr-hit-${r.id}`}
                      content={r.label}
                      placement="top"
                      maxWidthClassName="w-56"
                      wrapperClassName="absolute top-0 bottom-0 bg-transparent"
                      wrapperStyle={{
                        left,
                        width,
                        cursor: onSectionSelect ? "pointer" : "default",
                        pointerEvents: onSectionSelect ? "auto" : "none",
                        zIndex: 2,
                      }}
                    >
                      <button
                        type="button"
                        className="h-full w-full"
                        onMouseDown={(ev) => {
                          if (!onSectionSelect) return;
                          ev.preventDefault();
                          ev.stopPropagation();
                          onSectionSelect(String(r.id));
                        }}
                      />
                    </Tooltip>
                  );
                })}

                {/* Bar labels */}
                {Array.from({ length: totalBarsSpan }).map((_, barIdx) => (
                  <div
                    key={`bar-label-${barIdx}`}
                    className={`absolute top-0 h-full flex items-center text-[10px] cursor-pointer select-none ${
                      selectedBarIndex === barIdx ? "bg-slate-800/40" : ""
                    }`}
                    style={{
                      left: barIdx * barWidthPx,
                      width: barWidthPx,
                      paddingLeft: 4,
                      borderRight: `1px solid ${BAR_GRID_THEME.bar}`,
                      color: BAR_GRID_THEME.label,
                    }}
                    onClick={() => onBarSelect?.(barIdx)}
                  >
                    <span>{barIdx + 1}</span>
                    {barDirectives?.[barIdx]?.forceFill ? (
                      <span
                        className="ml-1 px-1 rounded border text-[9px] font-semibold"
                        style={{ borderColor: "rgba(34,197,94,0.55)", color: "rgba(34,197,94,0.95)", background: "rgba(34,197,94,0.12)" }}
                        title="Force fill"
                      >
                        F
                      </span>
                    ) : null}
                    {barDirectives?.[barIdx]?.suppressFill ? (
                      <span
                        className="ml-1 px-1 rounded border text-[9px] font-semibold"
                        style={{ borderColor: "rgba(244,63,94,0.55)", color: "rgba(244,63,94,0.95)", background: "rgba(244,63,94,0.12)" }}
                        title="Suppress fill"
                      >
                        Ø
                      </span>
                    ) : null}
                  </div>
                ))}

                {Array.from({ length: totalBarsSpan }).flatMap((_, barIdx) =>
                  Array.from({ length: beatsPerBar }).map((__, beatIdx) => {
                    const left = barIdx * barWidthPx + beatIdx * pixelsPerBeat;
                    return (
                      <div
                        key={`beat-label-${barIdx}-${beatIdx}`}
                        className="absolute"
                        style={{
                          left,
                          top: 18,
                          width: pixelsPerBeat,
                          height: 18,
                          paddingLeft: 4,
                          color: "rgba(226,232,240,0.70)",
                          fontSize: 10,
                          fontWeight: 700,
                          pointerEvents: "none",
                          userSelect: "none",
                        }}
                      >
                        {beatIdx + 1}
                      </div>
                    );
                  }),
                )}

                {Array.from({ length: totalBarsSpan }).flatMap((_, barIdx) =>
                  Array.from({ length: subdivisionsPerBar }).flatMap((__, subIdx) => {
                    const withinBeat = subIdx % subdivisionsPerBeat;
                    const label = subdivisionLabelForIndex(withinBeat);
                    if (!label) return [];
                    const left = barIdx * barWidthPx + (barWidthPx * subIdx) / subdivisionsPerBar;
                    return (
                      <div
                        key={`sub-label-${barIdx}-${subIdx}`}
                        className="absolute"
                        style={{
                          left,
                          top: 18,
                          width: Math.max(1, barWidthPx / Math.max(1, subdivisionsPerBar)),
                          height: 18,
                          paddingLeft: 4,
                          color: "rgba(226,232,240,0.45)",
                          fontSize: 10,
                          fontWeight: 700,
                          pointerEvents: "none",
                          userSelect: "none",
                        }}
                      >
                        {label}
                      </div>
                    );
                  }),
                )}

                {normalizedSectionRegions.map((r) => {
                  const left = r.startBar * barWidthPx;
                  const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
                  return (
                    <div
                      key={`section-label-${r.id}`}
                      className="absolute top-0 h-full flex items-center"
                      style={{
                        left: left + 18,
                        width: Math.max(1, width - 24),
                        color: r.color,
                        opacity: 0.95,
                        pointerEvents: "none",
                        zIndex: 3,
                        fontSize: 10,
                        fontWeight: 700,
                        textShadow: "0 1px 0 rgba(0,0,0,0.6)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {r.label}
                    </div>
                  );
                })}

                {/* Subdivision grid + groove weights */}
                {Array.from({ length: totalBarsSpan }).map((_, barIdx) =>
                  Array.from({ length: subdivisionsPerBar }).map((__, subIdx) => {
                    const left = barIdx * barWidthPx + (barWidthPx * subIdx) / subdivisionsPerBar;

                    const weight = grooveWeights?.[barIdx]?.[subIdx]?.weight ?? "neutral";
                    let color = BAR_GRID_THEME.subdivision;
                    if (subIdx % (subdivisionsPerBar / 4 || 1) === 0) {
                      color = BAR_GRID_THEME.beat;
                    }
                    if (weight === "heavy") {
                      color = BAR_GRID_THEME.bar;
                    } else if (weight === "syncopated") {
                      color = BAR_GRID_THEME.accent;
                    }

                    return (
                      <div
                        key={`${barIdx}-${subIdx}`}
                        className="absolute top-0 bottom-0"
                        style={{
                          left,
                          borderLeft: `1px solid ${color}`,
                          opacity: subIdx % (subdivisionsPerBar / 4 || 1) === 0 ? 0.95 : 0.65,
                        }}
                      />
                    );
                  }),
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Main content */}
      <div className="flex flex-row flex-1 overflow-hidden min-w-0">
        <div className="flex-1 min-w-0 overflow-y-auto overflow-x-hidden" ref={laneYScrollRef}>
          <div className="flex flex-row min-w-0 items-start">
            {/* Instrument labels (shares vertical scroll with grid) */}
            {!compact && (
              <div className="w-36 flex-shrink-0 bg-slate-950 border-r border-slate-700" ref={labelColRef}>
                {instrumentOrder.map((instId) => {
                  const { accent } = limbAccentForInstrument(instId);
                  const channelId = mapInstrumentToChannel(instId);
                  const chState = laneChannelState[instId] || { mute: false, solo: false };
                  return (
                    <div
                      key={instId}
                      className="flex items-center justify-between gap-2 px-2 text-[11px] font-semibold"
                      style={{
                        height: laneHeight,
                        color: accent || "#e2e8f0",
                        backgroundColor: accent ? `${accent}1a` : undefined,
                        boxShadow: `inset 0 -1px 0 ${accent ? `${accent}66` : "rgba(148, 163, 184, 0.10)"}`,
                      }}
                    >
                      <span className="min-w-0 flex-1 truncate">{instId.replace("_", " ")}</span>
                      {drumEngine && channelId && (
                        <span className="flex items-center gap-1">
                          <Tooltip content="Solo" placement="top" maxWidthClassName="w-20">
                            <button
                              type="button"
                              className={
                                "w-5 h-4 rounded border text-[9px] leading-none " +
                                (chState.solo
                                  ? "bg-yellow-500/80 border-yellow-300 text-black"
                                  : "bg-slate-900 border-slate-700 text-slate-300")
                              }
                              onClick={() => {
                                const next = !chState.solo;
                                drumEngine.setChannelParams(channelId, { solo: next });
                                setLaneChannelState((prev) => ({
                                  ...prev,
                                  [instId]: { ...chState, solo: next },
                                }));
                              }}
                            >
                              S
                            </button>
                          </Tooltip>
                          <Tooltip content="Mute" placement="top" maxWidthClassName="w-20">
                            <button
                              type="button"
                              className={
                                "w-5 h-4 rounded border text-[9px] leading-none " +
                                (chState.mute
                                  ? "bg-red-600/80 border-red-300 text-white"
                                  : "bg-slate-900 border-slate-700 text-slate-300")
                              }
                              onClick={() => {
                                const next = !chState.mute;
                                drumEngine.setChannelParams(channelId, { mute: next });
                                setLaneChannelState((prev) => ({
                                  ...prev,
                                  [instId]: { ...chState, mute: next },
                                }));
                              }}
                            >
                              M
                            </button>
                          </Tooltip>
                        </span>
                      )}
                    </div>
                  );
                })}

                {!compact && (
                  <>
                    {limbLaneOrder.map((limb) => (
                      <div
                        key={`limb-label-${limb}`}
                        className="flex items-center px-2 text-[11px] font-semibold"
                        style={{
                          height: limbLaneHeight,
                          color: LIMB_CONFIG[limb].accentColor,
                          boxShadow: "inset 0 1px 0 rgba(148, 163, 184, 0.12)",
                        }}
                      >
                        <div className="flex items-center justify-between gap-2 w-full">
                          <span>{LIMB_CONFIG[limb].label}</span>
                          <Tooltip
                            content="Instrument used when clicking this limb lane"
                            placement="top"
                            maxWidthClassName="w-72"
                          >
                            <select
                              className="bg-slate-900 border border-slate-700 rounded px-1 py-0.5 text-[10px] text-slate-100"
                              value={limbInstrumentByLimb[limb] ?? DEFAULT_LIMB_INSTRUMENT[limb]}
                              onChange={(e) => {
                                const next = e.target.value as DrumInstrumentId;
                                setLimbInstrumentByLimb((prev) => ({ ...prev, [limb]: next }));
                              }}
                            >
                              {limbInstrumentOptions.map((inst) => (
                                <option key={`${limb}-inst-${inst}`} value={inst}>
                                  {inst.replaceAll("_", " ")}
                                </option>
                              ))}
                            </select>
                          </Tooltip>
                        </div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            )}

            {/* Note lanes (horizontal scroll only; shares vertical scroll with labels) */}
            <div
              className="flex-1 min-w-0 relative overflow-x-auto overflow-y-hidden"
              ref={laneScrollRef}
              style={{ height: totalLaneContentHeight, alignSelf: "flex-start" }}
            >
              <div
                className="relative"
                ref={gridInnerRef}
                style={{
                  width: `${totalWidth}px`,
                  height: totalLaneContentHeight,
                  borderRight: `1px solid ${BAR_GRID_THEME.bar}`,
                }}
              >
                {debugEnabled && (
                  <div className="absolute inset-0 pointer-events-none" style={{ zIndex: 50 }}>
                    {instrumentOrder.map((instId, idx) => (
                      <div
                        key={`dbg-lane-label-${instId}`}
                        className="absolute left-1"
                        style={{
                          top: idx * laneHeight + 2,
                          fontSize: 10,
                          color: "rgba(226,232,240,0.55)",
                          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                        }}
                      >
                        {idx}
                      </div>
                    ))}
                    {!compact &&
                      limbLaneOrder.map((limb, idx) => (
                        <div
                          key={`dbg-limb-label-${limb}`}
                          className="absolute left-1"
                          style={{
                            top: instrumentOrder.length * laneHeight + idx * limbLaneHeight + 2,
                            fontSize: 10,
                            color: "rgba(226,232,240,0.55)",
                            fontFamily:
                              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
                          }}
                        >
                          L{idx}
                        </div>
                      ))}
                  </div>
                )}

                {debugEnabled && debugSelectedNote && (
                  <div
                    className="absolute top-0 bottom-0 pointer-events-none"
                    style={{
                      left: debugSelectedNote.x,
                      width: 1,
                      background: "rgba(253, 224, 71, 0.9)",
                      boxShadow: "0 0 6px rgba(253, 224, 71, 0.45)",
                      zIndex: 60,
                    }}
                  />
                )}
                {normalizedSectionRegions.map((r) => {
                  const left = r.startBar * barWidthPx;
                  const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
                  const isSelected = selectedSectionIdSet.has(String(r.id));
                  return (
                    <div
                      key={`section-lane-${r.id}`}
                      className="absolute top-0 bottom-0"
                      style={{
                        left,
                        width,
                        background: r.color,
                        opacity: isSelected ? 0.20 : 0.08,
                        pointerEvents: "none",
                        zIndex: 0,
                      }}
                    />
                  );
                })}

                {normalizedSectionRegions.map((r) => {
                  if (!selectedSectionIdSet.has(String(r.id))) return null;
                  const left = r.startBar * barWidthPx;
                  const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
                  return (
                    <div
                      key={`section-lane-outline-${r.id}`}
                      className="absolute top-0 bottom-0"
                      style={{
                        left,
                        width,
                        border: "2px solid rgba(217,70,239,0.45)",
                        pointerEvents: "none",
                        zIndex: 2,
                      }}
                    />
                  );
                })}

                {normalizedSectionRegions.map((r) => {
                  const left = r.startBar * barWidthPx;
                  const width = Math.max(1, (r.endBar - r.startBar + 1) * barWidthPx);
                  return (
                    <Tooltip
                      key={`section-lane-hit-${r.id}`}
                      content={r.label}
                      placement="top"
                      maxWidthClassName="w-56"
                      wrapperClassName="absolute top-0 bottom-0 bg-transparent"
                      wrapperStyle={{
                        left,
                        width,
                        cursor: onSectionSelect ? "pointer" : "default",
                        pointerEvents: onSectionSelect ? "auto" : "none",
                        zIndex: 1,
                      }}
                    >
                      <button
                        type="button"
                        className="h-full w-full"
                        onMouseDown={(ev) => {
                          if (!onSectionSelect) return;
                          ev.preventDefault();
                          ev.stopPropagation();
                          onSectionSelect(String(r.id));
                        }}
                      />
                    </Tooltip>
                  );
                })}
                {clampedPlayheadX !== null && (
                  <div
                    className="absolute top-0 bottom-0"
                    style={{
                      left: clampedPlayheadX,
                      width: 2,
                      background: "rgba(34, 211, 238, 0.8)",
                      boxShadow: "0 0 8px rgba(34, 211, 238, 0.6)",
                      pointerEvents: "none",
                      zIndex: 20,
                    }}
                  />
                )}
                {Array.from({ length: totalBarsSpan }).map((_, barIdx) => (
                  <div
                    key={`lane-grid-bar-${barIdx}`}
                    className="absolute top-0 bottom-0"
                    style={{
                      left: barIdx * barWidthPx,
                      borderLeft: `1px solid ${BAR_GRID_THEME.bar}`,
                      opacity: 0.9,
                      pointerEvents: "none",
                    }}
                  />
                ))}
                {Array.from({ length: totalBarsSpan }).flatMap((_, barIdx) =>
                  Array.from({ length: subdivisionsPerBar }).map((__, subIdx) => {
                    const left = barIdx * barWidthPx + (barWidthPx * subIdx) / subdivisionsPerBar;
                    const isBeat = subIdx % (subdivisionsPerBar / 4 || 1) === 0;
                    const color = isBeat ? BAR_GRID_THEME.beat : BAR_GRID_THEME.subdivision;
                    return (
                      <div
                        key={`lane-grid-sub-${barIdx}-${subIdx}`}
                        className="absolute top-0 bottom-0"
                        style={{
                          left,
                          borderLeft: `1px solid ${color}`,
                          opacity: isBeat ? 0.6 : 0.45,
                          pointerEvents: "none",
                        }}
                      />
                    );
                  }),
                )}

                {/* Horizontal lines */}
                {instrumentOrder.map((instId, laneIdx) => (
                  <div
                    key={instId}
                    className="absolute left-0 right-0"
                    style={{
                      top: laneIdx * laneHeight,
                      height: laneHeight,
                      borderBottom: "1px solid rgba(148, 163, 184, 0.14)",
                      pointerEvents: "none",
                    }}
                  />
                ))}

                {!compact &&
                  instrumentOrder.map((instId, laneIdx) => (
                    <div
                      key={`lane-mid-${instId}`}
                      className="absolute left-0 right-0"
                      style={{
                        top: laneIdx * laneHeight + Math.floor(laneHeight / 2),
                        height: 1,
                        borderTop: "1px solid rgba(148, 163, 184, 0.08)",
                        pointerEvents: "none",
                      }}
                    />
                  ))}

                {!compact &&
                  limbLaneOrder.map((limb, idx) => (
                    <div
                      key={`limb-row-${limb}`}
                      className="absolute left-0 right-0"
                      style={{
                        top: instrumentOrder.length * laneHeight + idx * limbLaneHeight,
                        height: limbLaneHeight,
                        borderTop: "1px solid rgba(148, 163, 184, 0.14)",
                        pointerEvents: "none",
                      }}
                    />
                  ))}

                {/* Notes */}
                {instrumentOrder.map((instId, laneIdx) => {
                  const laneNotes = notesByInstrument[instId] || [];
                  const h = Math.max(2, laneHeight - 2);
                  const y = 1;
                  return (
                    <div
                      key={`inst-lane-${instId}`}
                      className="absolute left-0 right-0"
                      style={{
                        top: laneIdx * laneHeight,
                        height: laneHeight,
                        zIndex: 10,
                      }}
                    >
                      {laneNotes.map((n) => {
                        const noteBar = n.barIndex ?? 0;
                        if (noteBar < renderStartBar || noteBar > renderEndBar) {
                          return null;
                        }

                        const fracInBar = (n.tickInBar ?? 0) / ticksPerBar;
                        const x = noteBar * barWidthPx + fracInBar * barWidthPx;
                        const w = Math.max(
                          4,
                          barWidthPx * ((n.tickLength ?? ticksPerSubdivision) / ticksPerBar)
                        );

                        const selected = selectedNoteIds.includes(n.id);
                        const { accent: limbAccent, limb } = limbAccentForNote(n);
                        const accent = ACCENT_BY_INSTRUMENT[instId] ?? limbAccent;
                        let backgroundColor = accent ? `${accent}d0` : "#64748b";
                        if (n.isGhost) backgroundColor = accent ? `${accent}66` : "#94a3b8";
                        else if (n.isAccent) backgroundColor = accent ? `${accent}ff` : "#fbbf24";
                        else if (n.aspect === "fill") backgroundColor = accent ? `${accent}b3` : "#a855f7";
                        const borderColor = accent ? `${accent}a0` : "transparent";
                        const limbLabel = limb ? LIMB_CONFIG[limb].label : "Unassigned";

                        return (
                          <div
                            key={n.id}
                            className={`absolute rounded-sm cursor-pointer border ${
                              selected ? "outline outline-1 outline-white" : ""
                            } ${n.locked ? "ring-2 ring-emerald-400/80" : ""}`}
                            data-note-id={n.id}
                            style={{
                              left: x,
                              top: y,
                              width: w,
                              height: h,
                              backgroundColor,
                              borderColor,
                              color: accent ? "#0f172a" : undefined,
                              boxSizing: "border-box",
                              zIndex: selected ? 12 : 10,
                            }}
                          >
                            <Tooltip
                              content={`${instId} (lane) · ${String((n as any).instrumentId || "") || "(no instrumentId)"} (note) · pitch ${n.midiPitch} · ${limbLabel} @ bar ${noteBar + 1}`}
                              placement="top"
                              maxWidthClassName="w-64"
                              wrapperClassName="w-full h-full"
                            >
                              <div className="h-full w-full" onClick={(ev) => handleNoteClick(n, ev)} />
                            </Tooltip>
                          </div>
                        );
                      })}
                    </div>
                  );
                })}

                {!compact &&
                  limbLaneOrder.map((limb, limbIdx) => {
                    const laneNotes = limbNotesByLimb[limb] || [];
                    const maxSlots = 1;
                    const slotH = Math.max(10, Math.floor((limbLaneHeight - 2) / maxSlots));
                    const h = Math.max(6, slotH - 2);
                    const limbAccent = LIMB_CONFIG[limb].accentColor;
                    return (
                      <div
                        key={`limb-lane-${limb}`}
                        className="absolute left-0 right-0"
                        style={{
                          top: instrumentOrder.length * laneHeight + limbIdx * limbLaneHeight,
                          height: limbLaneHeight,
                          zIndex: 8,
                        }}
                        onMouseDown={(ev) => {
                          ev.stopPropagation();
                          toggleLimbHit(limb, ev);
                        }}
                      >
                        {(() => {
                          // Group by time so simultaneous hits can be stacked.
                          const groups = new Map<string, DrumNoteEvent[]>();
                          for (const n of laneNotes) {
                            const noteBar = n.barIndex ?? 0;
                            if (noteBar < renderStartBar || noteBar > renderEndBar) continue;
                            const key = `${noteBar}:${n.tickInBar ?? 0}`;
                            const arr = groups.get(key);
                            if (arr) arr.push(n);
                            else groups.set(key, [n]);
                          }

                          const rendered: React.ReactNode[] = [];
                          const groupArrays = Array.from(groups.values());
                          for (const arr of groupArrays) {
                            arr.sort((a, b) => {
                              const ai = instrumentOrder.indexOf((a.instrumentId || "") as any);
                              const bi = instrumentOrder.indexOf((b.instrumentId || "") as any);
                              return (ai < 0 ? 999 : ai) - (bi < 0 ? 999 : bi);
                            });

                            for (let slot = 0; slot < arr.length; slot++) {
                              const n = arr[slot];
                              const noteBar = n.barIndex ?? 0;
                              const fracInBar = (n.tickInBar ?? 0) / ticksPerBar;
                              const x = noteBar * barWidthPx + fracInBar * barWidthPx;
                              const w = Math.max(4, barWidthPx * ((n.tickLength ?? ticksPerSubdivision) / ticksPerBar));
                              const selected = selectedNoteIds.includes(n.id);
                              const iconUrl = getIconUrlForInstrument(n.instrumentId);
                              const y = 1 + (slot % maxSlots) * slotH;
                              const hitAccent =
                                ACCENT_BY_INSTRUMENT[n.instrumentId] ||
                                (typeof n.midiPitch === "number"
                                  ? ACCENT_BY_INSTRUMENT[getInstrumentForMidiPitch(n.midiPitch) as DrumInstrumentId]
                                  : undefined) ||
                                limbAccent;

                              rendered.push(
                                <div
                                  key={`limb-hit-${n.id}`}
                                  className={`absolute rounded-sm border ${selected ? "outline outline-1 outline-white" : ""}`}
                                  style={{
                                    left: x,
                                    top: y,
                                    width: w,
                                    height: h,
                                    backgroundColor: `${hitAccent}33`,
                                    borderColor: `${hitAccent}aa`,
                                    boxSizing: "border-box",
                                    pointerEvents: "none",
                                    overflow: "hidden",
                                  }}
                                >
                                  {iconUrl && (
                                    <img
                                      src={iconUrl}
                                      alt={n.instrumentId}
                                      style={{
                                        width: "100%",
                                        height: "100%",
                                        padding: 2,
                                        boxSizing: "border-box",
                                        objectFit: "contain",
                                        opacity: 0.92,
                                        filter:
                                          "invert(1) brightness(1.1) contrast(1.35) drop-shadow(0 0 2px rgba(0,0,0,0.75))",
                                      }}
                                    />
                                  )}
                                </div>
                              );
                            }
                          }
                          return rendered;
                        })()}
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
