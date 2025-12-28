import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import webdawApi, { alignSections, loadSession, saveSession, sectionizeAudio, dcsmSectionizeSmart } from "../services/api";
import Timeline from "./Timeline";
import { Engine } from "../audio/engine";
import DrumPlayerModal from "./drums/DrumPlayerModal";
import { getSharedDrumPlayerEngine, type DrumPlayerChannelId } from "../audio/drumPlayerEngine";
import type { MidiNote as PianoRollNote } from "./PianoRoll";
import { SectionControls } from "./SectionControls";
import { DrummerSelector, Drummer } from "./DrummerSelector";
import DrumOptionsPanel, { DrumOptions } from "./DrumOptionsPanel";
import MicroTempoMeter from "./MicroTempoMeter";
import { ManualArrangementModal, ManualArrangement } from "./ManualArrangementModal";
import { InternetSongLookupModal, SongInfo } from "./InternetSongLookupModal";
import DrumBuilderPanelV2 from "./DrumBuilderPanelV2";
import { useBrainPanelStore } from "../state/useBrainPanelStore";
import { BrainPanel } from "./brain/BrainPanel";
import {
  DrumGenerationConfig,
  DrumTrackForDCSM,
  DrumNoteEvent,
  DrumInstrumentId,
  LimbId as DrumTrackLimbId,
  DRUM_INSTRUMENT_MIDI_MAP,
} from "../types/drumTrack";
import { GrooveWeightMap } from "../types/grooveWeight";
import { DrumEditorPane } from "./drums/DrumEditorPane";
import { resolveApiBaseNormalized } from "../utils/apiBase";
import { GridResolution } from "../utils/pianoRollGrid";
import { inferLimbFromInstrument, inferLimbFromLane, type LimbId } from "../constants/limbs";
import type { DrumSectionRegion } from "./drums/DrumPianoRoll";
import { useMidi } from "../midi/midiStore";
import type { MidiClip, MidiNote as MidiClipNote } from "../midi/types";
import {
  applyDrumGenerationResult,
  DrumGenerationDebugSnapshot,
  DrumTrackPlacementContext,
} from "./drumGenerationHandlers";

function HoverTip({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <span className="relative inline-flex items-center group">
      {children}
      <span className="pointer-events-none absolute left-0 top-full mt-1 hidden w-72 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-[11px] text-slate-200 shadow-xl group-hover:block z-50">
        {text}
      </span>
    </span>
  );
}

function DrummerPersonaModal({
  open,
  onClose,
  selectedDrummer,
  onSelect,
}: {
  open: boolean;
  onClose: () => void;
  selectedDrummer: Drummer | null;
  onSelect: (drummer: Drummer) => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-950 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 p-4">
          <div>
            <div className="text-sm font-semibold text-white">Choose a Drum Personality</div>
            <div className="mt-1 text-xs text-slate-400">
              This step selects the drummer persona (feel, time, dynamics, limb tendencies) that will guide every
              generation.
            </div>
          </div>
          <button
            className="text-slate-400 hover:text-slate-100"
            onClick={onClose}
            title="Close"
            type="button"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 text-xs text-slate-300">
            <div>
              <span className="font-semibold text-slate-100">What it is:</span> a drummer model/persona used to keep grooves stylistically consistent.
            </div>
            <div className="mt-1">
              <span className="font-semibold text-slate-100">Why it matters:</span> prevents random feel changes and improves musical continuity across sections.
            </div>
            <div className="mt-1">
              <span className="font-semibold text-slate-100">When to change:</span> only if you intentionally want a different drummer feel.
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">Selected</div>
                <div className="text-sm font-semibold text-white">
                  {selectedDrummer?.display_name || "None"}
                </div>
              </div>
              {selectedDrummer && (
                <span className="text-[11px] px-2 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                  {selectedDrummer.style?.toUpperCase() || "CUSTOM"}
                </span>
              )}
            </div>
            <div className="mt-3">
              <DrummerSelector
                onSelect={(drummer) => {
                  onSelect(drummer);
                  onClose();
                }}
                selectedDrummer={selectedDrummer}
              />
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-slate-800 p-4">
          <button
            className="px-3 py-1.5 rounded bg-slate-800 border border-slate-700 text-sm text-slate-200 hover:bg-slate-700"
            onClick={onClose}
            type="button"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export type UploadedTrack = {
  key: string;
  peaks: number[];
  sr: number;
  seconds: number;
  color: string;
  name: string;
  peaksL?: number[];
  peaksR?: number[];
  waveformExtents?: WaveformExtent[];
  waveformExtentsL?: WaveformExtent[];
  waveformExtentsR?: WaveformExtent[];
};

type WaveformExtent = {
  min: number;
  max: number;
};

export type Section = {
  id: string;
  start: number;
  end: number;
  density: number;
  fillIn: boolean;
  fillOut: boolean;
  label?: string;                 // intro/verse/chorus/bridge/outro/break/solo
  confidence?: number;             // 0.0-1.0 confidence in section label
  energy?: number;                 // 0.0-1.0 RMS energy (loudness)
  spectral_centroid?: number;      // 0.0-1.0 spectral centroid (brightness)
  repetition_group?: number;       // Group ID for similar sections
  tempo?: number;                  // Detected tempo for this section
  tempoConfidence?: number;        // 0.0-1.0 confidence in tempo detection
  tempoLocked?: boolean;           // User has manually set tempo
  startBarIndex?: number;          // Absolute bar index from SongMap
  endBarIndex?: number;            // Inclusive bar index
  barCount?: number;               // Number of bars in section
  timeSignature?: [number, number];// Section-specific meter if available
};

export type MeasureRange = {
  sectionId: string;
  sectionLabel: string;
  startMeasure: number;
  endMeasure: number;
  measureCount: number;
  tempos: number[];
  avgTempo: number;
  timeSignature: [number, number];
  startTime: number;
  endTime: number;
};

const DRUM_SECTION_LABELS = new Set(["intro", "verse", "chorus", "bridge", "outro"]);

const SCRATCH_SECTION_LABEL_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "intro", label: "Intro" },
  { value: "verse", label: "Verse" },
  { value: "prechorus", label: "Pre-Chorus" },
  { value: "chorus", label: "Chorus" },
  { value: "postchorus", label: "Post-Chorus" },
  { value: "bridge", label: "Bridge" },
  { value: "breakdown", label: "Breakdown" },
  { value: "interlude", label: "Interlude" },
  { value: "solo", label: "Solo" },
  { value: "outro", label: "Outro" },
  { value: "ending", label: "Ending" },
  { value: "tag", label: "Tag" },
  { value: "transition", label: "Transition" },
  { value: "turnaround", label: "Turnaround" },
  { value: "pickup", label: "Pickup" },
  { value: "link", label: "Link" },
  { value: "break", label: "Break" },
  { value: "vamp", label: "Vamp" },
  { value: "count_in", label: "Count-In" },
  { value: "coda", label: "Coda" },
  { value: "buildup", label: "Build-Up" },
  { value: "rise", label: "Rise" },
  { value: "drop", label: "Drop" },
  { value: "climax", label: "Climax" },
  { value: "lift", label: "Lift" },
  { value: "fall", label: "Fall" },
  { value: "half_time", label: "Half-Time" },
  { value: "double_time", label: "Double-Time" },
  { value: "final_chorus", label: "Final Chorus" },
  { value: "double_chorus", label: "Double Chorus" },
  { value: "unknown", label: "Unknown" },
];

type SectionPatternPreset = {
  intensity: number;
  variation: number;
  fillDensity: number;
  fillType: DrumOptions["fill_preset"];
  mode: "template" | "ai_variation" | "full_ai";
  swingBoost?: number;
  ghostBoost?: number;
  preferRudiments?: boolean;
  enforceFill?: boolean;
};

const SECTION_AUTOGEN_PRESETS: Record<string, SectionPatternPreset> = {
  intro: {
    intensity: 0.35,
    variation: 0.25,
    fillDensity: 0.15,
    fillType: "none",
    mode: "template",
    swingBoost: -0.05,
  },
  verse: {
    intensity: 0.55,
    variation: 0.35,
    fillDensity: 0.25,
    fillType: "auto",
    mode: "ai_variation",
  },
  chorus: {
    intensity: 0.9,
    variation: 0.65,
    fillDensity: 0.55,
    fillType: "tomrun",
    mode: "full_ai",
    swingBoost: 0.05,
    ghostBoost: 0.1,
    preferRudiments: true,
    enforceFill: true,
  },
  bridge: {
    intensity: 0.7,
    variation: 0.7,
    fillDensity: 0.45,
    fillType: "snarebuzz",
    mode: "full_ai",
    ghostBoost: 0.08,
    preferRudiments: true,
  },
  outro: {
    intensity: 0.45,
    variation: 0.4,
    fillDensity: 0.2,
    fillType: "auto",
    mode: "ai_variation",
    swingBoost: -0.02,
  },
  default: {
    intensity: 0.6,
    variation: 0.45,
    fillDensity: 0.3,
    fillType: "auto",
    mode: "ai_variation",
  },
};

const clamp01 = (value: number): number => {
  if (!Number.isFinite(value)) return 0;
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
};

type SongMapSummary = {
  duration?: number;
  globalBpmEstimate?: number;
  meter?: [number, number];
  bars?: Array<{ tempo_bpm?: number }>;
  sections?: any[];
  beatTimes?: number[];
  source?: string;
  title?: string;
  artist?: string;
};

const mapInstrumentToLane = (instrument?: string): string => {
  if (!instrument) return "snare";
  const id = instrument.toLowerCase();
  if (id.startsWith("kick")) return "kick";
  if (id.startsWith("snare")) return "snare";
  if (id.includes("open") && id.includes("hat")) return "openhat";
  if (id.includes("hat")) return "hihat";
  if (id.startsWith("ride")) return "ride";
  if (id.startsWith("crash") || id.includes("china") || id.includes("splash")) return "crash";
  if (id.startsWith("tom")) return "tom";
  if (id.includes("clap") || id.includes("perc") || id.includes("cowbell")) return "clap";
  return "tom";
};

const laneToInstrumentId = (lane?: string): DrumInstrumentId => {
  switch ((lane || "snare").toLowerCase()) {
    case "kick":
      return "kick";
    case "snare":
    case "snare_center":
      return "snare_center";
    case "snare_rim":
      return "snare_rim";
    case "snare_ghost":
      return "snare_ghost";
    case "openhat":
      return "hihat_open";
    case "hihat":
      return "hihat_closed";
    case "ride":
      return "ride_bow";
    case "ridebell":
      return "ride_bell";
    case "tom":
    case "tom_high":
      return "tom_high";
    case "tom_mid":
      return "tom_mid";
    case "tom_floor":
      return "tom_floor";
    case "crash":
      return "crash_1";
    case "crash2":
      return "crash_2";
    case "perc":
    case "clap":
    case "cowbell":
      return "other";
    default:
      return "other";
  }
};

const normalizeVelocity = (velocity?: number): number => {
  if (velocity == null) return 0.8;
  if (velocity > 1) {
    return Math.max(0, Math.min(1, velocity / 127));
  }
  return Math.max(0, Math.min(1, velocity));
};

type LegacyNoteCandidate = {
  id?: string;
  time?: number;
  length?: number;
  duration?: number;
  drum?: string;
  instrument?: string;
  instrumentId?: string;
  velocity?: number;
  vel?: number;
};

const synthesizeDrumTrackFromLegacyNotes = (
  legacyNotes: LegacyNoteCandidate[],
  sectionId: string,
  config: DrumGenerationConfig,
  fallbackBpm: number,
): DrumTrackForDCSM | null => {
  if (!Array.isArray(legacyNotes) || !legacyNotes.length) {
    return null;
  }

  const ticksPerBeat = 960;
  const beatsPerBar = config.timeSignature?.[0] ?? 4;
  const measureCount = Math.max(1, config.endMeasure - config.startMeasure + 1);
  const baseTempos = config.tempos && config.tempos.length ? config.tempos : [];
  const measureTempos = Array.from({ length: measureCount }).map((_, idx) => {
    const tempo = baseTempos[idx] ?? baseTempos[baseTempos.length - 1] ?? fallbackBpm;
    return tempo > 0 ? tempo : fallbackBpm;
  });
  const measureDurations = measureTempos.map((tempo) => (60 / tempo) * beatsPerBar);
  const measureBoundaries: number[] = [0];
  for (const duration of measureDurations) {
    measureBoundaries.push(measureBoundaries[measureBoundaries.length - 1] + duration);
  }

  const locateMeasurePosition = (relativeTime: number) => {
    const clampedTime = Math.max(0, relativeTime);
    let measureIndex = measureDurations.length - 1;
    for (let i = 0; i < measureDurations.length; i += 1) {
      if (clampedTime < measureBoundaries[i + 1] - 1e-6) {
        measureIndex = i;
        break;
      }
    }
    const tempo = measureTempos[Math.min(measureIndex, measureTempos.length - 1)] || fallbackBpm;
    const secondsPerBeat = 60 / Math.max(tempo, 1);
    const offsetWithinMeasure = clampedTime - measureBoundaries[measureIndex];
    const beatsIntoMeasure = Math.max(0, offsetWithinMeasure / secondsPerBeat);
    const tickInBar = Math.round(beatsIntoMeasure * ticksPerBeat);
    return {
      barIndex: config.startMeasure + measureIndex,
      tickInBar,
      secondsPerBeat,
    };
  };

  const drumNotes: DrumNoteEvent[] = legacyNotes.map((raw, idx) => {
    const lane = mapInstrumentToLane(raw?.instrument || raw?.instrumentId || raw?.drum);
    const instrumentId = laneToInstrumentId(lane);
    const midiPitch = DRUM_INSTRUMENT_MIDI_MAP[instrumentId] ?? DRUM_INSTRUMENT_MIDI_MAP.snare_center;
    const relativeTime = typeof raw?.time === "number" ? raw.time : 0;
    const durationSec = typeof raw?.length === "number"
      ? raw.length
      : typeof raw?.duration === "number"
        ? raw.duration
        : 0.25;
    const { barIndex, tickInBar, secondsPerBeat } = locateMeasurePosition(relativeTime);
    const tickLength = Math.max(
      Math.round((durationSec / secondsPerBeat) * ticksPerBeat),
      ticksPerBeat / 16,
    );
    const velocitySource = typeof raw?.velocity === "number"
      ? raw.velocity
      : typeof raw?.vel === "number"
        ? raw.vel
        : 0.85;
    const normalizedVelocity = normalizeVelocity(velocitySource);
    const velocity = Math.max(1, Math.min(127, Math.round(normalizedVelocity * 127)));

    return {
      id: raw?.id || `legacy-${sectionId}-${idx}-${Date.now()}`,
      barIndex,
      tickInBar,
      tickLength,
      channel: 9,
      midiPitch,
      velocity,
      instrumentId,
      limbId: inferLimbFromLane(lane) ?? undefined,
      isGhost: velocity <= 45,
      isAccent: velocity >= 110,
      isFlam: false,
      isDrag: false,
    };
  });

  return {
    track_id: `legacy-${sectionId}-${Date.now()}`,
    style_id: config.style || "legacy",
    resolution_ppq: ticksPerBeat,
    notes: drumNotes,
    performance_spec: {
      styleId: config.style || "legacy",
      globalFeel: "straight",
      quantizationBase: "16th",
      phrases: [],
    },
  };
};

const hydrateLegacyNote = (raw: any, idx: number, defaultDuration: number, prefix: string): PianoRollNote => {
  const durationValue =
    typeof raw?.duration === "number"
      ? raw.duration
      : typeof raw?.length === "number"
        ? raw.length
        : defaultDuration;

  const lane = raw?.lane || mapInstrumentToLane(raw?.instrumentId || raw?.drum);
  const limbId = coerceSupportedLimb(raw?.limbId) ?? inferLimbFromLane(lane);

  return {
    id: raw?.id || `${prefix}-${Date.now()}-${idx}`,
    time: typeof raw?.time === "number" ? raw.time : 0,
    duration: durationValue,
    lane,
    vel: normalizeVelocity(raw?.vel ?? raw?.velocity),
    aspect: raw?.aspect,
    phraseMarker: raw?.phraseMarker,
    rudimentId: raw?.rudimentId,
    limbId,
  };
};

const TRACK_COLOR_POOL = ["#60a5fa", "#22d3ee", "#a78bfa", "#34d399", "#f59e0b", "#ef4444"] as const;
const pickTrackColor = (count: number) => TRACK_COLOR_POOL[count % TRACK_COLOR_POOL.length];

type WaveformPayload = {
  key?: string;
  peaks?: number[];
  peaksL?: number[];
  peaksR?: number[];
  sr?: number;
  duration?: number;
};

const SUPPORTED_NOTE_LIMBS: readonly LimbId[] = ["RH", "LH", "RF", "LF"];
const coerceSupportedLimb = (value?: DrumTrackLimbId | LimbId | null): LimbId | null => {
  if (!value) {
    return null;
  }
  return SUPPORTED_NOTE_LIMBS.includes(value as LimbId) ? (value as LimbId) : null;
};

type NoteAspectValue = NonNullable<PianoRollNote["aspect"]>;
const NOTE_ASPECT_VALUES: readonly NoteAspectValue[] = ["groove", "accent", "fill"] as const;
const coerceNoteAspect = (value?: string | null): NoteAspectValue | undefined => {
  if (!value) {
    return undefined;
  }
  const normalized = value.trim().toLowerCase();
  return NOTE_ASPECT_VALUES.find((candidate) => candidate === normalized) ?? undefined;
};

const summarizeDrumTrack = (track: DrumTrackForDCSM) => {
  const notes = Array.isArray(track?.notes) ? track.notes : [];
  if (!notes.length) {
    return {
      noteCount: 0,
      minBar: null as number | null,
      maxBar: null as number | null,
      instruments: [] as string[],
    };
  }

  let minBar = Number.POSITIVE_INFINITY;
  let maxBar = Number.NEGATIVE_INFINITY;
  const instruments = new Set<string>();

  for (const note of notes) {
    const barIndex = Number(note?.barIndex ?? 0);
    if (Number.isFinite(barIndex)) {
      if (barIndex < minBar) minBar = barIndex;
      if (barIndex > maxBar) maxBar = barIndex;
    }
    if (note?.instrumentId) {
      instruments.add(String(note.instrumentId));
    }
  }

  return {
    noteCount: notes.length,
    minBar: Number.isFinite(minBar) ? minBar : null,
    maxBar: Number.isFinite(maxBar) ? maxBar : null,
    instruments: Array.from(instruments),
  };
};

const normalizePeakSeries = (input: any): number[] => {
  if (!input) return [];

  const coerceSample = (value: any): number => {
    if (typeof value === "number") {
      return Number.isFinite(value) ? value : 0;
    }
    if (typeof value === "string") {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    if (Array.isArray(value)) {
      let maxAbs = 0;
      for (const entry of value) {
        maxAbs = Math.max(maxAbs, Math.abs(coerceSample(entry)));
      }
      return maxAbs;
    }
    if (value && typeof value === "object") {
      const numericFields = ["max", "min", "rms", "peak", "value"];
      let candidate = 0;
      for (const field of numericFields) {
        const sample = (value as Record<string, unknown>)[field];
        if (typeof sample === "number" && Number.isFinite(sample)) {
          candidate = Math.max(candidate, Math.abs(sample));
        }
      }
      return candidate;
    }
    return 0;
  };

  let samples: number[] = [];
  if (Array.isArray(input)) {
    samples = input.map(coerceSample);
  } else if (ArrayBuffer.isView(input)) {
    samples = Array.from(input as unknown as ArrayLike<number>).map(coerceSample);
  } else if (input instanceof ArrayBuffer) {
    samples = Array.from(new Float32Array(input));
  } else if (typeof input === "object" && Array.isArray((input as any).data)) {
    samples = (input as any).data.map(coerceSample);
  }

  if (!samples.length) {
    return [];
  }

  let maxAbs = 0;
  for (const value of samples) {
    if (!Number.isFinite(value)) continue;
    const abs = Math.abs(value);
    if (abs > maxAbs) {
      maxAbs = abs;
    }
  }

  if (!Number.isFinite(maxAbs) || maxAbs <= 0) {
    return samples.map(() => 0);
  }

  const scale = 1 / maxAbs;
  return samples.map((value) => {
    if (!Number.isFinite(value)) {
      return 0;
    }
    const scaled = value * scale;
    if (scaled > 1) return 1;
    if (scaled < -1) return -1;
    return scaled;
  });
};

const clampSignedUnit = (value: number): number => {
  if (!Number.isFinite(value)) return 0;
  if (value > 1) return 1;
  if (value < -1) return -1;
  return value;
};

const collectNumericCandidates = (value: any, target: number[]) => {
  if (typeof value === "number" && Number.isFinite(value)) {
    target.push(value);
    return;
  }
  if (Array.isArray(value)) {
    value.forEach((entry) => collectNumericCandidates(entry, target));
    return;
  }
  if (ArrayBuffer.isView(value)) {
    const view = value as unknown as ArrayLike<number>;
    for (let i = 0; i < view.length; i++) {
      const entry = view[i];
      if (typeof entry === "number" && Number.isFinite(entry)) {
        target.push(entry);
      }
    }
    return;
  }
  if (value instanceof ArrayBuffer) {
    collectNumericCandidates(new Float32Array(value), target);
    return;
  }
  if (value && typeof value === "object") {
    const numericFields = [
      "min",
      "max",
      "low",
      "high",
      "neg",
      "pos",
      "negative",
      "positive",
      "peak",
      "value",
      "rms",
    ];
    numericFields.forEach((field) => {
      const candidate = (value as Record<string, unknown>)[field];
      if (typeof candidate === "number" && Number.isFinite(candidate)) {
        target.push(candidate);
      }
    });
  }
};

const extractExtent = (value: any): WaveformExtent => {
  const candidates: number[] = [];
  collectNumericCandidates(value, candidates);
  if (!candidates.length) {
    return { min: 0, max: 0 };
  }

  let localMin = Infinity;
  let localMax = -Infinity;
  let hasPositive = false;
  let hasNegative = false;

  candidates.forEach((candidate) => {
    if (candidate < localMin) localMin = candidate;
    if (candidate > localMax) localMax = candidate;
    if (candidate >= 0) hasPositive = true;
    if (candidate <= 0) hasNegative = true;
  });

  if (!hasNegative && hasPositive) {
    const amplitude = Math.max(0, localMax);
    return { min: -amplitude, max: amplitude };
  }

  if (!hasPositive && hasNegative) {
    const amplitude = Math.abs(localMin);
    return { min: -amplitude, max: amplitude };
  }

  if (!Number.isFinite(localMin) || !Number.isFinite(localMax)) {
    return { min: 0, max: 0 };
  }

  if (localMin === localMax) {
    const amplitude = Math.abs(localMax);
    return { min: -amplitude, max: amplitude };
  }

  return { min: localMin, max: localMax };
};

const normalizePeakExtents = (input: any): WaveformExtent[] => {
  if (!input || !Array.isArray(input)) {
    return [];
  }

  const extents = input.map((value) => extractExtent(value));
  let maxAbs = 0;
  for (const extent of extents) {
    if (Number.isFinite(extent.max)) {
      maxAbs = Math.max(maxAbs, Math.abs(extent.max));
    }
    if (Number.isFinite(extent.min)) {
      maxAbs = Math.max(maxAbs, Math.abs(extent.min));
    }
  }

  if (maxAbs <= 0) {
    return extents.map(() => ({ min: 0, max: 0 }));
  }

  const scale = 1 / maxAbs;
  return extents.map((extent) => ({
    min: clampSignedUnit(extent.min * scale),
    max: clampSignedUnit(extent.max * scale),
  }));
};

const waveformHasAudio = (wf?: WaveformPayload | null) => {
  if (!wf) return false;
  const peaks = normalizePeakSeries(wf.peaks);
  return peaks.length > 0 && typeof wf.sr === "number";
};

const audioDurationCache = new Map<string, number>();

const buildAudioUrlCandidates = (key: string): string[] => {
  const base = resolveApiBaseNormalized();
  const relative = `/files/audio?key=${encodeURIComponent(key)}`;
  return base ? [relative, `${base}${relative}`] : [relative];
};

const withCacheBuster = (url: string) => `${url}${url.includes("?") ? "&" : "?"}cb=${Date.now()}`;

async function fetchAudioDurationSeconds(key: string): Promise<number | null> {
  if (audioDurationCache.has(key)) {
    return audioDurationCache.get(key)!;
  }
  if (typeof window === "undefined" || typeof document === "undefined") {
    return null;
  }

  const candidates = buildAudioUrlCandidates(key);
  for (const candidate of candidates) {
    const duration = await new Promise<number | null>((resolve) => {
      const audioEl = document.createElement("audio");
      audioEl.preload = "metadata";
      const cleanup = () => {
        audioEl.removeAttribute("src");
        audioEl.load();
        audioEl.remove();
      };
      audioEl.onloadedmetadata = () => {
        const detected = Number.isFinite(audioEl.duration) ? audioEl.duration : null;
        cleanup();
        resolve(detected);
      };
      audioEl.onerror = () => {
        cleanup();
        resolve(null);
      };
      audioEl.src = withCacheBuster(candidate);
    });
    if (typeof duration === "number" && duration > 0.2) {
      audioDurationCache.set(key, duration);
      return duration;
    }
  }
  return null;
}

async function fetchWaveformData(key: string): Promise<WaveformPayload> {
  const base = resolveApiBaseNormalized();
  const query = `?key=${encodeURIComponent(key)}`;
  const relativePaths = ["/waveform", "/files/waveform"];
  const candidates = new Set<string>();

  relativePaths.forEach((path) => {
    candidates.add(`${path}${query}`);
    if (base) {
      candidates.add(`${base}${path}${query}`);
    }
  });

  let lastError: Error | null = null;

  for (const url of Array.from(candidates)) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        return await response.json();
      }
      const body = await response.text().catch(() => "");
      lastError = new Error(`Waveform fetch failed (${response.status}): ${body.slice(0, 120)}`);
    } catch (err: any) {
      lastError = err instanceof Error ? err : new Error(String(err));
    }
  }

  throw lastError ?? new Error("Unable to load waveform data");
}

async function buildTrackFromWaveform({
  key,
  name,
  color,
  initialWaveform,
  preferFreshWaveform = false,
}: {
  key: string;
  name: string;
  color: string;
  initialWaveform?: WaveformPayload | null;
  preferFreshWaveform?: boolean;
}): Promise<UploadedTrack> {
  let waveform: WaveformPayload | undefined | null = initialWaveform;

  const shouldForceRefresh = preferFreshWaveform || !waveformHasAudio(waveform);
  if (shouldForceRefresh) {
    try {
      const refreshed = await fetchWaveformData(key);
      if (waveformHasAudio(refreshed)) {
        waveform = refreshed;
      }
    } catch (err) {
      if (!waveformHasAudio(waveform)) {
        throw err;
      }
      console.warn('Waveform refresh failed, using placeholder data instead:', err);
    }
  }

  let peaks = normalizePeakSeries(waveform?.peaks);
  const peaksL = normalizePeakSeries(waveform?.peaksL);
  const peaksR = normalizePeakSeries(waveform?.peaksR);
  const waveformExtents = normalizePeakExtents(waveform?.peaks);
  const waveformExtentsL = normalizePeakExtents(waveform?.peaksL);
  const waveformExtentsR = normalizePeakExtents(waveform?.peaksR);
  if (!peaks.length && peaksL.length) {
    peaks = peaksL;
  }
  const sr = typeof waveform?.sr === "number" ? waveform!.sr : 44100;
  const durationFromBackend = typeof waveform?.duration === "number" ? waveform!.duration : undefined;
  const computedSeconds = peaks.length > 0 ? peaks.length / sr : undefined;
  let seconds = Math.max(1, durationFromBackend ?? computedSeconds ?? 1);

  if (seconds <= 5) {
    try {
      const detectedDuration = await fetchAudioDurationSeconds(key);
      if (typeof detectedDuration === "number" && detectedDuration > seconds + 0.25) {
        seconds = detectedDuration;
      }
    } catch (durationErr) {
      console.warn("Audio duration probe failed", durationErr);
    }
  }

  const hydrated: UploadedTrack = {
    key,
    peaks,
    sr,
    seconds,
    color,
    name,
    waveformExtents: waveformExtents.length ? waveformExtents : undefined,
  };

  if (peaksL.length && peaksR.length) {
    hydrated.peaksL = peaksL;
    hydrated.peaksR = peaksR;
  }

  if (waveformExtentsL.length && waveformExtentsR.length) {
    hydrated.waveformExtentsL = waveformExtentsL;
    hydrated.waveformExtentsR = waveformExtentsR;
  }

  return hydrated;
}

function secToBarsBeats(sec: number, bpm: number, [num, den]: [number, number]) {
  const secPerBeat = (60 / bpm) * (4 / den);
  const secPerBar = secPerBeat * num;
  const bar = Math.floor(sec / secPerBar) + 1;
  const beat = Math.floor((sec % secPerBar) / secPerBeat) + 1;
  const frac = ((sec % secPerBeat) / secPerBeat);
  return `${bar}.${beat}${frac >= 0.5 ? "+" : ""}`;
}

// Convert section to measure range for drum builder
function sectionToMeasureRange(
  section: Section,
  bpm: number,
  defaultTimeSig: [number, number],
  songMap?: SongMapSummary | null,
  tempoFlattenToleranceBpm: number = 2.0,
  tempoMode: "lock" | "follow" = "follow",
): MeasureRange {
  const resolvedTimeSig = section.timeSignature || songMap?.meter || defaultTimeSig;
  const beatsPerMeasure = resolvedTimeSig[0];
  const hasBarAnchors =
    typeof section.startBarIndex === "number" && typeof section.endBarIndex === "number";

  let startMeasure = 0;
  let measureCount = 1;

  const beatTimes = Array.isArray(songMap?.beatTimes) ? songMap!.beatTimes! : [];

  const nearestBeatIndex = (t: number) => {
    if (!beatTimes.length) return null;
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
    return Math.abs(beatTimes[idx] - t) < Math.abs(beatTimes[prev] - t) ? idx : prev;
  };

  if (hasBarAnchors) {
    startMeasure = Math.max(0, section.startBarIndex!);
    const inferredCount = section.barCount ?? section.endBarIndex! - section.startBarIndex! + 1;
    measureCount = Math.max(1, inferredCount);

    if (beatTimes.length) {
      const beatsPerBar = beatsPerMeasure;
      const anchorStartBeatIndex = Math.max(0, startMeasure * beatsPerBar);
      const anchorEndBeatIndex = Math.max(0, (startMeasure + measureCount) * beatsPerBar);
      const anchoredStartTime =
        anchorStartBeatIndex < beatTimes.length ? beatTimes[anchorStartBeatIndex] ?? null : null;
      const anchoredEndTime =
        anchorEndBeatIndex < beatTimes.length ? beatTimes[anchorEndBeatIndex] ?? null : null;

      const tempoForSection = section.tempo || bpm || 120;
      const secPerBeat = 60 / Math.max(1, tempoForSection);
      const secPerBar = secPerBeat * beatsPerBar;
      const tolerance = Math.max(2, secPerBar * 2);

      const startMismatch =
        typeof anchoredStartTime === "number" && Number.isFinite(anchoredStartTime)
          ? Math.abs(anchoredStartTime - section.start) > tolerance
          : false;
      const endMismatch =
        typeof anchoredEndTime === "number" && Number.isFinite(anchoredEndTime)
          ? Math.abs(anchoredEndTime - section.end) > tolerance
          : false;

      if (startMismatch || endMismatch) {
        const startBeatIdx = nearestBeatIndex(section.start);
        const endBeatIdx = nearestBeatIndex(section.end);
        if (startBeatIdx !== null && endBeatIdx !== null) {
          const startBar = Math.floor(startBeatIdx / beatsPerBar);
          const endBar = Math.max(startBar, Math.floor(endBeatIdx / beatsPerBar));
          startMeasure = Math.max(0, startBar);
          measureCount = Math.max(1, endBar - startMeasure + 1);
        }
      }
    }
  } else {
    const tempoForSection = section.tempo || bpm;
    const secPerBeat = 60 / Math.max(1, tempoForSection);
    const secPerMeasure = secPerBeat * beatsPerMeasure;
    startMeasure = Math.floor(section.start / secPerMeasure);
    const rawEndMeasure = Math.ceil(section.end / secPerMeasure);
    measureCount = Math.max(1, rawEndMeasure - startMeasure);
  }

  let tempos: number[] = [];
  if (songMap?.bars?.length && typeof section.startBarIndex === "number") {
    const sliceStart = Math.max(0, section.startBarIndex);
    const sliceEndExclusive = Math.min(
      songMap.bars.length,
      typeof section.endBarIndex === "number"
        ? section.endBarIndex + 1
        : sliceStart + measureCount,
    );
    tempos = songMap.bars.slice(sliceStart, sliceEndExclusive).map((bar) => {
      const fallback = section.tempo || bpm;
      return typeof bar?.tempo_bpm === "number" && bar.tempo_bpm > 0 ? bar.tempo_bpm : fallback;
    });

    if (tempos.length && !section.tempoLocked) {
      const clean = tempos.filter((t) => typeof t === "number" && Number.isFinite(t) && t > 0);
      if (clean.length >= 2) {
        const minT = Math.min(...clean);
        const maxT = Math.max(...clean);
        const range = maxT - minT;
        const avg = clean.reduce((a, b) => a + b, 0) / clean.length;
        const rounded = Math.round(avg * 10) / 10;

        const RANGE_TOL_BPM = Math.max(0, Number(tempoFlattenToleranceBpm) || 0);
        if (Number.isFinite(range) && range > RANGE_TOL_BPM) {
          tempos = Array(tempos.length).fill(rounded);
        }
      }
    }
    if (tempos.length) {
      measureCount = tempos.length;
    }
  }

  if (!tempos.length) {
    const tempo = section.tempo || bpm;
    tempos = Array(measureCount).fill(tempo);
  }

  if (tempoMode === "lock") {
    const clean = tempos.filter((t) => typeof t === "number" && Number.isFinite(t) && t > 0);
    const base = clean.length
      ? Math.round((clean.reduce((a, b) => a + b, 0) / clean.length) * 10) / 10
      : (section.tempo || bpm);
    tempos = Array(measureCount).fill(base);
  }

  const endMeasure = startMeasure + measureCount - 1;
  const avgTempo = tempos.reduce((sum, value) => sum + value, 0) / tempos.length;

  let startTime = section.start;
  let endTime = section.end;
  if (hasBarAnchors && beatTimes.length) {
    const beatsPerBar = beatsPerMeasure;
    const startBeatIndex = Math.max(0, startMeasure * beatsPerBar);
    const endBeatIndex = Math.max(0, (endMeasure + 1) * beatsPerBar);
    if (startBeatIndex < beatTimes.length) {
      startTime = beatTimes[startBeatIndex] ?? startTime;
    }
    if (endBeatIndex < beatTimes.length) {
      endTime = beatTimes[endBeatIndex] ?? endTime;
    } else if (beatTimes.length) {
      endTime = Math.max(endTime, beatTimes[beatTimes.length - 1] ?? endTime);
    }
  }

  return {
    sectionId: section.id,
    sectionLabel: section.label ? section.label.charAt(0).toUpperCase() + section.label.slice(1) : "Section",
    startMeasure,
    endMeasure,
    measureCount,
    tempos,
    avgTempo,
    timeSignature: resolvedTimeSig,
    startTime,
    endTime,
  };
}

function pickFirstAvailable<T = unknown>(source: Record<string, any>, keys: string[], fallback?: T) {
  for (const key of keys) {
    if (source && Object.prototype.hasOwnProperty.call(source, key)) {
      const value = source[key];
      if (value !== undefined && value !== null) {
        return value as T;
      }
    }
  }
  return fallback as T;
}

function readNoteNumber(source: Record<string, any>, keys: string[], fallback: number) {
  const raw = pickFirstAvailable(source, keys);
  const num = typeof raw === "string" ? Number(raw) : raw;
  return Number.isFinite(num) ? Number(num) : fallback;
}

function readNoteString(source: Record<string, any>, keys: string[], fallback?: string | null) {
  const raw = pickFirstAvailable<string>(source, keys);
  if (typeof raw === "string" && raw.trim().length) {
    return raw;
  }
  return fallback ?? null;
}

export default function WebDAWApp() {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [tracks, setTracks] = useState<UploadedTrack[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [notes, setNotes] = useState<PianoRollNote[]>([]);
  const [sectionDrumTracks, setSectionDrumTracks] = useState<Record<string, DrumTrackForDCSM>>({});
  const [sectionGrooveMaps, setSectionGrooveMaps] = useState<Record<string, GrooveWeightMap | undefined>>({});
  const [sectionPlacementContexts, setSectionPlacementContexts] = useState<Record<string, DrumTrackPlacementContext>>({});
  const [sectionNoteIds, setSectionNoteIds] = useState<Record<string, string[]>>({});
  const sectionNoteIdsRef = useRef<Record<string, string[]>>({});
  const pianoRollScrollRef = useRef<HTMLDivElement | null>(null);
  const timelineScrollRef = useRef<HTMLDivElement | null>(null);
  const scrollSyncStateRef = useRef<{ isSyncing: boolean }>({ isSyncing: false });
  const lastSectionSyncSignatureRef = useRef<string | null>(null);
  const loggedTrackSamplesRef = useRef<Set<string>>(new Set());
  const [drumTrackId, setDrumTrackId] = useState<string | null>(null);
  const [drumClipId, setDrumClipId] = useState<string | null>(null);
  const [debugDrumGen, setDebugDrumGen] = useState<DrumGenerationDebugSnapshot | null>(null);
  const [debugMode, setDebugMode] = useState(false);

  const midiSong = useMidi((state) => state.song);
  const addMidiTrack = useMidi((state) => state.addTrack);
  const addMidiClip = useMidi((state) => state.addClip);
  const updateMidiNotes = useMidi((state) => state.updateNotes);
  const getMidiClip = useMidi((state) => state.getClip);
  const updateMidiClip = useMidi((state) => state.updateClip);

  useEffect(() => {
    sectionNoteIdsRef.current = sectionNoteIds;
  }, [sectionNoteIds]);

  const getMaxScroll = useCallback((el: HTMLElement) => Math.max(0, el.scrollWidth - el.clientWidth), []);

  const setScrollRatio = useCallback(
    (ratio: number, source?: HTMLElement | null) => {
      const timelineEl = timelineScrollRef.current;
      const pianoEl = pianoRollScrollRef.current;
      const targets = [timelineEl, pianoEl].filter((el): el is HTMLDivElement => Boolean(el));
      if (!targets.length) return;

      const clamped = Math.min(1, Math.max(0, Number.isFinite(ratio) ? ratio : 0));
      scrollSyncStateRef.current.isSyncing = true;
      targets.forEach((el) => {
        if (source && el === source) return;
        const max = getMaxScroll(el);
        const nextLeft = max * clamped;
        if (Math.abs(el.scrollLeft - nextLeft) > 0.5) {
          el.scrollLeft = nextLeft;
        }
      });
      window.requestAnimationFrame(() => {
        scrollSyncStateRef.current.isSyncing = false;
      });
    },
    [getMaxScroll],
  );

  const [bpm, setBpm] = useState(120);
  const [timeSig, setTimeSig] = useState<[number, number]>([4, 4]);
  const beatsPerBar = timeSig[0];
  const [playhead, setPlayhead] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [loop, setLoop] = useState({ enabled: false, start: 0, end: 4 });
  const [selectedDrummer, setSelectedDrummer] = useState<Drummer | null>(null);
  const [gridResolution, setGridResolution] = useState<GridResolution>("16th");
  const [gridPixelsPerBeat, setGridPixelsPerBeat] = useState(80);
  const [scrollPercent, setScrollPercent] = useState(0);

  const [tempoFlattenToleranceBpm, setTempoFlattenToleranceBpm] = useState<number>(() => {
    const raw = window.localStorage.getItem("dtk.drumGen.tempoFlattenToleranceBpm");
    const parsed = raw ? Number(raw) : 2.0;
    return Number.isFinite(parsed) && parsed >= 0 ? parsed : 2.0;
  });

  useEffect(() => {
    window.localStorage.setItem(
      "dtk.drumGen.tempoFlattenToleranceBpm",
      String(Number.isFinite(tempoFlattenToleranceBpm) ? tempoFlattenToleranceBpm : 2.0),
    );
  }, [tempoFlattenToleranceBpm]);

  const [drumTempoMode, setDrumTempoMode] = useState<"lock" | "follow">(() => {
    const raw = window.localStorage.getItem("dtk.drumGen.tempoMode");
    return raw === "lock" || raw === "follow" ? raw : "lock";
  });

  useEffect(() => {
    window.localStorage.setItem("dtk.drumGen.tempoMode", drumTempoMode);
  }, [drumTempoMode]);

  const drumEngineRef = useRef<ReturnType<typeof getSharedDrumPlayerEngine> | null>(null);
  const drumLoadedRef = useRef<Record<string, number>>({});
  const activeDrumTrackRef = useRef<DrumTrackForDCSM | null>(null);
  const lastDrumScheduleSecRef = useRef<number>(0);

  const instrumentToChannel = useCallback(
    (instrumentId: DrumInstrumentId | string | undefined | null): DrumPlayerChannelId | null => {
      const id = String(instrumentId || "");
      if (!id) return null;
      if (id === "kick") return "kick";
      if (id.startsWith("snare")) return "snare_top";
      if (id.startsWith("hihat")) return "hat";
      if (id.startsWith("ride")) return "ride";
      if (id.startsWith("tom_high")) return "tom1";
      if (id.startsWith("tom_mid")) return "tom3";
      if (id.startsWith("tom_floor")) return "tom5";
      if (id.startsWith("crash")) return "crash";
      return null;
    },
    [],
  );

  const getAudioUrlForSample = useCallback((sampleId: number) => `/api/drum-samples/${sampleId}/audio`, []);

  const ensureDrumEngineReady = useCallback(async () => {
    const eng = getSharedDrumPlayerEngine();
    drumEngineRef.current = eng;
    await eng.ensureRunning();

    const raw = window.localStorage.getItem("dtk.drumPlayer.channelSampleId");
    let map: Record<string, number> = {};
    try {
      map = raw ? (JSON.parse(raw) as Record<string, number>) : {};
    } catch {
      map = {};
    }

    for (const [ch, sid] of Object.entries(map)) {
      const sampleId = Number(sid);
      if (!Number.isFinite(sampleId)) continue;
      if (drumLoadedRef.current[ch] === sampleId) continue;
      await eng.loadSampleForChannel(ch as DrumPlayerChannelId, getAudioUrlForSample(sampleId));
      drumLoadedRef.current[ch] = sampleId;
    }
  }, [getAudioUrlForSample]);

  const convertTrackToMidiNotes = useCallback(
    (track: DrumTrackForDCSM, placement?: DrumTrackPlacementContext): PianoRollNote[] => {
      if (!track?.notes?.length) {
        return [];
      }
      const sampleKey = track.track_id || track.style_id || `track-${track.notes.length}`;
      if (!loggedTrackSamplesRef.current.has(sampleKey)) {
        loggedTrackSamplesRef.current.add(sampleKey);
        console.log("[MidiDebug] track sample", sampleKey, track.notes.slice(0, 3));
      }
      const tempoEstimate = (placement?.tempos?.[0] ?? bpm) || 120;
      const beatsPerBar = placement?.timeSignature?.[0] ?? timeSig[0];
      const ticksPerBeat = track.resolution_ppq || 960;
      const ticksPerBar = ticksPerBeat * beatsPerBar;
      const secondsPerBeat = 60 / Math.max(1, tempoEstimate);
      const placementStartMeasure = placement?.startMeasure ?? 0;
      const placementBeatsPerBar = placement?.timeSignature?.[0] ?? beatsPerBar;
      const fallbackPlacementTempo = placement?.tempos?.[0] ?? tempoEstimate;
      const providedStartTimeSec =
        typeof placement?.startTimeSec === "number" && Number.isFinite(placement.startTimeSec)
          ? placement.startTimeSec
          : null;
      const derivedStartTimeSec =
        placementStartMeasure > 0 && Number.isFinite(fallbackPlacementTempo) && fallbackPlacementTempo > 0
          ? (placementStartMeasure * 60 * placementBeatsPerBar) / fallbackPlacementTempo
          : 0;
      const startOffsetSec = (() => {
        if (
          providedStartTimeSec !== null &&
          (placementStartMeasure <= 4 || providedStartTimeSec > 0.5)
        ) {
          return providedStartTimeSec;
        }
        if (derivedStartTimeSec > 0) {
          console.info(
            "[MidiDebug] Using derived start time for section",
            placementStartMeasure,
            "bars ->",
            derivedStartTimeSec.toFixed(3),
            "sec",
          );
          return derivedStartTimeSec;
        }
        return providedStartTimeSec ?? 0;
      })();

      let trackMinBar = Number.POSITIVE_INFINITY;
      for (const rawNote of track.notes) {
        const note = rawNote as Record<string, any>;
        const barValue = readNoteNumber(note, ["barIndex", "bar_index", "bar"], 0);
        if (Number.isFinite(barValue) && barValue < trackMinBar) {
          trackMinBar = barValue;
        }
      }
      const usesAbsoluteBars =
        Number.isFinite(trackMinBar) && Number.isFinite(placementStartMeasure)
          ? trackMinBar >= placementStartMeasure - 0.5
          : false;
      const barBase = usesAbsoluteBars ? placementStartMeasure : 0;

      return track.notes.map((rawNote, idx) => {
        const note = rawNote as Record<string, any>;
        const resolvedBar = readNoteNumber(note, ["barIndex", "bar_index", "bar"], 0);
        const relativeBar = Math.max(0, resolvedBar - barBase);
        const tickInBar = readNoteNumber(
          note,
          ["tickInBar", "tick_in_bar", "tick", "tickIndex", "tick_index", "tickOffset", "tick_offset"],
          0,
        );
        const totalTicks = relativeBar * ticksPerBar + Math.max(0, tickInBar);
        const rawRelativeTimeSec = readNoteNumber(
          note,
          [
            "timeSec",
            "time_sec",
            "seconds",
            "second",
            "timeSeconds",
            "time_seconds",
            "relativeTime",
            "relative_time",
          ],
          Number.NaN,
        );
        const rawAbsoluteTimeSec = readNoteNumber(
          note,
          ["absoluteTimeSec", "absTimeSec", "absolute_time_sec", "abs_time_sec"],
          Number.NaN,
        );
        const rawDurationSec = readNoteNumber(
          note,
          [
            "durationSec",
            "duration_sec",
            "durationSeconds",
            "lengthSec",
            "length_sec",
            "secondsLength",
            "seconds_length",
          ],
          Number.NaN,
        );
        const rawEndTimeSec = readNoteNumber(
          note,
          ["endTimeSec", "end_time_sec", "timeEndSec", "time_end_sec"],
          Number.NaN,
        );
        const microTimingMs = readNoteNumber(
          note,
          ["microTimingMs", "micro_timing_ms", "timingOffsetMs", "timing_offset_ms"],
          0,
        );
        const microTimingSec = Number.isFinite(microTimingMs) ? microTimingMs / 1000 : 0;

        const computedTime = startOffsetSec + (totalTicks / ticksPerBeat) * secondsPerBeat;
        const fallbackTime = Number.isFinite(rawAbsoluteTimeSec)
          ? rawAbsoluteTimeSec
          : Number.isFinite(rawRelativeTimeSec)
            ? startOffsetSec + rawRelativeTimeSec
            : Number.NaN;
        const shouldUseFallbackTime =
          Number.isFinite(fallbackTime) &&
          (!Number.isFinite(totalTicks) || (totalTicks === 0 && fallbackTime > computedTime + 1e-4));
        const timeBaseRaw = shouldUseFallbackTime ? fallbackTime : computedTime;
        const timeBase = Number.isFinite(timeBaseRaw) ? timeBaseRaw : startOffsetSec;
        const time = timeBase + microTimingSec;

        const tickLength = readNoteNumber(
          note,
          ["tickLength", "tick_length", "durationTicks", "duration_ticks", "tickLen", "tick_len"],
          ticksPerBeat / 4,
        );
        const computedDuration = Math.max(0, (tickLength / ticksPerBeat) * secondsPerBeat);
        let duration = Math.max(0.03, computedDuration);
        if ((duration <= 0.031 || !Number.isFinite(duration)) && Number.isFinite(rawDurationSec) && rawDurationSec > 0) {
          duration = Math.max(0.03, rawDurationSec);
        } else if ((duration <= 0.031 || !Number.isFinite(duration)) && Number.isFinite(rawEndTimeSec)) {
          const durationBaseline = Number.isFinite(fallbackTime) ? fallbackTime : timeBase;
          const durationFallback = rawEndTimeSec - durationBaseline;
          if (durationFallback > 0) {
            duration = Math.max(0.03, durationFallback);
          }
        }
        const instrumentId = (readNoteString(note, [
          "instrumentId",
          "instrument_id",
          "instrument",
        ], "snare_center") as DrumInstrumentId) ?? "snare_center";
        const laneName = readNoteString(note, ["lane", "drumLane", "lane_id"], undefined);
        const lane = laneName || mapInstrumentToLane(instrumentId);
        const primaryLimb = coerceSupportedLimb(
          (readNoteString(note, ["limbId", "limb_id", "limb"], undefined) as LimbId | null) ?? undefined,
        );
        const inferredLimb = inferLimbFromInstrument(instrumentId) ?? inferLimbFromLane(lane) ?? undefined;
        const limbId = primaryLimb ?? inferredLimb ?? undefined;
        return {
          id: readNoteString(note, ["id", "noteId", "note_id"], undefined) ?? `dcsm-${Date.now()}-${idx}`,
          time,
          duration,
          lane,
          vel: normalizeVelocity(
            readNoteNumber(note, ["velocity", "vel", "midiVelocity", "midi_velocity"], 96),
          ),
          aspect: coerceNoteAspect(readNoteString(note, ["aspect"], undefined)),
          phraseMarker: readNoteString(note, ["phraseMarker", "phrase_marker"], undefined) ?? undefined,
          rudimentId: readNoteString(note, ["rudimentId", "rudiment_id"], undefined) ?? undefined,
          limbId,
        };
      });
    },
    [bpm, timeSig],
  );

  const convertTrackToMidiClipNotes = useCallback(
    (track: DrumTrackForDCSM): MidiClipNote[] => {
      if (!track?.notes?.length) {
        return [];
      }
      const sourceResolution = Number(track.resolution_ppq) > 0 ? Number(track.resolution_ppq) : 960;
      const targetPpq = midiSong.ppq || 480;
      const ratio = targetPpq / sourceResolution;
      const ticksPerBarSource = beatsPerBar * sourceResolution;
      const stamp = Date.now();

      return track.notes.map((rawNote, idx) => {
        const note = rawNote as Record<string, any>;
        const barIndex = readNoteNumber(note, ["barIndex", "bar_index", "bar"], 0);
        const tickInBar = readNoteNumber(
          note,
          ["tickInBar", "tick_in_bar", "tick", "tickIndex", "tick_index", "tickOffset", "tick_offset"],
          0,
        );
        const tickLength = readNoteNumber(
          note,
          ["tickLength", "tick_length", "durationTicks", "duration_ticks", "tickLen", "tick_len"],
          sourceResolution / 4,
        );
        const absoluteSourceTicks = barIndex * ticksPerBarSource + tickInBar;
        const startTick = Math.max(0, Math.round(absoluteSourceTicks * ratio));
        const endTick = startTick + Math.max(1, Math.round(tickLength * ratio));
        const pitch = Math.round(
          readNoteNumber(
            note,
            ["midiPitch", "midi_pitch", "pitch", "note", "midi"],
            DRUM_INSTRUMENT_MIDI_MAP.snare_center,
          ),
        );
        const velocity = Math.max(
          1,
          Math.min(127, Math.round(readNoteNumber(note, ["velocity", "vel", "midiVelocity", "midi_velocity"], 96))),
        );
        return {
          id: readNoteString(note, ["id", "noteId", "note_id"], undefined) || `dcsm-midi-${stamp}-${idx}`,
          t0: startTick,
          t1: endTick,
          pitch,
          vel: velocity,
          chan: Math.max(0, Math.round(readNoteNumber(note, ["channel", "chan", "midiChannel", "midi_channel"], 10))),
        };
      });
    },
    [midiSong.ppq, beatsPerBar],
  );

  const convertLegacyMidiNotesToClip = useCallback(
    (legacyNotes: any[]): MidiClipNote[] => {
      if (!Array.isArray(legacyNotes) || !legacyNotes.length) {
        return [];
      }
      const targetPpq = midiSong.ppq || 480;
      const tempoBpm = midiSong.tempoMap?.[0]?.bpm ?? bpm ?? 120;
      const ticksPerSecond = (tempoBpm / 60) * targetPpq;
      const stamp = Date.now();

      return legacyNotes.map((note, idx) => {
        const startTick = Math.max(0, Math.round(((typeof note?.time === "number" ? note.time : 0) * ticksPerSecond)));
        const durationSec =
          typeof note?.length === "number"
            ? note.length
            : typeof note?.duration === "number"
              ? note.duration
              : 0.25;
        const endTick = startTick + Math.max(1, Math.round(durationSec * ticksPerSecond));
        const pitch = typeof note?.note === "number" ? note.note : DRUM_INSTRUMENT_MIDI_MAP.snare_center;
        const velocity = Math.max(1, Math.min(127, Math.round(typeof note?.velocity === "number" ? note.velocity : 96)));
        return {
          id: note?.id || `legacy-midi-${stamp}-${idx}`,
          t0: startTick,
          t1: endTick,
          pitch,
          vel: velocity,
          chan: Number(note?.chan ?? 10),
        };
      });
    },
    [midiSong.ppq, midiSong.tempoMap, bpm],
  );

  const [grooveSource, setGrooveSource] = useState<string>("pattern");
  const [grooveMode, setGrooveMode] = useState<string>("exact");
  const [styleGroup, setStyleGroup] = useState<string>("rock");
  const [lastEgmdPhraseInfo, setLastEgmdPhraseInfo] = useState<any | null>(null);

  // EGMD clip picker state/effects are declared further below (after arrangementSource)

  const applyTrackToMidiClip = useCallback(
    (track?: DrumTrackForDCSM | null, legacyNotes?: any[] | null, placement?: DrumTrackPlacementContext) => {
      if (!drumTrackId || !drumClipId) {
        return;
      }
      const clip = getMidiClip(drumTrackId, drumClipId);
      if (!clip) {
        return;
      }

      let sectionNotes: MidiClipNote[] = [];
      if (track?.notes?.length) {
        sectionNotes = convertTrackToMidiClipNotes(track);
      } else if (Array.isArray(legacyNotes) && legacyNotes.length) {
        sectionNotes = convertLegacyMidiNotesToClip(legacyNotes);
      }

      if (!sectionNotes.length) {
        return;
      }

      let mergedNotes = sectionNotes;
      if (placement && typeof placement.startMeasure === "number" && typeof placement.endMeasure === "number") {
        const ppq = midiSong.ppq || 480;
        const beatsPerMeasure = placement.timeSignature?.[0] ?? beatsPerBar;
        const ticksPerMeasure = ppq * beatsPerMeasure;
        const rangeStartTick = Math.max(0, Math.round(placement.startMeasure * ticksPerMeasure));
        const rangeEndTick = Math.max(rangeStartTick, Math.round((placement.endMeasure + 1) * ticksPerMeasure));
        const existing = Array.isArray(clip.notes) ? clip.notes : [];
        const preserved = existing.filter((n) => n.t1 <= rangeStartTick || n.t0 >= rangeEndTick);
        mergedNotes = [...preserved, ...sectionNotes].sort((a, b) => a.t0 - b.t0);
      }

      updateMidiNotes(drumTrackId, drumClipId, mergedNotes);
      const clipEndTick = mergedNotes.reduce((max, note) => Math.max(max, note.t1), clip.endTick ?? 0);
      const updates: Partial<MidiClip> = {
        endTick: clipEndTick,
      };
      if (track) {
        updates.dcsmTrack = track;
        updates.disableGrooveShaping = grooveSource === "egmd_phrases" && grooveMode === "exact";
      }
      updateMidiClip(drumTrackId, drumClipId, updates);
    },
    [
      drumTrackId,
      drumClipId,
      getMidiClip,
      convertTrackToMidiClipNotes,
      convertLegacyMidiNotesToClip,
      updateMidiNotes,
      updateMidiClip,
      midiSong.ppq,
      beatsPerBar,
      grooveSource,
      grooveMode,
    ],
  );

  const syncSectionMidiNotes = useCallback(
    (sectionId: string, track: DrumTrackForDCSM, overridePlacement?: DrumTrackPlacementContext) => {
      if (!sectionId || !track?.notes?.length) {
        return;
      }
      const placement = overridePlacement ?? sectionPlacementContexts[sectionId];
      const midiNotes = convertTrackToMidiNotes(track, placement);
      setNotes((prev) => {
        const existingIds = new Set(sectionNoteIdsRef.current[sectionId] ?? []);
        const preserved = existingIds.size ? prev.filter((note) => !existingIds.has(note.id)) : prev;
        return [...preserved, ...midiNotes];
      });
      setSectionNoteIds((prev) => ({
        ...prev,
        [sectionId]: midiNotes.map((note) => note.id),
      }));
    },
    [convertTrackToMidiNotes, sectionPlacementContexts],
  );

  // NEW: Selected sections for generation
  const [selectedSectionIds, setSelectedSectionIds] = useState<Set<string>>(new Set());

  const [songMap, setSongMap] = useState<SongMapSummary | null>(null);

  const drumSectionRegions: DrumSectionRegion[] = useMemo(() => {
    if (!Array.isArray(sections) || !sections.length) return [];
    const regions: DrumSectionRegion[] = [];
    for (const s of sections) {
      try {
        const mr = sectionToMeasureRange(s, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode);
        const label = mr.sectionLabel || "Section";
        regions.push({
          id: mr.sectionId,
          label,
          startBar: mr.startMeasure,
          endBar: mr.endMeasure,
        });
      } catch {
        // ignore
      }
    }
    return regions;
  }, [sections, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode]);

  const [scratchStyle, setScratchStyle] = useState<string>("rock");
  const [scratchArrangement, setScratchArrangement] = useState<Array<{ label: string; bars: number }>>([
    { label: "intro", bars: 4 },
    { label: "verse", bars: 8 },
    { label: "chorus", bars: 8 },
    { label: "bridge", bars: 4 },
    { label: "chorus", bars: 8 },
    { label: "outro", bars: 4 },
  ]);

  const hasSectionSelection = selectedSectionIds.size > 0;
  
  // NEW: Arrangement entry modals
  const [showManualModal, setShowManualModal] = useState(false);
  const [showLookupModal, setShowLookupModal] = useState(false);
  const [showDrumPlayer, setShowDrumPlayer] = useState(false);

  const [midiMapName, setMidiMapName] = useState<string>("Mixosaurus_EZ_Drummer");
  const [lastGeneratedMidiBase64, setLastGeneratedMidiBase64] = useState<string | null>(null);
  const [lastGeneratedMidiLabel, setLastGeneratedMidiLabel] = useState<string | null>(null);
  const [showDrummerPersonaModal, setShowDrummerPersonaModal] = useState(false);
  
  // NEW: Track arrangement source for conflict handling
  const [arrangementSource, setArrangementSource] = useState<string | null>(null);

  const [egmdPhraseOptions, setEgmdPhraseOptions] = useState<
    Array<{
      phrase_id: number;
      midi_path?: string | null;
      audio_path?: string | null;
      tempo_bpm?: number | null;
      meter?: string | null;
    }>
  >([]);
  const [selectedEgmdPhraseId, setSelectedEgmdPhraseId] = useState<number | null>(null);

  const isScratchEntry = tracks.length === 0;
  const isScratchWorkflow = arrangementSource === "scratch" || isScratchEntry;

  useEffect(() => {
    if (!isScratchWorkflow) return;
    // Scratch workflow: always EGMD Exact Clip
    if (grooveSource !== "egmd_phrases") {
      setGrooveSource("egmd_phrases");
    }
    if (grooveMode !== "exact") {
      setGrooveMode("exact");
    }
  }, [isScratchWorkflow, grooveSource, grooveMode]);

  useEffect(() => {
    if (grooveSource !== "egmd_phrases") {
      setEgmdPhraseOptions([]);
      setSelectedEgmdPhraseId(null);
      return;
    }
    const controller = new AbortController();
    const apiBase = resolveApiBaseNormalized();
    const meter = `${timeSig[0]}/${timeSig[1]}`;
    const tempo = Number.isFinite(bpm) && bpm > 0 ? bpm : 120;
    const url = `${apiBase}/api/egmd/phrases?style_group=${encodeURIComponent(styleGroup)}&meter=${encodeURIComponent(meter)}&tempo_bpm=${encodeURIComponent(String(tempo))}&limit=50`;
    (async () => {
      try {
        const res = await fetch(url, { signal: controller.signal });
        if (!res.ok) {
          setEgmdPhraseOptions([]);
          return;
        }
        const json = await res.json();
        const items = Array.isArray(json?.items) ? json.items : [];
        setEgmdPhraseOptions(items);
        // Keep the current selection if it still exists; otherwise reset to Best Match.
        if (
          selectedEgmdPhraseId !== null &&
          !items.some((it: any) => Number(it?.phrase_id) === selectedEgmdPhraseId)
        ) {
          setSelectedEgmdPhraseId(null);
        }
      } catch {
        // ignore
      }
    })();
    return () => controller.abort();
  }, [grooveSource, styleGroup, bpm, timeSig, selectedEgmdPhraseId]);

  // NEW: Drum Builder - measure range selection
  const [selectedMeasureRange, setSelectedMeasureRange] = useState<MeasureRange | null>(null);
  const buildScratchSong = useCallback(() => {
    const resolvedBpm = Number.isFinite(bpm) && bpm > 0 ? bpm : 120;
    const beatsPerBarLocal = timeSig[0] || 4;
    const secondsPerBeat = 60 / resolvedBpm;
    const secondsPerBar = secondsPerBeat * beatsPerBarLocal;

    const cleaned = scratchArrangement
      .map((row) => ({
        label: (row.label || "section").toLowerCase(),
        bars: Math.max(1, Math.floor(row.bars || 1)),
      }))
      .filter((row) => row.bars > 0);

    let t = 0;
    let barCursor = 0;
    const nextSections: Section[] = cleaned.map((row, idx) => {
      const dur = row.bars * secondsPerBar;
      const start = t;
      const end = t + dur;
      const startBarIndex = barCursor;
      const endBarIndex = barCursor + row.bars - 1;
      t = end;
      barCursor = endBarIndex + 1;
      return {
        id: `scratch-${idx}-${Date.now()}`,
        start,
        end,
        density: 0.7,
        fillIn: idx > 0,
        fillOut: idx < cleaned.length - 1,
        label: row.label,
        confidence: 1.0,
        tempo: resolvedBpm,
        startBarIndex,
        endBarIndex,
        barCount: row.bars,
        timeSignature: timeSig,
      };
    });

    const totalBars = Math.max(1, barCursor);
    const bars = Array.from({ length: totalBars }).map(() => ({ tempo_bpm: resolvedBpm }));
    const beatTimes = Array.from({ length: totalBars * beatsPerBarLocal + 1 }).map((_, i) => i * secondsPerBeat);

    setSongMap({
      duration: totalBars * secondsPerBar,
      globalBpmEstimate: resolvedBpm,
      meter: timeSig,
      bars,
      sections: nextSections,
      beatTimes,
      source: "scratch",
      title: "Untitled",
      artist: "",
    });

    setArrangementSource("scratch");

    setSections(nextSections);
    setSelectedSectionIds(new Set());
    setSelectedMeasureRange(null);
    if (nextSections.length) {
      const first = nextSections[0];
      setSelectedSectionIds(new Set([first.id]));
      setSelectedMeasureRange(
        sectionToMeasureRange(first, resolvedBpm, timeSig, {
          meter: timeSig,
          bars,
          beatTimes,
        }, tempoFlattenToleranceBpm, drumTempoMode),
      );
    }
  }, [bpm, scratchArrangement, timeSig]);

  const [generatingDrums, setGeneratingDrums] = useState(false);
  const [bulkGenerating, setBulkGenerating] = useState(false);
  const [fullSongStatus, setFullSongStatus] = useState<
    { type: 'progress' | 'success' | 'error'; message: string } | null
  >(null);
  const [fullSongProgress, setFullSongProgress] = useState<{ completed: number; total: number }>({
    completed: 0,
    total: 0,
  });
  const sectionTrackIds = useMemo(() => Object.keys(sectionDrumTracks ?? {}), [sectionDrumTracks]);

  const fullSongDrumTrack = useMemo(() => {
    const explicit = sectionDrumTracks?.["full-song"] ?? null;
    if (explicit && Array.isArray(explicit.notes) && explicit.notes.length) {
      return explicit;
    }

    const keys = Object.keys(sectionDrumTracks ?? {}).filter((k) => k !== "__global__" && k !== "full-song");
    if (!keys.length) {
      return null;
    }
    const tracksToMerge = keys
      .map((k) => sectionDrumTracks[k])
      .filter((t): t is DrumTrackForDCSM => Boolean(t && Array.isArray(t.notes) && t.notes.length));
    if (!tracksToMerge.length) {
      return null;
    }

    const base = tracksToMerge[0];
    const performanceSpec =
      base.performance_spec ??
      ({
        styleId: base.style_id || "unknown",
        globalFeel: "straight",
        quantizationBase: "16th",
        phrases: [],
      } as any);

    return {
      track_id: "full-song",
      style_id: base.style_id || "unknown",
      resolution_ppq: typeof base.resolution_ppq === "number" ? base.resolution_ppq : 960,
      notes: tracksToMerge.flatMap((t) => t.notes ?? []),
      performance_spec: performanceSpec,
    } satisfies DrumTrackForDCSM;
  }, [sectionDrumTracks]);

  useEffect(() => {
    activeDrumTrackRef.current = fullSongDrumTrack;
  }, [fullSongDrumTrack]);

  const scheduleDrumsBetween = useCallback(
    async (fromSec: number, toSec: number) => {
      const eng = drumEngineRef.current;
      const track = activeDrumTrackRef.current;
      if (!eng || !track) return;
      if (!Array.isArray(track.notes) || track.notes.length === 0) return;
      if (!(bpm > 0)) return;

      const beatsPerBarLocal = (timeSig?.[0] ?? 4) || 4;
      const ticksPerBeat = track.resolution_ppq || 960;
      const ticksPerBarLocal = ticksPerBeat * beatsPerBarLocal;

      for (const n of track.notes) {
        const bar = n.barIndex ?? 0;
        const tick = n.tickInBar ?? 0;
        const totalTicks = bar * ticksPerBarLocal + tick;
        const beats = totalTicks / ticksPerBeat;
        const tSec = (beats * 60) / bpm;
        if (tSec < fromSec || tSec >= toSec) continue;
        const ch = instrumentToChannel(n.instrumentId as any);
        if (!ch) continue;
        eng.playChannelOneShot(ch, { gain: Math.max(0.2, Math.min(1.5, (n.velocity ?? 100) / 100)) });
      }
    },
    [bpm, instrumentToChannel, timeSig],
  );
  const activeSectionId =
    selectedMeasureRange?.sectionId === "full-song"
      ? "full-song"
      : selectedMeasureRange?.sectionId && sectionDrumTracks[selectedMeasureRange.sectionId]
        ? selectedMeasureRange.sectionId
        : sectionTrackIds.length > 0
          ? sectionTrackIds[0]
          : null;
  const activeDrumTrack =
    activeSectionId === "full-song"
      ? fullSongDrumTrack
      : activeSectionId && sectionDrumTracks[activeSectionId]
        ? sectionDrumTracks[activeSectionId]
        : null;
  const activeGrooveMap =
    activeSectionId && sectionGrooveMaps[activeSectionId]
      ? sectionGrooveMaps[activeSectionId]
      : undefined;
  const fallbackPlacementContext = useMemo(() => {
    if (!selectedMeasureRange) {
      return undefined;
    }
    return {
      startMeasure: selectedMeasureRange.startMeasure,
      endMeasure: selectedMeasureRange.endMeasure,
      tempos: selectedMeasureRange.tempos,
      timeSignature: selectedMeasureRange.timeSignature,
      startTimeSec: selectedMeasureRange.startTime,
    } satisfies DrumTrackPlacementContext;
  }, [selectedMeasureRange]);

  const activePlacementContext = useMemo(() => {
    if (!activeSectionId) {
      return fallbackPlacementContext;
    }
    return sectionPlacementContexts[activeSectionId] ?? fallbackPlacementContext;
  }, [activeSectionId, sectionPlacementContexts, fallbackPlacementContext]);
  const activeSelectionId = selectedMeasureRange?.sectionId ?? null;

  useEffect(() => {
    console.log("[DrumUI] debug", {
      selectedSectionId: selectedMeasureRange?.sectionId ?? null,
      activeSectionId,
      hasActiveDrumTrack: !!activeDrumTrack,
      trackKeys: sectionTrackIds,
      notesCount: notes.length,
    });
  }, [selectedMeasureRange?.sectionId, activeSectionId, activeDrumTrack, sectionTrackIds, notes.length]);

  useEffect(() => {
    if (!selectedMeasureRange) {
      console.log("[MidiDebug] No selectedMeasureRange; notes length:", notes.length);
      return;
    }

    const rangeStart = selectedMeasureRange.startTime ?? 0;
    const rangeEnd = selectedMeasureRange.endTime ?? rangeStart;
    const toSummary = (note: PianoRollNote) => ({
      id: note.id,
      time: Number(note.time?.toFixed?.(3) ?? note.time ?? 0),
      duration: Number(note.duration?.toFixed?.(3) ?? note.duration ?? 0),
      lane: note.lane,
      limbId: note.limbId ?? null,
    });
    const inRange = notes.filter((note) => {
      const start = note.time ?? 0;
      return start >= rangeStart && start <= rangeEnd;
    });
    const times = notes.map((note) => note.time ?? 0);
    const minTime = times.length ? Math.min(...times) : null;
    const maxTime = times.length ? Math.max(...times) : null;

    console.log("[MidiDebug] notes", {
      total: notes.length,
      minTime,
      maxTime,
      rangeStart,
      rangeEnd,
      inRangeCount: inRange.length,
      sampleInRange: inRange.slice(0, 5).map(toSummary),
    });
  }, [notes, selectedMeasureRange]);

  useEffect(() => {
    if (!tracks.length) {
      return;
    }
    console.log(
      "[WaveDebug] Tracks",
      tracks.map((track) => ({
        key: track.key,
        seconds: track.seconds,
        peaksLen: track.peaks?.length ?? 0,
        sr: track.sr,
      })),
    );
  }, [tracks]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const maxTrackSeconds = tracks.reduce((max, track) => {
      const seconds = typeof track.seconds === "number" ? track.seconds : 0;
      return Math.max(max, seconds);
    }, 0);
    const maxSectionEnd = sections.reduce((max, section) => {
      const end = typeof section.end === "number" ? section.end : 0;
      return Math.max(max, end);
    }, 0);
    (window as any).__DTK_STATE__ = {
      tracksCount: tracks.length,
      sectionsCount: sections.length,
      notesCount: notes.length,
      sectionTrackKeys: Object.keys(sectionDrumTracks ?? {}),
      activeSectionId,
      selectedSectionId: selectedMeasureRange?.sectionId ?? null,
      timelineDurationSec: Math.max(10, maxTrackSeconds, maxSectionEnd, 0),
      sections: sections.slice(0, 50).map((section) => ({
        id: section.id,
        start: section.start,
        end: section.end,
        label: section.label,
      })),
    };
  }, [tracks, sections, notes.length, sectionDrumTracks, activeSectionId, selectedMeasureRange?.sectionId]);

  useEffect(() => {
    if (!selectedMeasureRange?.sectionId) {
      lastSectionSyncSignatureRef.current = null;
      return;
    }

    const sectionId = selectedMeasureRange.sectionId;
    const track = sectionDrumTracks[sectionId];
    if (!track) {
      lastSectionSyncSignatureRef.current = null;
      return;
    }

    const placement = activePlacementContext ?? fallbackPlacementContext;
    if (!placement) {
      return;
    }

    const noteCount = track.notes?.length ?? 0;
    const lastNoteId = noteCount > 0 ? track.notes[noteCount - 1]?.id ?? `idx-${noteCount - 1}` : "none";
    const placementKeyParts = [
      placement.startMeasure ?? 0,
      placement.endMeasure ?? 0,
      placement.startTimeSec ?? 0,
      Array.isArray(placement.tempos) ? placement.tempos.join(",") : "",
      placement.timeSignature ? placement.timeSignature.join("/") : "",
    ];
    const signature = [
      sectionId,
      track.track_id ?? "track",
      noteCount,
      lastNoteId,
      placementKeyParts.join("|"),
    ].join(":");

    if (lastSectionSyncSignatureRef.current === signature) {
      return;
    }

    lastSectionSyncSignatureRef.current = signature;
    syncSectionMidiNotes(sectionId, track, placement);
  }, [selectedMeasureRange?.sectionId, sectionDrumTracks, activePlacementContext, fallbackPlacementContext, syncSectionMidiNotes]);

  const ensureSectionSelection = useCallback(
    (sectionId: string | null | undefined) => {
      if (!sectionId) {
        return;
      }
      setSelectedSectionIds((prev) => {
        if (prev.size > 0) {
          return prev;
        }
        return new Set([sectionId]);
      });
      setSelectedMeasureRange((prev) => {
        if (prev) {
          return prev;
        }
        const targetSection = sections.find((s) => s.id === sectionId);
        return targetSection ? sectionToMeasureRange(targetSection, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode) : prev;
      });
    },
    [sections, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode],
  );


  const handleClearAudio = useCallback(() => {
    if (!tracks.length) {
      return;
    }
    const confirmed = window.confirm("Remove all uploaded audio, sections, and drum edits?");
    if (!confirmed) {
      return;
    }
    setTracks([]);
    setSections([]);
    setNotes([]);
    setSectionDrumTracks({});
    setSectionGrooveMaps({});
    setSectionPlacementContexts({});
    setSectionNoteIds({});
    setSelectedSectionIds(new Set());
    setSelectedMeasureRange(null);
    setSongMap(null);
    setArrangementSource(null);
    setErr(null);
  }, [tracks.length]);

  const downloadJson = useCallback((data: unknown, filename: string) => {
    try {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
    } catch (downloadErr) {
      console.warn("[DebugExport] Failed to create JSON download", downloadErr);
      alert("Unable to export debug payload; see console for details.");
    }
  }, []);

  const exportActiveDrumDebug = useCallback(() => {
    const sectionId = selectedMeasureRange?.sectionId ?? activeSectionId ?? null;
    if (!sectionId) {
      alert("Select a section before exporting drum debug data.");
      return;
    }
    const track = sectionDrumTracks[sectionId];
    if (!track) {
      alert("No drum track data is available for the selected section yet.");
      return;
    }
    const placement = sectionPlacementContexts[sectionId];
    const selectedRange = selectedMeasureRange && selectedMeasureRange.sectionId === sectionId
      ? selectedMeasureRange
      : null;
    const noteIds = new Set(sectionNoteIds[sectionId] ?? []);
    const sectionNotes = noteIds.size ? notes.filter((note) => noteIds.has(note.id)) : [];
    const payload = {
      exportedAt: new Date().toISOString(),
      sectionId,
      placement,
      selectedRange,
      track,
      sectionNotes,
      stats: {
        trackNotes: track.notes?.length ?? 0,
        sectionNotes: sectionNotes.length,
      },
    };
    downloadJson(payload, `drum-debug-${sectionId}-${Date.now()}.json`);
  }, [
    selectedMeasureRange,
    activeSectionId,
    sectionDrumTracks,
    sectionPlacementContexts,
    sectionNoteIds,
    notes,
    downloadJson,
  ]);
  
  const injectDebugTestGroove = useCallback(() => {
    if (!selectedMeasureRange) {
      console.warn("[DebugTestGroove] No section selected; select a section before injecting the pattern.");
      return;
    }

    const baseBar = selectedMeasureRange.startMeasure ?? 0;
    const targetSectionId = selectedMeasureRange.sectionId ?? "__debug__";
    const beatsPerBarForSection = selectedMeasureRange.timeSignature?.[0] ?? timeSig[0] ?? 4;
    const barsToCover = Math.max(1, Math.min(2, selectedMeasureRange.measureCount || 2));
    const ticksPerBeat = 960;
    const debugNotes: DrumNoteEvent[] = [];
    const stamp = Date.now();

    const addNote = (
      barOffset: number,
      beatIndex: number,
      instrumentId: DrumInstrumentId,
      velocity = 0.95,
    ) => {
      const barIndex = baseBar + barOffset;
      const tickInBar = Math.max(0, Math.round(beatIndex * ticksPerBeat));
      const tickLength = Math.max(60, Math.round(ticksPerBeat * 0.95));
      const midiPitch = DRUM_INSTRUMENT_MIDI_MAP[instrumentId] ?? DRUM_INSTRUMENT_MIDI_MAP.snare_center;
      const midiVelocity = Math.max(1, Math.min(127, Math.round(velocity * 127)));
      const limbId = inferLimbFromInstrument(instrumentId) ?? inferLimbFromLane(instrumentId) ?? null;

      debugNotes.push({
        id: `debug-${targetSectionId}-${stamp}-${debugNotes.length}`,
        barIndex,
        tickInBar,
        tickLength,
        channel: 9,
        midiPitch,
        velocity: midiVelocity,
        instrumentId,
        limbId: limbId ?? undefined,
        isGhost: midiVelocity <= 40,
        isAccent: midiVelocity >= 110,
        isFlam: false,
        isDrag: false,
      });
    };

    for (let barOffset = 0; barOffset < barsToCover; barOffset += 1) {
      for (let beat = 0; beat < beatsPerBarForSection; beat += 1) {
        addNote(barOffset, beat, "kick", 0.98);
        addNote(barOffset, beat, "hihat_closed", 0.7);
        if (beat === 1 || beat === 3) {
          addNote(barOffset, beat, "snare_center", 0.9);
        }
      }
    }

    const debugTrack: DrumTrackForDCSM = {
      track_id: `debug-${targetSectionId}-${stamp}`,
      style_id: "debug",
      resolution_ppq: ticksPerBeat,
      notes: debugNotes,
      performance_spec: {
        styleId: "debug",
        globalFeel: "straight",
        quantizationBase: "16th",
        phrases: [],
      },
    };

    setSectionDrumTracks((prev) => ({
      ...prev,
      [targetSectionId]: debugTrack,
    }));

    const placement = activePlacementContext ?? fallbackPlacementContext;
    if (placement) {
      syncSectionMidiNotes(targetSectionId, debugTrack, placement);
    } else {
      syncSectionMidiNotes(targetSectionId, debugTrack);
    }

    applyTrackToMidiClip(debugTrack);
    ensureSectionSelection(targetSectionId);
    setDebugDrumGen({
      payloadSectionId: targetSectionId,
      hasDrumTrack: true,
      drumTrackNotes: debugNotes.length,
      hasLegacyNotes: false,
      legacyNotesCount: 0,
    });
    console.log(
      `[DebugTestGroove] Injected ${debugNotes.length} notes into section ${targetSectionId} starting at bar ${baseBar}`,
    );
  }, [
    selectedMeasureRange,
    timeSig,
    activePlacementContext,
    fallbackPlacementContext,
    syncSectionMidiNotes,
    applyTrackToMidiClip,
    ensureSectionSelection,
    setSectionDrumTracks,
    setDebugDrumGen,
  ]);
  const sectionDebugSummaries = useMemo(() => {
    return Object.entries(sectionDrumTracks ?? {}).map(([id, track]) => {
      const summary = track ? summarizeDrumTrack(track) : summarizeDrumTrack({ notes: [] } as any);
      return {
        id,
        noteCount: summary.noteCount,
        minBar: summary.minBar,
        maxBar: summary.maxBar,
        instruments: summary.instruments,
        barCount: typeof (track as any)?.barCount === "number" ? (track as any).barCount : null,
        trackId: (track as any)?.track_id ?? null,
      };
    });
  }, [sectionDrumTracks]);

  useEffect(() => {
    if (!fullSongStatus) {
      setFullSongProgress({ completed: 0, total: 0 });
      return;
    }
    if (fullSongStatus.type !== 'progress') {
      const timer = window.setTimeout(() => setFullSongStatus(null), 6000);
      return () => window.clearTimeout(timer);
    }
  }, [fullSongStatus]);
  
  // Comprehensive drum options
  const [drumOptions, setDrumOptions] = useState<DrumOptions>({
    bpm: 120, bars: 8, density: 0.7, swing: 0, humanize: 0.3,
    style: 'rock', label: 'verse', swing_preset: 'off', vel_preset: 'accent24', fill_preset: 'random',
    drum_velocity: 0.85, cymbal_velocity: 0.70, kick_velocity: 0.90, snare_velocity: 0.85,
    tom_velocity: 0.80, hihat_velocity: 0.65, crash_velocity: 0.90, ride_velocity: 0.70,
    drum_density: 0.7, cymbal_density: 0.6, hihat_density: 0.8, ride_density: 0.4, crash_density: 0.2,
    fill_density: 0.7, fill_location: 'end', fill_frequency: 0.25,
    hihat_complexity: 0.5, hihat_pattern: 'eighths', hihat_open_ratio: 0.2, hihat_ghost_notes: 0.3,
    ride_complexity: 0.4, ride_pattern: 'quarters', ride_vs_hihat_ratio: 0.3, ride_bell_ratio: 0.1,
    bass_line_mode: 'auto', bass_kick_sync: 0.7, bass_lock_downbeats: true,
    tom_usage: 0.3, crash_frequency: 0.2, ghost_note_density: 0.2, dynamic_range: 0.5
  });

  useEffect(() => {
    if (!selectedMeasureRange) {
      return;
    }
    const normalizedLabel = selectedMeasureRange.sectionLabel
      ?.toLowerCase()
      ?.replace(/[^a-z]/g, "");
    const derivedBpm = Math.round(selectedMeasureRange.avgTempo || bpm || 120);
    const derivedBars = Math.max(1, selectedMeasureRange.measureCount);

    setDrumOptions((prev) => {
      const nextLabel = normalizedLabel && DRUM_SECTION_LABELS.has(normalizedLabel)
        ? normalizedLabel
        : prev.label;
      if (prev.bpm === derivedBpm && prev.bars === derivedBars && prev.label === nextLabel) {
        return prev;
      }
      return {
        ...prev,
        bpm: derivedBpm,
        bars: derivedBars,
        label: nextLabel,
      };
    });
  }, [selectedMeasureRange?.sectionId, selectedMeasureRange?.avgTempo, selectedMeasureRange?.measureCount, selectedMeasureRange?.sectionLabel, bpm]);

  useEffect(() => {
    setDrumOptions((prev) => {
      const nextBpm = Math.round(bpm || 120);
      if (prev.bpm === nextBpm) {
        return prev;
      }
      return { ...prev, bpm: nextBpm };
    });
  }, [bpm]);

  useEffect(() => {
    if (!activeSelectionId) {
      setSelectedMeasureRange(null);
      return;
    }

    if (selectedMeasureRange?.sectionId === "full-song") {
      return;
    }

    const section = sections.find((s) => s.id === activeSelectionId);
    if (!section) {
      setSelectedMeasureRange(null);
      return;
    }

    setSelectedMeasureRange((prev) => {
      if (prev?.sectionId === activeSelectionId) {
        return prev;
      }
      return sectionToMeasureRange(section, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode);
    });
  }, [activeSelectionId, sections, bpm, timeSig, songMap, selectedMeasureRange?.sectionId, tempoFlattenToleranceBpm, drumTempoMode]);
  
  // Read URL parameters from Professional Tier page
  const [sourceInfo, setSourceInfo] = useState<{source?: string; filename?: string; drummer?: string; fileKey?: string}>({});
  const autoLoadAttemptedRef = useRef(false);
  
  useEffect(() => {
    // Prevent duplicate auto-load in React StrictMode using ref
    if (autoLoadAttemptedRef.current) {
      console.log('⏭️ Auto-load already attempted, skipping');
      return;
    }
    autoLoadAttemptedRef.current = true;
    
    const urlParams = new URLSearchParams(window.location.search);
    const source = urlParams.get('source');
    const filename = urlParams.get('filename');
    const drummer = urlParams.get('drummer');
    const fileKey = urlParams.get('fileKey');
    
    console.log('WebDAWApp URL params:', { source, filename, drummer, fileKey });
    
    if (source || filename || drummer || fileKey) {
      setSourceInfo({ source: source || undefined, filename: filename || undefined, drummer: drummer || undefined, fileKey: fileKey || undefined });
      console.log('✅ Source info set:', { source, filename, drummer, fileKey });
      
      // Auto-load file if fileKey is present
      if (fileKey && filename) {
        console.log('🚀 Starting auto-load for fileKey:', fileKey);
        
        const loadFileFromKeyAsync = async (key: string, name: string) => {
          console.log('📂 loadFileFromKeyAsync called with:', key, name);
          await loadFileFromKey(key, name);
        };
        
        setTimeout(() => loadFileFromKeyAsync(fileKey, filename), 100);
      }
    }
  }, []);

  const gridSec = useMemo(() => (60 / bpm) * (4 / timeSig[1]) / 16, [bpm, timeSig]); // 1/64

  const timelineDurationSec = useMemo(() => {
    const trackDurations = tracks.length ? tracks.map((t) => t.seconds || 0) : [0];
    const waveformDuration = Math.max(...trackDurations, 0);
    const sectionExtent = sections.length ? Math.max(...sections.map((s) => s.end || 0)) : 0;
    const loopExtent = loop?.end ?? 0;
    return Math.max(10, waveformDuration, sectionExtent, loopExtent);
  }, [tracks, sections, loop]);

  const totalSongBars = useMemo(() => {
    const beatsPerMeasure = timeSig[0] || 4;
    const secPerBeat = (60 / Math.max(1, bpm)) * (4 / (timeSig[1] || 4));
    const secPerBar = secPerBeat * beatsPerMeasure;
    if (!Number.isFinite(secPerBar) || secPerBar <= 0) {
      return 1;
    }
    return Math.max(1, Math.ceil(timelineDurationSec / secPerBar));
  }, [bpm, timeSig, timelineDurationSec]);

  useEffect(() => {
    // Ensure we have a midi track + clip set up
    let ensuredTrackId = drumTrackId;
    let ensuredClipId = drumClipId;

    const drumsTrack = midiSong.tracks.find((t) => t.kind === "drums" || t.chan === 10);
    if (drumsTrack) {
      ensuredTrackId = drumsTrack.id;
      if (drumsTrack.clips.length > 0) {
        ensuredClipId = drumsTrack.clips[0].id;
      }
    }

    if (!ensuredTrackId) {
      ensuredTrackId = addMidiTrack({ name: "Drums", kind: "drums", chan: 10 });
    }

    if (!ensuredClipId && ensuredTrackId) {
      const ppq = midiSong.ppq || 480;
      const defaultBars = Math.max(4, totalSongBars ?? selectedMeasureRange?.measureCount ?? 4);
      const clipEndTick = defaultBars * beatsPerBar * ppq;
      ensuredClipId = addMidiClip(ensuredTrackId, {
        name: "Main Groove",
        startTick: 0,
        endTick: clipEndTick,
        notes: [],
      });
    }

    if (ensuredTrackId && ensuredTrackId !== drumTrackId) {
      setDrumTrackId(ensuredTrackId);
    }
    if (ensuredClipId && ensuredClipId !== drumClipId) {
      setDrumClipId(ensuredClipId);
    }
  }, [
    midiSong.tracks,
    midiSong.ppq,
    addMidiTrack,
    addMidiClip,
    drumTrackId,
    drumClipId,
    beatsPerBar,
    selectedMeasureRange?.measureCount,
    totalSongBars,
  ]);

  const pixelsPerSecond = useMemo(() => {
    const beatsPerSecond = bpm > 0 ? bpm / 60 : 120 / 60;
    return gridPixelsPerBeat * beatsPerSecond;
  }, [bpm, gridPixelsPerBeat]);

  const scrollTimelineTo = useCallback((targetPx: number) => {
    const el = timelineScrollRef.current;
    if (!el) return;
    el.scrollLeft = Math.max(0, targetPx);
  }, []);

  const scrollToTime = useCallback((seconds: number) => {
    if (!Number.isFinite(seconds)) return;
    scrollTimelineTo(seconds * pixelsPerSecond);
  }, [pixelsPerSecond, scrollTimelineTo]);

  const scrollToSelectedSection = useCallback(() => {
    if (!selectedSectionIds.size) return;
    const firstId = Array.from(selectedSectionIds)[0];
    const section = sections.find((s) => s.id === firstId);
    if (!section) return;
    const el = timelineScrollRef.current;
    if (!el) {
      scrollToTime(section.start);
      return;
    }
    const startPx = section.start * pixelsPerSecond;
    const sectionPx = Math.max(1, (section.end - section.start) * pixelsPerSecond);
    const centered = Math.max(0, startPx - Math.max(0, (el.clientWidth - sectionPx) / 2));
    scrollTimelineTo(centered);
  }, [pixelsPerSecond, scrollTimelineTo, scrollToTime, sections, selectedSectionIds]);

  const handleDebugJumpToSection = useCallback(
    (sectionId: string) => {
      if (!sectionId) {
        return;
      }

      setSelectedSectionIds(new Set([sectionId]));

      const targetSection = sections.find((s) => s.id === sectionId);
      if (targetSection) {
        const nextRange = sectionToMeasureRange(targetSection, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode);
        setSelectedMeasureRange(nextRange);
      } else {
        console.warn("[DebugJump] No Section object found for", sectionId);
      }

      scrollToSelectedSection();
    },
    [sections, bpm, timeSig, songMap, scrollToSelectedSection, setSelectedSectionIds, setSelectedMeasureRange],
  );

  const scrollToPlayhead = useCallback(() => {
    scrollToTime(playhead);
  }, [playhead, scrollToTime]);

  const handleScrollSlider = useCallback(
    (percent: number) => {
      const ratio = percent / 100;
      setScrollRatio(ratio, null);
      setScrollPercent(percent);
    },
    [setScrollRatio],
  );

  const onScrollSliderChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const next = Number(event.target.value);
    handleScrollSlider(next);
  }, [handleScrollSlider]);

  useEffect(() => {
    let raf = 0; let last = performance.now();
    function tick(now: number) {
      const dt=(now-last)/1000; last=now;
      if (playing) {
        setPlayhead((p) => {
          const next = p + dt;
          void scheduleDrumsBetween(lastDrumScheduleSecRef.current, next);
          lastDrumScheduleSecRef.current = next;
          return next;
        });
      }
      raf=requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick); return ()=>cancelAnimationFrame(raf);
  }, [playing, scheduleDrumsBetween]);

  useEffect(() => { Engine.setBpm(bpm); }, [bpm]);
  useEffect(() => { Engine.setLoop(loop.start, loop.end, loop.enabled); }, [loop]);
  useEffect(() => {
    const apiBase = resolveApiBaseNormalized();
    const urls = tracks.map(t => ({ key: t.key, url: `${apiBase}/files/audio?key=${encodeURIComponent(t.key)}` }));
    Engine.refreshTracks(urls);
  }, [tracks]);

  useEffect(() => {
    let attachRaf: number | null = null;
    let scrollRaf: number | null = null;
    let cleanup: (() => void) | null = null;

    const ratioFor = (el: HTMLElement) => {
      const max = getMaxScroll(el);
      if (!Number.isFinite(max) || max <= 0) return 0;
      return Math.min(1, Math.max(0, el.scrollLeft / max));
    };

    const updatePercentFrom = (el: HTMLElement) => {
      const ratio = ratioFor(el);
      const pct = ratio * 100;
      setScrollPercent((prev) => (Math.abs(prev - pct) < 0.25 ? prev : pct));
    };

    const attachIfReady = () => {
      const timelineEl = timelineScrollRef.current;
      const pianoEl = pianoRollScrollRef.current;
      if (!timelineEl || !pianoEl) {
        attachRaf = window.requestAnimationFrame(attachIfReady);
        return;
      }
      if (cleanup) {
        return;
      }

      const onScroll = (source: HTMLElement) => {
        if (scrollSyncStateRef.current.isSyncing) {
          updatePercentFrom(source);
          return;
        }
        if (scrollRaf) return;
        scrollRaf = window.requestAnimationFrame(() => {
          scrollRaf = null;
          const ratio = ratioFor(source);
          setScrollRatio(ratio, source);
          updatePercentFrom(source);
        });
      };

      const onTimeline = () => onScroll(timelineEl);
      const onPiano = () => onScroll(pianoEl);

      updatePercentFrom(timelineEl);

      timelineEl.addEventListener("scroll", onTimeline, { passive: true });
      pianoEl.addEventListener("scroll", onPiano, { passive: true });

      cleanup = () => {
        timelineEl.removeEventListener("scroll", onTimeline);
        pianoEl.removeEventListener("scroll", onPiano);
      };
    };

    attachIfReady();

    return () => {
      if (attachRaf) {
        window.cancelAnimationFrame(attachRaf);
      }
      if (scrollRaf) {
        window.cancelAnimationFrame(scrollRaf);
      }
      cleanup?.();
    };
  }, [getMaxScroll, setScrollRatio]);
  
  // CRITICAL FIX: Only seek when NOT playing (manual seek only)
  // Don't seek during playback - it causes audio distortion!
  useEffect(() => { 
    if (!playing) {
      Engine.seek(playhead); 
    }
  }, [playhead, playing]);

  async function addFile(file: File) {
    setBusy(true); setErr(null);
    try {
      // Upload file and request waveform metadata
      const { waveform } = await webdawApi.fullWorkflow(file);
      if (!waveform?.key) {
        throw new Error("Upload succeeded but waveform metadata was missing");
      }

      const hydratedTrack = await buildTrackFromWaveform({
        key: waveform.key,
        name: file.name,
        color: pickTrackColor(tracks.length),
        initialWaveform: waveform,
        preferFreshWaveform: true,
      });

      setTracks((t) => [...t, hydratedTrack]);
      
      // Analyze tempo automatically
      try {
        const { analyzeTempo } = await import('../services/api');
        const tempoResult = await analyzeTempo(waveform.key);
        if (tempoResult.tempo && tempoResult.tempo > 0) {
          setBpm(Math.round(tempoResult.tempo));
          console.log(`Detected tempo: ${tempoResult.tempo} BPM`);
        }
      } catch (tempoError: any) {
        console.warn('Tempo detection failed:', tempoError);
        setErr(`Waveform loaded, but tempo detection failed. Using default 120 BPM.`);
      }
      
      // Auto-sectionize after tempo is detected
      if (waveform.key) {
        // Give tempo detection a moment to complete
        setTimeout(() => handleAutoSectionize(waveform.key), 500);
      }
    } catch (e: any) { setErr(e?.message || "Upload failed"); } finally { setBusy(false); }
  }
  
  const loadingFilesRef = useRef<Set<string>>(new Set());
  
  async function loadFileFromKey(fileKey: string, filename: string) {
    // Prevent duplicate loading using ref-based lock
    if (loadingFilesRef.current.has(fileKey)) {
      return;
    }
    
    // Check if track already exists
    if (tracks.some(t => t.key === fileKey)) {
      console.log('Track already loaded, skipping');
      return;
    }
    
    // Lock this file key
    loadingFilesRef.current.add(fileKey);
    setBusy(true); setErr(null);
    
    try {
      console.log('Loading file from key:', fileKey);
      
      const hydratedTrack = await buildTrackFromWaveform({
        key: fileKey,
        name: filename,
        color: pickTrackColor(tracks.length),
      });

      setTracks((existing) => [...existing, hydratedTrack]);
    } catch (e: any) {
      setErr(e?.message || "Failed to load file");
      console.error('Load file error:', e);
    } finally { 
      setBusy(false);
      // Release the lock so file can be loaded again if needed
      loadingFilesRef.current.delete(fileKey);
    }
  }
  
  function onDropFiles(list: FileList) { Array.from(list).forEach((f) => addFile(f)); }

  // Align selected sections to a track's beats
  async function alignTo(trackKey: string) {
    try {
      const { sections: aligned } = await alignSections(trackKey, sections.map(s=>({start:s.start,end:s.end})));
      setSections(sections.map((s,i)=>({ ...s, start: aligned[i].start, end: aligned[i].end })));
    } catch (e) { console.warn("align failed", e); }
  }

  // NEW: Full analysis with bars, meter, and enhanced sections
  async function handleAnalyzeFull(trackKey: string) {
    setBusy(true);
    try {
      const response = await fetch(
        `/dcsm/analyze_full?key=${encodeURIComponent(trackKey)}`
      );
      
      if (!response.ok) {
        throw new Error(`Full analysis failed: ${response.statusText}`);
      }
      
      const json = await response.json();
      
      // Build SongMap
      const map: any = {
        duration: json.duration,
        globalBpmEstimate: json.global_bpm_estimate ?? 120,
        meter: json.meter,
        bars: json.bars,
        sections: json.sections,
        beatTimes: json.beat_times ?? [],
      };
      
      setSongMap(map);
      
      console.log("🎯 SongMap loaded!");
      console.log(`  Global BPM: ${map.globalBpmEstimate}`);
      console.log(`  Meter: ${map.meter[0]}/${map.meter[1]}`);
      console.log(`  Bars: ${map.bars.length}`);
      console.log(`  Sections: ${map.sections.length}`);
      console.log(`  Section labels:`, map.sections.map((s: any) => s.label));
      
      // Update BPM
      setBpm(Math.round(map.globalBpmEstimate));
      
      // Convert sections to UI format with bar indices and micro tempo
      const uiSections: Section[] = map.sections.map((s: any, i: number) => {
        // Calculate per-section tempo from bars
        let sectionTempo = map.globalBpmEstimate;
        if (map.bars && map.bars.length > 0 && s.start_bar_index !== undefined && s.end_bar_index !== undefined) {
          const sectionBars = map.bars.slice(s.start_bar_index, s.end_bar_index + 1);
          if (sectionBars.length > 0) {
            const tempos = sectionBars.map((b: any) => b.tempo_bpm);
            sectionTempo = tempos.reduce((a: number, b: number) => a + b, 0) / tempos.length;
          }
        }
        
        return {
          id: `section-${Date.now()}-${i}`,
          start: s.start,
          end: s.end,
          label: s.label || `Section ${i + 1}`,
          confidence: s.confidence || 0.75,
          energy: s.energy || 0.5,
          spectral_centroid: s.spectral_centroid || 0.5,
          repetition_group: s.repetition_group,
          startBarIndex: s.start_bar_index,
          endBarIndex: s.end_bar_index,
          barCount: s.bar_count,
          tempo: sectionTempo, // ← Per-section micro tempo!
          density: 0.5 + (s.energy || 0.5) * 0.4,
          fillIn: i > 0,
          fillOut: i < map.sections.length - 1,
        };
      });
      
      console.log(`✅ Created ${uiSections.length} UI sections with tempo data`);
      
      // Apply with conflict handling
      const avgTempo = map.bars.length > 0 
        ? map.bars.reduce((sum: number, b: any) => sum + b.tempo_bpm, 0) / map.bars.length 
        : 120;
      applyArrangement(uiSections, 'Auto-Analyze (AI)', avgTempo);
      
      // Log bar tempo variations for debugging
      if (map.bars.length > 0) {
        const tempos = map.bars.map((b: any) => b.tempo_bpm);
        const minTempo = Math.min(...tempos);
        const maxTempo = Math.max(...tempos);
        const avgTempo = tempos.reduce((a: number, b: number) => a + b, 0) / tempos.length;
        console.log(`  Per-bar tempo: min=${minTempo.toFixed(1)}, max=${maxTempo.toFixed(1)}, avg=${avgTempo.toFixed(1)}`);
      }
      
    } catch (e: any) {
      console.error("Full analysis error:", e);
      setErr(`Full analysis failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  // Helper: Apply arrangement with conflict handling
  function applyArrangement(newSections: Section[], sourceName: string, newBpm?: number) {
    // Warn if replacing existing arrangement
    if (sections.length > 0 && arrangementSource) {
      const confirmed = window.confirm(
        `⚠️ Replace ${arrangementSource} (${sections.length} sections) with ${sourceName} (${newSections.length} sections)?`
      );
      if (!confirmed) {
        console.log('❌ User cancelled arrangement replacement');
        return false;
      }
    }
    
    setSections(newSections);
    setSelectedSectionIds(new Set());
    setSelectedMeasureRange(null);
    setArrangementSource(sourceName);
    if (newBpm) setBpm(newBpm);
    setErr(null);
    
    console.log(`✅ Applied ${sourceName}: ${newSections.length} sections`);
    return true;
  }
  
  // Clear arrangement
  function clearArrangement() {
    const confirmed = window.confirm('Clear all sections and start over?');
    if (!confirmed) return;
    
    setSections([]);
    setSelectedSectionIds(new Set());
    setSelectedMeasureRange(null);
    setPlayhead(0);
    setArrangementSource(null);
    setSongMap(null);
    setSectionDrumTracks({});
    setSectionGrooveMaps({});
    setSectionPlacementContexts({});
    setSectionNoteIds({});
    setNotes([]);
    console.log('🗑️ Arrangement cleared');
  }
  
  // Auto-detect musical arrangement sections with beat layer
  async function handleAutoSectionize(trackKey: string) {
    setBusy(true);
    try {
      // Use NEW full analysis endpoint with bar layer
      await handleAnalyzeFull(trackKey);
    } catch (e: any) {
      console.error("Section detection error:", e);
      setErr(`Auto-sectionization failed: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }
  
  // Handle manual arrangement entry
  function handleManualArrangement(arrangement: ManualArrangement) {
    console.log('📝 Manual arrangement applied:', arrangement);
    
    // Convert measures to time
    const beatsPerMeasure = arrangement.timeSignature[0];
    const secondsPerBeat = 60.0 / arrangement.globalTempo;
    const secondsPerMeasure = secondsPerBeat * beatsPerMeasure;
    
    // Convert manual sections to UI sections
    const uiSections: Section[] = arrangement.sections.map((s, i) => {
      const startTime = (s.startMeasure - 1) * secondsPerMeasure;
      const endTime = startTime + (s.numMeasures * secondsPerMeasure);
      
      return {
        id: `manual-${Date.now()}-${i}`,
        start: startTime,
        end: endTime,
        label: s.label,
        tempo: s.tempo || arrangement.globalTempo,
        density: 0.7,
        fillIn: i > 0,
        fillOut: i < arrangement.sections.length - 1,
        confidence: 1.0,
        energy: 0.5,
      };
    });
    
    const totalMeasures = arrangement.sections.reduce((sum, s) => sum + s.numMeasures, 0);
    applyArrangement(uiSections, `Manual Entry (${totalMeasures} measures)`, arrangement.globalTempo);
  }
  
  // Handle internet song lookup
  function handleSongLookup(songInfo: SongInfo) {
    console.log('🌐 Song info from internet:', songInfo);
    
    const sanitizedSections = (songInfo.sections || []).filter((section) =>
      typeof section.startTime === 'number' &&
      typeof section.endTime === 'number' &&
      section.endTime > section.startTime
    );

    const primaryTrackDuration = tracks[0]?.seconds;
    const lookupDuration = sanitizedSections.length > 0
      ? sanitizedSections[sanitizedSections.length - 1].endTime
      : undefined;

    let timelineScale = 1;
    if (primaryTrackDuration && lookupDuration && lookupDuration > 0) {
      const diff = Math.abs(primaryTrackDuration - lookupDuration);
      if (diff > 1.5) {
        timelineScale = primaryTrackDuration / lookupDuration;
        console.log(`⚖️ Scaling lookup sections by ${timelineScale.toFixed(3)} to match uploaded audio (${primaryTrackDuration.toFixed(2)}s)`);
      }
    }

    if (sanitizedSections.length > 0) {
      const timestamp = Date.now();
      const uiSections: Section[] = sanitizedSections.map((section, idx) => ({
        id: `lookup-${timestamp}-${idx}`,
        start: section.startTime * timelineScale,
        end: section.endTime * timelineScale,
        label: section.label,
        tempo: songInfo.tempo,
        density: 0.7,
        fillIn: idx > 0,
        fillOut: idx < sanitizedSections.length - 1,
        confidence: 0.95,
        energy: 0.6,
      }));

      const applied = applyArrangement(
        uiSections,
        `Well Known Song • ${songInfo.title}`,
        songInfo.tempo
      );

      if (applied) {
        const derivedDuration = uiSections[uiSections.length - 1]?.end ?? primaryTrackDuration ?? 0;
        setSongMap({
          duration: derivedDuration,
          globalBpmEstimate: songInfo.tempo,
          meter: songInfo.timeSignature || [4, 4],
          sections: uiSections,
          bars: [],
          beatTimes: [],
          source: songInfo.source,
          title: songInfo.title,
          artist: songInfo.artist,
        });
      }
    } else {
      // No sections, just apply tempo and update map for tempo panel
      setBpm(songInfo.tempo);
      setSongMap({
        duration: primaryTrackDuration ?? 0,
        globalBpmEstimate: songInfo.tempo,
        meter: songInfo.timeSignature || [4, 4],
        sections: [],
        bars: [],
        beatTimes: [],
        source: songInfo.source,
        title: songInfo.title,
        artist: songInfo.artist,
      });
      console.log(`✅ Applied tempo from ${songInfo.title}: ${songInfo.tempo} BPM`);
    }
  }

  async function executeDrumGeneration(
    config: DrumGenerationConfig,
    options: { suppressSpinner?: boolean } = {}
  ): Promise<boolean> {
    const { suppressSpinner = false } = options;
    if (!suppressSpinner) {
      setGeneratingDrums(true);
    }
    let appliedHighRes = false;
    try {
      let payload: DrumGenerationConfig = {
        ...config,
        publicDrummerId: selectedDrummer?.id ?? config.publicDrummerId ?? config.drummer,
        drummerPersona: selectedDrummer ?? config.drummerPersona,
      };
      if (config.sectionId) {
        try {
          const brainStore = useBrainPanelStore.getState();
          const brainConfig = await brainStore.ensureSectionConfig(config.sectionId);
          if (brainConfig) {
            payload = {
              ...payload,
              brainConfig,
            };
          }
        } catch (err) {
          console.warn("Failed to fetch brain config for section", config.sectionId, err);
        }
      }

      payload = { ...payload, midiMapName };
      payload = {
        ...payload,
        grooveSource: grooveSource === "egmd_phrases" ? "egmd_phrases" : undefined,
        grooveMode: grooveSource === "egmd_phrases" ? grooveMode : undefined,
        styleGroup: grooveSource === "egmd_phrases" ? styleGroup : undefined,
        egmdPhraseId: grooveSource === "egmd_phrases" && selectedEgmdPhraseId !== null ? selectedEgmdPhraseId : undefined,
      };
      console.log('🥁 Generating drums:', payload);

      const apiBase = resolveApiBaseNormalized();
      const url = `${apiBase}/api/generate-drums`;

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Generation failed');
      }
      
      const result = await response.json();
      const resultMetadata = result?.metadata ?? {};
      const builderVersion =
        (resultMetadata as any)?.builder_version ?? (resultMetadata as any)?.builderVersion ?? null;
      const resultOk = (result as any)?.ok;
      if (resultOk === false) {
        const detail =
          (result as any)?.error ?? (result as any)?.message ?? (result as any)?.detail ?? 'Generation failed';
        throw new Error(String(detail));
      }
      if (builderVersion && String(builderVersion).toLowerCase() !== "v2") {
        const msg = `Warning: drum builder_version=${builderVersion}. Expected v2.`;
        console.warn(msg, { metadata: resultMetadata });
        setErr(msg);
      }
      const genMs = (resultMetadata as any)?.generation_time_ms;
      console.log(
        `✅ Drums generated${typeof genMs === "number" ? ` in ${genMs}ms` : ""}`,
      );

      setLastEgmdPhraseInfo((resultMetadata as any)?.egmdPhrase ?? null);

      if (typeof result?.midi_base64 === "string" && result.midi_base64.length > 0) {
        setLastGeneratedMidiBase64(result.midi_base64);
        const label = payload.sectionId ? `Drums-${payload.sectionId}` : "Drums";
        setLastGeneratedMidiLabel(label);
      }

      let placementContext: DrumTrackPlacementContext | undefined;
      const sectionId = payload.sectionId;
      if (sectionId) {
        const targetSection = sections.find((s) => s.id === sectionId) || null;
        const currentRange =
          selectedMeasureRange && selectedMeasureRange.sectionId === sectionId
            ? selectedMeasureRange
            : targetSection
              ? sectionToMeasureRange(targetSection, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode)
              : null;
        const startTimeSec = currentRange?.startTime ?? targetSection?.start ?? 0;
        placementContext = {
          startMeasure: payload.startMeasure,
          endMeasure: payload.endMeasure,
          tempos: payload.tempos,
          timeSignature: payload.timeSignature,
          startTimeSec,
        };
        setSectionPlacementContexts((prev) => ({
          ...prev,
          [sectionId]: placementContext!,
        }));
      }
      const applied = applyDrumGenerationResult(
        result,
        payload,
        {
          bpm,
          timeSig,
          setSectionDrumTracks,
          setSectionGrooveMaps,
          setNotes,
          syncSectionMidiNotes,
          ensureSectionSelection,
          applyTrackToMidiClip,
          setDebugDrumGen,
        },
        {
          placementContext,
          convertTrackToMidiNotes,
          gridSec,
          hydrateLegacyNote,
          synthesizeLegacyTrack: (legacyNotes, derivedSectionId, config, fallbackBpmValue) =>
            synthesizeDrumTrackFromLegacyNotes(
              legacyNotes,
              derivedSectionId,
              config,
              typeof fallbackBpmValue === "number" && fallbackBpmValue > 0
                ? fallbackBpmValue
                : bpm,
            ),
        },
      );
      appliedHighRes = applied || appliedHighRes;
      
    } catch (e: any) {
      console.error('❌ Drum generation failed:', e);
      setErr(`Drum generation failed: ${e.message}`);
      throw e;
    } finally {
      if (!suppressSpinner) {
        setGeneratingDrums(false);
      }
    }
    return appliedHighRes;
  }

  async function handleGenerateDrums(config: DrumGenerationConfig) {
    try {
      if (!selectedDrummer) {
        setShowDrummerPersonaModal(true);
        return;
      }
      await executeDrumGeneration(config);
    } catch {
      // Error already handled inside executeDrumGeneration
    }
  }

  function downloadMidiBase64(base64Midi: string, filenameBase: string) {
    const binStr = window.atob(base64Midi);
    const bytes = new Uint8Array(binStr.length);
    for (let i = 0; i < binStr.length; i++) bytes[i] = binStr.charCodeAt(i);

    const blob = new Blob([bytes], { type: "audio/midi" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${filenameBase}.mid`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  const buildAutoConfigForSection = (section: Section): DrumGenerationConfig | null => {
    const measureRange = sectionToMeasureRange(section, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode);
    if (!measureRange) {
      return null;
    }

    const normalizedLabel = section.label?.toLowerCase() ?? 'default';
    const profile = SECTION_AUTOGEN_PRESETS[normalizedLabel] || SECTION_AUTOGEN_PRESETS.default;
    const energy = typeof section.energy === 'number' ? section.energy : 0.6;

    const baseIntensity = clamp01(drumOptions.density);
    const intensity = clamp01(baseIntensity * 0.6 + profile.intensity * 0.4 + (energy - 0.5) * 0.3);
    const baseVariation = clamp01(drumOptions.dynamic_range ?? drumOptions.humanize ?? 0.5);
    const variation = clamp01(baseVariation * 0.5 + profile.variation * 0.5);
    const fillDensity = clamp01(profile.fillDensity ?? drumOptions.fill_density);
    const fillType = profile.fillType ?? drumOptions.fill_preset ?? 'auto';
    const swingAmount = clamp01((drumOptions.swing ?? 0) + (profile.swingBoost ?? 0));
    const ghostAmount = clamp01((drumOptions.ghost_note_density ?? 0.3) + (profile.ghostBoost ?? 0));
    const fillLocations = (profile.enforceFill || section.fillOut)
      ? [Math.max(0, measureRange.measureCount - 1)]
      : [];

    const rudimentControls = profile.preferRudiments
      ? {
          enabled: true,
          preferredFamilies: [],
          preferredRudiments: [],
          density: clamp01(drumOptions.ghost_note_density ?? 0.4),
          ensureDownbeatKick: true,
          preserveHatTail: true,
          handLead: 'auto' as const,
        }
      : undefined;

    const drummerId = selectedDrummer?.id || 'jeff_porcaro';
    const resolvedStyle = selectedDrummer?.style || drumOptions.style || 'rock';

    return {
      sectionId: section.id,
      startMeasure: measureRange.startMeasure,
      endMeasure: measureRange.endMeasure,
      tempos: measureRange.tempos,
      timeSignature: measureRange.timeSignature,
      style: resolvedStyle,
      drummer: drummerId,
      intensity,
      variation,
      generationMode: profile.mode,
      humanize: true,
      fillLocations,
      fillType,
      fillDensity,
      humanizeAmount: clamp01(drumOptions.humanize),
      ghostNoteAmount: ghostAmount,
      swingAmount,
      buildScope: 'selected_section',
      guideEnabled: false,
      fillControls: {
        fillType,
        density: fillDensity,
        frequency: fillLocations.length ? 'section_transitions' : 'none',
      },
      rudimentControls,
    };
  };

  async function handleGenerateFullSong() {
    if (!sections.length) {
      setErr('No sections available to build drums for yet.');
      return;
    }
    if (!selectedDrummer) {
      setShowDrummerPersonaModal(true);
      return;
    }
    if (bulkGenerating || generatingDrums) {
      return;
    }
    setBulkGenerating(true);
    setFullSongProgress({ completed: 0, total: 1 });
    setFullSongStatus({
      type: 'progress',
      message: `Building drums for full song…`,
    });
    try {
      const primaryTrackKey = tracks[0]?.key;
      if (primaryTrackKey) {
        try {
          await analyzeSectionTempos(primaryTrackKey, sections);
        } catch (tempoErr) {
          console.warn('Tempo analysis during full-song generation failed', tempoErr);
        }
      }

      const fullRange: MeasureRange = {
        sectionId: "full-song",
        sectionLabel: "Full Song",
        startMeasure: 0,
        endMeasure: Math.max(0, totalSongBars - 1),
        measureCount: Math.max(1, totalSongBars),
        tempos: Array(Math.max(1, totalSongBars)).fill(bpm),
        avgTempo: bpm,
        timeSignature: timeSig,
        startTime: 0,
        endTime: timelineDurationSec,
      };

      const songSections = sections
        .map((section) => {
          const measureRange = sectionToMeasureRange(section, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode);
          const bars = Math.max(1, measureRange.measureCount);
          const name = (section.label || "section")
            .toLowerCase()
            .replace(/\s+/g, "_")
            .replace(/[^a-z0-9_]/g, "")
            .replace(/^_+|_+$/g, "");
          return { name: name || "section", bars };
        })
        .filter((s) => s.bars > 0);

      const derivedSongStyle = (drumOptions.style || "rock") as DrumGenerationConfig["songStyle"];

      setSelectedMeasureRange(fullRange);
      setSelectedSectionIds(new Set(["full-song"]));

      const fullSongConfig: DrumGenerationConfig = {
        sectionId: "full-song",
        startMeasure: fullRange.startMeasure,
        endMeasure: fullRange.endMeasure,
        tempos: fullRange.tempos,
        timeSignature: fullRange.timeSignature,
        style: drumOptions.style || "rock",
        drummer: selectedDrummer?.id || "jeff_porcaro",
        intensity: clamp01(drumOptions.density ?? 0.6),
        variation: clamp01(drumOptions.dynamic_range ?? drumOptions.humanize ?? 0.5),
        generationMode: "full_ai",
        humanize: true,
        fillLocations: [],
        fillType: drumOptions.fill_preset ?? "auto",
        fillDensity: clamp01(drumOptions.fill_density ?? 0.4),
        humanizeAmount: clamp01(drumOptions.humanize ?? 0.6),
        ghostNoteAmount: clamp01(drumOptions.ghost_note_density ?? 0.35),
        swingAmount: clamp01(drumOptions.swing ?? 0),
        buildScope: "full_song",
        guideEnabled: false,
        songStyle: derivedSongStyle,
        songSections,
        fillControls: {
          fillType: drumOptions.fill_preset ?? "auto",
          density: clamp01(drumOptions.fill_density ?? 0.4),
          frequency: "all_transitions",
        },
      };

      const applied = await executeDrumGeneration(fullSongConfig, { suppressSpinner: true });
      setFullSongProgress({ completed: 1, total: 1 });

      if (!applied) {
        setFullSongStatus({
          type: 'error',
          message: 'Finished, but the generator returned no drum data for the full song.',
        });
      } else {
        setFullSongStatus({
          type: 'success',
          message: '🥁 Completed drum build for the full song.',
        });
      }
    } catch (fullSongError: any) {
      console.error('❌ Full-song drum generation failed:', fullSongError);
      const errorMessage = `Full-song drum generation failed: ${fullSongError?.message || fullSongError}`;
      setErr(errorMessage);
      setFullSongStatus({ type: 'error', message: errorMessage });
    } finally {
      setBulkGenerating(false);
    }
  }

  // Analyze tempo for all sections
  async function analyzeSectionTempos(trackKey: string, sectionsToAnalyze: Section[]) {
    try {
      const { analyzeTempoSections } = await import('../services/api');
      const result = await analyzeTempoSections(
        trackKey,
        sectionsToAnalyze.map(s => ({ start: s.start, end: s.end }))
      );
      
      // Update sections with tempo data
      setSections(prev => prev.map((section, i) => {
        const tempoData = result.results[i];
        if (tempoData && !section.tempoLocked) {
          return {
            ...section,
            tempo: Math.round(tempoData.tempo * 10) / 10, // Round to 1 decimal
            tempoConfidence: tempoData.confidence,
          };
        }
        return section;
      }));
      
      console.log(`✅ Analyzed tempo for ${result.results.length} sections`);
    } catch (e: any) {
      console.warn('Tempo analysis failed:', e);
    }
  }

  // Save/Load session
  const SID = "dev";
  async function save(){
    try{ await saveSession(SID, { bpm, loop, tracks, sections, notes }); alert("Session saved"); } catch(e){ alert("Save failed"); }
  }
  async function load(){
    try{ 
      const s = await loadSession(SID) as any; 
      setTracks(s.tracks||[]); 
      setSections(s.sections||[]); 
      setNotes(s.notes||[]); 
      setBpm(s.bpm||120); 
      setLoop(s.loop||{enabled:false,start:0,end:4}); 
    } catch(e){ 
      alert("No saved session"); 
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <div className="flex-1 min-w-0 flex flex-col">
        <div className="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3">
          <div />
          <div className="flex flex-wrap items-center gap-3">
            <button className="px-2 py-1 rounded bg-emerald-600" onClick={async()=>{ await ensureDrumEngineReady(); lastDrumScheduleSecRef.current = playhead; await Engine.play(playhead); setPlaying(true); }}>Play</button>
            <button className="px-2 py-1 rounded bg-slate-700" onClick={async()=>{ await Engine.pause(); setPlaying(false); }}>Pause</button>
            <button className="px-2 py-1 rounded bg-slate-700" onClick={async()=>{ await Engine.stop(); setPlaying(false); setPlayhead(0); }}>Stop</button>
            <div className="flex items-center gap-1">
              <span className="text-slate-400 text-sm">BPM</span>
              <input className="w-16 bg-slate-800 rounded px-2 py-1" type="number" value={bpm} onChange={(e)=>setBpm(Math.max(20, Math.min(300, Number(e.target.value)||120)))} />
            </div>
            <label className="flex items-center gap-1 ml-4">
              <input type="checkbox" checked={loop.enabled} onChange={(e)=>setLoop({ ...loop, enabled: e.target.checked })} /> Loop
            </label>
            <div className="ml-4 w-[520px] max-w-[45vw]">
              <MicroTempoMeter
                beatTimes={Array.isArray(songMap?.beatTimes) ? songMap!.beatTimes! : []}
                playheadSec={playhead}
                sessionBpm={bpm}
                playing={playing}
                heightPx={72}
              />
            </div>
            <div className="text-sm text-slate-300 w-20 text-right">{secToBarsBeats(playhead, bpm, timeSig)}</div>
            <button className="px-3 py-1 rounded bg-indigo-600" onClick={() => fileRef.current?.click()} disabled={busy}>{busy?"Uploading…":"Upload Audio"}</button>
            <input ref={fileRef} type="file" accept="audio/*" className="hidden" onChange={(e)=>{ const f=e.target.files?.[0]; if (f) addFile(f); e.currentTarget.value=""; }} />
            <button className="px-3 py-1 rounded bg-slate-700 hover:bg-slate-600" onClick={() => setShowDrumPlayer(true)}>
              Drum Player
            </button>
            <button className="px-3 py-1 rounded bg-slate-700" onClick={load}>Load</button>
            {tracks.length > 0 && (
              <button
                className="px-3 py-1 rounded bg-rose-700 hover:bg-rose-600"
                onClick={handleClearAudio}
                disabled={busy}
              >
                Clear Audio
              </button>
            )}
            {tracks.length>0 && <button className="px-3 py-1 rounded bg-slate-700" onClick={()=>alignTo(tracks[0].key)}>Align to {tracks[0].name?.split("/").pop()}</button>}
          </div>
        </div>

        <div className="flex-1 min-w-0 overflow-hidden flex">
          {/* Center Column: Timeline + Piano Roll */}
          <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
            {/* Timeline & Musical Arrangement - Unified Container */}
            <div className="border-b border-slate-800 bg-slate-900">
              <div className="px-4 py-3 border-b border-slate-800/70 bg-slate-900/70">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex-1 min-w-[220px]">
                      <p className="text-[11px] uppercase tracking-wide text-slate-400">
                        Waveform &amp; Drum Grid Zoom
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-[11px] text-slate-500 w-12">Tight</span>
                        <input
                          type="range"
                          min={10}
                          max={240}
                          step={5}
                          value={gridPixelsPerBeat}
                          onChange={(e) => setGridPixelsPerBeat(Number(e.target.value))}
                          className="flex-1 accent-cyan-400"
                        />
                        <span className="text-[11px] text-slate-500 w-12 text-right">Wide</span>
                      </div>
                    </div>
                    <div className="flex-1 min-w-[220px]">
                      <p className="text-[11px] uppercase tracking-wide text-slate-400">
                        Linked Scroll Position
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-[11px] text-slate-500 w-12">Start</span>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          step={1}
                          value={scrollPercent}
                          onChange={onScrollSliderChange}
                          className="flex-1 accent-fuchsia-500"
                        />
                        <span className="text-[11px] text-slate-500 w-12 text-right">End</span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-2 text-xs text-slate-300">
                      <span className="text-[11px] uppercase tracking-wide text-slate-400">
                        Scroll Shortcuts (Synced)
                      </span>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => scrollToTime(0)}
                          className="px-2.5 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500"
                        >
                          ⏮ Start
                        </button>
                        <button
                          type="button"
                          onClick={scrollToPlayhead}
                          disabled={!tracks.length}
                          className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500"
                        >
                          ▶ Playhead
                        </button>
                        <button
                          type="button"
                          onClick={scrollToSelectedSection}
                          disabled={!hasSectionSelection}
                          className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500"
                        >
                          🎯 Section
                        </button>
                      </div>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Drag horizontally on any panel or use the shortcuts above — the timeline, drum piano roll, and limb grid stay locked together.
                  </p>

                  {debugMode && (
                    <div className="mt-2 text-[11px] text-slate-300 bg-slate-950/60 border border-slate-800 rounded px-2 py-1">
                      {(() => {
                        const t = timelineScrollRef.current;
                        const p = pianoRollScrollRef.current;
                        const fmt = (el: HTMLDivElement | null) =>
                          el
                            ? {
                                left: Math.round(el.scrollLeft),
                                w: el.scrollWidth,
                                cw: el.clientWidth,
                              }
                            : null;
                        return (
                          <div className="flex flex-col gap-1">
                            <div>timelineRef: {t ? "set" : "null"} {t ? JSON.stringify(fmt(t)) : ""}</div>
                            <div>pianoRef: {p ? "set" : "null"} {p ? JSON.stringify(fmt(p)) : ""}</div>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              </div>
              {/* Timeline / Waveform */}
              <div className="p-4">
                {err && <div className="mb-3 text-rose-400 text-sm">Error: {err}</div>}
                <Timeline
                  bpm={bpm}
                  tracks={tracks}
                  sections={sections}
                  onSectionsChange={setSections}
                  playhead={playhead}
                  setPlayhead={setPlayhead}
                  playing={playing}
                  onDropFiles={(fs)=>onDropFiles(fs)}
                  loop={loop}
                  setLoop={setLoop}
                  gridSec={gridSec}
                  onAutoSectionize={handleAutoSectionize}
                  pixelsPerBeat={gridPixelsPerBeat}
                  timeSignature={timeSig}
                  scrollSyncRef={timelineScrollRef}
                  selectedSectionIds={selectedSectionIds}
                  onSelectSection={(sectionId: string, multi: boolean) => {
                    if (!sectionId) {
                      // Empty string clears selection
                      setSelectedSectionIds(new Set());
                      setSelectedMeasureRange(null);
                      return;
                    }
                    if (multi) {
                      // Multi-select with Ctrl/Cmd key
                      const newSelected = new Set(selectedSectionIds);
                      if (newSelected.has(sectionId)) {
                        newSelected.delete(sectionId);
                      } else {
                        newSelected.add(sectionId);
                      }
                      setSelectedSectionIds(newSelected);
                      // Clear measure range for multi-select (drum builder needs single section)
                      setSelectedMeasureRange(null);
                    } else {
                      // Single select
                      setSelectedSectionIds(new Set([sectionId]));
                      
                      // Set measure range for drum builder
                      const section = sections.find(s => s.id === sectionId);
                      if (section) {
                        const measureRange = sectionToMeasureRange(section, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode);
                        setSelectedMeasureRange(measureRange);
                        console.log('🎯 Selected measure range:', measureRange);
                      }
                    }
                  }}
                />
              </div>

              {/* Musical Arrangement - Nested Below Waveform */}
              {sections.length > 0 && (
                <div className="border-t border-slate-800">
                  <SectionControls
                    sections={selectedSectionIds.size > 0 
                      ? sections.filter(s => selectedSectionIds.has(s.id))
                      : sections
                    }
                    onSectionsChange={setSections}
                    bpm={bpm}
                    timeSignature={timeSig}
                    currentTime={playhead}
                    trackKey={tracks[0]?.key}
                    onAnalyzeTempos={
                      tracks.length > 0
                        ? (sections) => analyzeSectionTempos(tracks[0]?.key, sections)
                        : undefined
                    }
                  />
                </div>
              )}
            </div>
            
            {/* Drum Editor + Limb Grid */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-3 text-sm text-slate-300">
                  <div className="font-semibold text-white">Drum Performance Editor</div>
                  {selectedMeasureRange && (
                    <div className="text-xs text-slate-400">
                      {selectedMeasureRange.sectionLabel} · {selectedMeasureRange.measureCount} bars
                    </div>
                  )}
                </div>
                {selectedMeasureRange ? (
                  activeDrumTrack ? (
                    <>
                      <div className="h-[520px]">
                        <DrumEditorPane
                          drumTrack={activeDrumTrack}
                          timeSignature={selectedMeasureRange.timeSignature ?? timeSig}
                          grooveWeights={activeGrooveMap}
                          gridResolution={gridResolution}
                          onGridResolutionChange={setGridResolution}
                          bpm={bpm}
                          playheadSeconds={playhead}
                          playing={playing}
                          drumEngine={drumEngineRef.current}
                          pixelsPerBeat={gridPixelsPerBeat}
                          visibleStartMeasure={selectedMeasureRange.startMeasure}
                          visibleMeasureCount={selectedMeasureRange.measureCount}
                          totalSongBars={totalSongBars}
                          sectionRegions={drumSectionRegions}
                          onUpdateTrack={(updatedTrack) => {
                            if (!activeSectionId || activeSectionId === "full-song") return;
                            setSectionDrumTracks((prev) => ({
                              ...prev,
                              [activeSectionId]: updatedTrack,
                            }));
                            syncSectionMidiNotes(activeSectionId, updatedTrack, activePlacementContext);
                          }}
                          pianoRollScrollRef={pianoRollScrollRef}
                        />
                      </div>
                    </>
                  ) : (
                    <div className="h-[200px] text-sm text-slate-400 flex flex-col items-center justify-center text-center px-4">
                      <div className="text-base text-slate-200 font-semibold mb-1">No drum data yet</div>
                      <p>
                        Run the Drum Builder for this section to unlock high-resolution editing, expressive
                        attributes, and limb-aware controls.
                      </p>
                    </div>
                  )
                ) : (
                  <div className="h-[200px] text-sm text-slate-400 flex items-center justify-center text-center px-4">
                    Select a section in the timeline to focus the editor.
                  </div>
                )}
              </div>

              {sections.length > 0 && (
                <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-slate-500">Drum Builder Console</p>
                      <p className="text-base font-semibold text-white">Dial in the virtual drummer before generating</p>
                    </div>
                    {selectedDrummer && (
                      <span className="text-[11px] px-2 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                        {selectedDrummer.style?.toUpperCase() || "CUSTOM"}
                      </span>
                    )}
                  </div>

                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">Virtual Drummer</p>
                        <p className="text-sm font-semibold text-white">
                          {selectedDrummer?.display_name || 'No drummer selected'}
                        </p>
                      </div>
                    </div>
                    <DrummerSelector
                      onSelect={(drummer) => {
                        setSelectedDrummer(drummer);
                        console.log('Selected drummer:', drummer.display_name);
                      }}
                      selectedDrummer={selectedDrummer}
                    />
                  </div>

                  <DrumOptionsPanel
                    options={drumOptions}
                    onChange={setDrumOptions}
                    drummerType={drumOptions.style}
                  />

                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">Tempo Flatten</p>
                        <p className="text-xs text-slate-400">Bar tempo range tolerance (BPM)</p>
                      </div>
                      <input
                        type="number"
                        min={0}
                        step={0.5}
                        value={tempoFlattenToleranceBpm}
                        onChange={(e) => {
                          const next = Number(e.target.value);
                          setTempoFlattenToleranceBpm(Number.isFinite(next) && next >= 0 ? next : 0);
                        }}
                        className="w-24 px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-100"
                      />
                    </div>
                  </div>

                  <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-[11px] uppercase tracking-wide text-slate-500">Drum Tempo Mode</p>
                        <p className="text-xs text-slate-400">Lock for steady tempo, Follow to use the detected tempo map.</p>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          className={
                            "px-2.5 py-1 rounded border text-xs " +
                            (drumTempoMode === "lock"
                              ? "bg-cyan-700/40 border-cyan-400/40 text-cyan-100"
                              : "bg-slate-900 border-slate-700 text-slate-300")
                          }
                          onClick={() => setDrumTempoMode("lock")}
                        >
                          Lock
                        </button>
                        <button
                          type="button"
                          className={
                            "px-2.5 py-1 rounded border text-xs " +
                            (drumTempoMode === "follow"
                              ? "bg-indigo-700/40 border-indigo-400/40 text-indigo-100"
                              : "bg-slate-900 border-slate-700 text-slate-300")
                          }
                          onClick={() => setDrumTempoMode("follow")}
                        >
                          Follow
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {sections.length > 0 && (
                <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="text-sm font-semibold text-white">
                        <HoverTip text="Generate limb-aware drums for the currently selected section range. Requires selecting a drummer persona first.">
                          <span>Section Drum Track Builder</span>
                        </HoverTip>
                      </h3>
                      <p className="text-xs text-slate-400">Uses the selected section or range to author limb-aware grooves.</p>
                    </div>
                    {selectedMeasureRange && (
                      <div className="text-xs text-slate-400">
                        {selectedMeasureRange.sectionLabel} · {selectedMeasureRange.measureCount} bars
                      </div>
                    )}
                  </div>
                  {selectedDrummer ? (
                    <DrumBuilderPanelV2
                      selectedRange={selectedMeasureRange}
                      onGenerate={handleGenerateDrums}
                      busy={generatingDrums}
                    />
                  ) : (
                    <div className="mt-2 rounded border border-yellow-500/30 bg-yellow-900/10 p-3 text-xs text-yellow-200 flex items-center justify-between gap-3">
                      <div>
                        Drum personality is required before generating.
                      </div>
                      <button
                        type="button"
                        className="px-3 py-1 rounded bg-amber-600 hover:bg-amber-500 text-xs font-semibold text-slate-950"
                        onClick={() => setShowDrummerPersonaModal(true)}
                      >
                        Choose Drum Personality
                      </button>
                    </div>
                  )}

                  <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="text-xs text-slate-400">MIDI Map</div>
                      <select
                        className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-100"
                        value={midiMapName}
                        onChange={(e) => setMidiMapName(e.target.value)}
                      >
                        <option value="Mixosaurus_EZ_Drummer">Mixosaurus (EZD/SD3)</option>
                        <option value="gm">GM</option>
                      </select>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-xs text-slate-400">Groove</div>
                      <select
                        className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-100"
                        value={grooveSource}
                        onChange={(e) => {
                          const next = e.target.value;
                          setGrooveSource(next);
                          if (next === "egmd_phrases") {
                            setGrooveMode("exact");
                          }
                        }}
                        disabled={isScratchWorkflow}
                      >
                        <option value="pattern">Built-in</option>
                        <option value="egmd_phrases">E-GMD Phrases</option>
                      </select>
                      {grooveSource === "egmd_phrases" && !isScratchWorkflow && (
                        <select
                          className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-100"
                          value={grooveMode}
                          onChange={(e) => setGrooveMode(e.target.value)}
                          title="E-GMD Playback Mode"
                        >
                          <option value="exact">Exact Clip</option>
                          <option value="enhanced">Enhanced</option>
                        </select>
                      )}
                      {grooveSource === "egmd_phrases" && (
                        <select
                          className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-100"
                          value={styleGroup}
                          onChange={(e) => setStyleGroup(e.target.value)}
                          disabled={isScratchWorkflow}
                        >
                          <option value="rock">Rock</option>
                          <option value="funk">Funk</option>
                          <option value="jazz">Jazz</option>
                          <option value="metal">Metal</option>
                          <option value="blues">Blues</option>
                          <option value="pop">Pop</option>
                          <option value="latin">Latin</option>
                          <option value="hiphop">Hip-Hop</option>
                          <option value="soul">Soul</option>
                        </select>
                      )}
                      {grooveSource === "egmd_phrases" && (
                        <select
                          className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-100"
                          value={selectedEgmdPhraseId === null ? "" : String(selectedEgmdPhraseId)}
                          onChange={(e) => {
                            const raw = e.target.value;
                            if (!raw) {
                              setSelectedEgmdPhraseId(null);
                              return;
                            }
                            const next = Number(raw);
                            setSelectedEgmdPhraseId(Number.isFinite(next) ? next : null);
                          }}
                          title="Select which EGMD clip to use for this style"
                        >
                          <option value="">Best Match</option>
                          {egmdPhraseOptions.map((p) => {
                            const filename = String(p.midi_path || "").split("\\").pop()?.split("/").pop() || "midi";
                            return (
                              <option key={String(p.phrase_id)} value={String(p.phrase_id)}>
                                #{String(p.phrase_id)} · {filename}
                              </option>
                            );
                          })}
                        </select>
                      )}
                    </div>
                    <button
                      className="px-3 py-1 rounded bg-emerald-700 hover:bg-emerald-600 text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={!lastGeneratedMidiBase64}
                      onClick={() => {
                        if (!lastGeneratedMidiBase64) return;
                        downloadMidiBase64(lastGeneratedMidiBase64, lastGeneratedMidiLabel || "DrumTracKAI-Drums");
                      }}
                      title={!lastGeneratedMidiBase64 ? "Generate drums first to enable MIDI download" : undefined}
                    >
                      Download MIDI
                    </button>
                  </div>

                  {grooveSource === "egmd_phrases" && lastEgmdPhraseInfo && (
                    <div className="mt-2 text-xs text-slate-400">
                      Selected phrase: #{String(lastEgmdPhraseInfo.phrase_id)} · {String(lastEgmdPhraseInfo.midi_path || '').split('\\').pop()}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Arrangement + Builder Console - Right Sidebar */}
          <div className="w-[360px] bg-slate-900 border-l border-slate-800 overflow-y-auto">
              {/* Header */}
              <div className="p-4 border-b border-slate-800 bg-indigo-900/20">
                <h2 className="text-lg font-bold text-white mb-1">🎼 Musical Arrangement Manager</h2>
                <p className="text-xs text-slate-400">Section detection and bar-level analysis</p>
              </div>
              
              {/* Source Info from Professional Tier */}
              {sourceInfo.source && (
                <div className="p-4 bg-blue-900/20 border-b border-blue-500/30">
                  <div className="text-xs text-blue-300 mb-1">Source: {sourceInfo.source}</div>
                  {sourceInfo.filename && (
                    <div className="text-sm text-white font-semibold">📁 {sourceInfo.filename}</div>
                  )}
                  {sourceInfo.drummer && (
                    <div className="text-sm text-white">🥁 {sourceInfo.drummer}</div>
                  )}
                </div>
              )}
              
              {/* Analysis Options */}
              {tracks.length > 0 && (
                <div className="p-4 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">
                    <HoverTip text="Choose how to create your song structure: analyze uploaded audio, or define a scratch arrangement. Analysis must complete before drum generation.">
                      <span>Arrangement Analysis</span>
                    </HoverTip>
                  </h3>
                  
                  {/* Current Arrangement Indicator */}
                  {arrangementSource && sections.length > 0 && (
                    <div className="mb-3 p-2 bg-blue-900/20 border border-blue-700/50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="text-xs font-semibold text-blue-300">📊 Current Arrangement:</div>
                          <div className="text-xs text-white mt-0.5">{arrangementSource}</div>
                          <div className="text-xs text-slate-400 mt-0.5">{sections.length} sections</div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Option 1: Auto-Analyze */}
                  <button 
                    className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 font-semibold text-white shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed mb-2"
                    onClick={() => handleAutoSectionize(tracks[0]?.key)}
                    disabled={busy}
                  >
                    {busy ? '⏳ Analyzing...' : '🎯 Auto-Analyze (AI)'}
                  </button>
                  <p className="text-xs text-slate-400 mb-3">Automatic detection of sections, bars, meter, and tempo</p>
                  
                  {/* Option 2: Manual Entry */}
                  <button 
                    className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 font-semibold text-white shadow-lg transition-all mb-2"
                    onClick={() => setShowManualModal(true)}
                  >
                    📝 Manual Entry
                  </button>
                  <p className="text-xs text-slate-400 mb-3">Define sections by measure count for your own songs</p>
                  
                  {/* Option 3: Well Known Song */}
                  <button 
                    className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 font-semibold text-white shadow-lg transition-all mb-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    onClick={() => setShowLookupModal(true)}
                    disabled={tracks.length === 0 || busy}
                    title={tracks.length === 0 ? 'Upload audio before running a Well Known Song lookup' : undefined}
                  >
                    🌐 Well Known Song
                  </button>
                  <p className="text-xs text-slate-400 mb-3">Search internet for tempo, time signature, and arrangement</p>
                  
                  {/* Manual Tempo Adjustment */}
                  {sections.length > 0 && songMap && (
                    <div className="mt-3 p-3 bg-slate-900/50 rounded-lg border border-slate-700">
                      <div className="flex items-center justify-between mb-2">
                        <label className="text-xs text-slate-300 font-semibold">Detected Tempo</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min="60"
                            max="200"
                            value={Math.round(bpm)}
                            onChange={(e) => setBpm(Math.max(60, Math.min(200, Number(e.target.value) || 120)))}
                            className="w-16 px-2 py-1 bg-slate-800 text-white text-sm rounded border border-slate-600 focus:border-indigo-500 focus:outline-none"
                          />
                          <span className="text-xs text-slate-400">BPM</span>
                        </div>
                      </div>
                      <div className="text-xs text-slate-500">
                        Auto-detected: {songMap.globalBpmEstimate?.toFixed(1)} BPM
                      </div>
                      <div className="text-xs text-amber-400 mt-1">
                        ⚠️ Adjust if tempo seems incorrect
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Upload prompt if no tracks */}
              {tracks.length === 0 && (
                <div className="p-4 border-b border-slate-800 space-y-3">
                  <div className="rounded-lg border border-slate-700 bg-slate-900/60 p-3">
                    <div className="text-xs text-slate-400 mt-1">
                      Set tempo, time signature, and an arrangement to generate drums without uploading audio.
                    </div>

                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-[11px] text-slate-400 mb-1">Tempo (BPM)</div>
                        <input
                          type="number"
                          min={40}
                          max={240}
                          value={bpm}
                          onChange={(e) => setBpm(Math.max(40, Math.min(240, Number(e.target.value) || 120)))}
                          className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                        />
                      </div>
                      <div>
                        <div className="text-[11px] text-slate-400 mb-1">Time Signature</div>
                        <select
                          className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                          value={`${timeSig[0]}/${timeSig[1]}`}
                          onChange={(e) => {
                            const [n, d] = e.target.value.split("/").map((v) => Number(v));
                            if (Number.isFinite(n) && Number.isFinite(d)) {
                              setTimeSig([n, d] as [number, number]);
                            }
                          }}
                        >
                          <option value="4/4">4/4</option>
                          <option value="3/4">3/4</option>
                          <option value="6/8">6/8</option>
                          <option value="5/4">5/4</option>
                          <option value="7/8">7/8</option>
                        </select>
                      </div>
                    </div>

                    <div className="mt-3">
                      <div className="text-[11px] text-slate-400 mb-1">Style</div>
                      <select
                        className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                        value={scratchStyle}
                        onChange={(e) => setScratchStyle(e.target.value)}
                      >
                        <option value="rock">Rock</option>
                        <option value="funk">Funk</option>
                        <option value="jazz">Jazz</option>
                        <option value="metal">Metal</option>
                        <option value="blues">Blues</option>
                        <option value="pop">Pop</option>
                        <option value="latin">Latin</option>
                      </select>
                    </div>

                    <div className="mt-3">
                      <div className="text-[11px] text-slate-400 mb-1">Groove</div>
                      <div className="grid grid-cols-2 gap-2">
                        <select
                          className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                          value={grooveSource}
                          onChange={(e) => {
                            const next = e.target.value;
                            setGrooveSource(next);
                            if (next === "egmd_phrases") {
                              setGrooveMode("exact");
                            }
                          }}
                          disabled={isScratchWorkflow}
                        >
                          <option value="pattern">Built-in</option>
                          <option value="egmd_phrases">E-GMD Phrases</option>
                        </select>
                        {grooveSource === "egmd_phrases" ? (
                          <div className="grid grid-cols-2 gap-2">
                            {!isScratchWorkflow ? (
                              <select
                                className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                                value={grooveMode}
                                onChange={(e) => setGrooveMode(e.target.value)}
                                title="E-GMD Playback Mode"
                              >
                                <option value="exact">Exact Clip</option>
                                <option value="enhanced">Enhanced</option>
                              </select>
                            ) : (
                              <div className="w-full px-2 py-1 bg-slate-800 text-slate-300 text-sm rounded border border-slate-700">
                                Exact Clip
                              </div>
                            )}
                            <select
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={styleGroup}
                              onChange={(e) => setStyleGroup(e.target.value)}
                              title="E-GMD Style Group"
                              disabled={isScratchWorkflow}
                            >
                              <option value="rock">Rock</option>
                              <option value="funk">Funk</option>
                              <option value="jazz">Jazz</option>
                              <option value="metal">Metal</option>
                              <option value="blues">Blues</option>
                              <option value="pop">Pop</option>
                              <option value="latin">Latin</option>
                              <option value="hiphop">Hip-Hop</option>
                              <option value="soul">Soul</option>
                            </select>
                          </div>
                        ) : (
                          <div className="w-full" />
                        )}
                      </div>
                      {grooveSource === "egmd_phrases" && (
                        <div className="mt-2">
                          <select
                            className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                            value={selectedEgmdPhraseId === null ? "" : String(selectedEgmdPhraseId)}
                            onChange={(e) => {
                              const raw = e.target.value;
                              if (!raw) {
                                setSelectedEgmdPhraseId(null);
                                return;
                              }
                              const next = Number(raw);
                              setSelectedEgmdPhraseId(Number.isFinite(next) ? next : null);
                            }}
                            title="Select which EGMD clip to use for this style"
                          >
                            <option value="">Best Match</option>
                            {egmdPhraseOptions.map((p) => {
                              const filename = String(p.midi_path || "").split("\\").pop()?.split("/").pop() || "midi";
                              return (
                                <option key={String(p.phrase_id)} value={String(p.phrase_id)}>
                                  #{String(p.phrase_id)} · {filename}
                                </option>
                              );
                            })}
                          </select>
                        </div>
                      )}
                      {grooveSource === "egmd_phrases" && (
                        <div className="mt-1 text-[11px] text-slate-500">E-GMD Style Group</div>
                      )}
                    </div>

                    <div className="mt-3">
                      <div className="flex items-center justify-between">
                        <div className="text-[11px] text-slate-400">Arrangement (Section + Bars)</div>
                        <button
                          className="px-2 py-1 text-[11px] rounded bg-slate-800 border border-slate-700 text-slate-200"
                          onClick={() => setScratchArrangement((prev) => [...prev, { label: "verse", bars: 8 }])}
                        >
                          Add
                        </button>
                      </div>
                      <div className="mt-2 space-y-2">
                        {scratchArrangement.map((row, idx) => (
                          <div key={`${idx}-${row.label}`} className="grid grid-cols-[1fr_72px_28px] gap-2 items-center">
                            <select
                              className="px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={row.label}
                              onChange={(e) => {
                                const v = e.target.value;
                                setScratchArrangement((prev) =>
                                  prev.map((r, i) => (i === idx ? { ...r, label: v } : r)),
                                );
                              }}
                            >
                              {SCRATCH_SECTION_LABEL_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                            <input
                              type="number"
                              min={1}
                              max={64}
                              value={row.bars}
                              onChange={(e) => {
                                const v = Math.max(1, Math.min(64, Number(e.target.value) || 1));
                                setScratchArrangement((prev) =>
                                  prev.map((r, i) => (i === idx ? { ...r, bars: v } : r)),
                                );
                              }}
                              className="px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                            />
                            <button
                              className="h-7 rounded bg-rose-900/40 border border-rose-800 text-rose-200"
                              onClick={() => setScratchArrangement((prev) => prev.filter((_, i) => i !== idx))}
                              title="Remove"
                            >
                              ×
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    <button
                      className="mt-3 w-full px-3 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-sm font-semibold"
                      onClick={() => {
                        setDrumOptions((prev) => ({ ...prev, bpm, style: scratchStyle }));
                        buildScratchSong();
                      }}
                    >
                      Create Arrangement
                    </button>

                    <div className="mt-2 text-[11px] text-slate-500">
                      After creating the arrangement, click a section in the timeline and use the Drum Builder.
                    </div>
                  </div>
                </div>
              )}
              
              
              <div className="p-4 border-b border-slate-800 space-y-2">
                <div>
                  <h3 className="text-sm font-semibold text-slate-100">
                    <HoverTip text="Generate a full-song drum performance. You must select a drummer persona first.">
                      <span>Create Drum Track</span>
                    </HoverTip>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Generate a cohesive drum performance across the full arrangement, or clear the arrangement and patterns.
                  </p>
                </div>
                <button
                  onClick={() => {
                    if (!selectedDrummer) {
                      setShowDrummerPersonaModal(true);
                      return;
                    }
                    handleGenerateFullSong();
                  }}
                  disabled={!sections.length || bulkGenerating || generatingDrums}
                  className="w-full px-4 py-2.5 rounded-lg bg-gradient-to-r from-orange-600 to-rose-600 hover:from-orange-500 hover:to-rose-500 font-semibold text-white shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  title={!sections.length ? "Add an arrangement first" : !selectedDrummer ? "Select a drummer persona first" : undefined}
                >
                  {bulkGenerating ? '⏳ Building Entire Song…' : '🥁 Generate Entire Song'}
                </button>
                {fullSongStatus && (
                  <div
                    className={`text-xs px-3 py-2 rounded border ${
                      fullSongStatus.type === 'success'
                        ? 'bg-emerald-900/10 text-emerald-200 border-emerald-400/40'
                        : fullSongStatus.type === 'error'
                          ? 'bg-rose-900/10 text-rose-200 border-rose-400/40'
                          : 'bg-cyan-900/10 text-cyan-200 border-cyan-400/40'
                    }`}
                  >
                    <span>{fullSongStatus.message}</span>
                    {fullSongStatus.type === 'progress' && fullSongProgress.total > 0 && (
                      <span className="ml-2 text-slate-200">
                        {fullSongProgress.completed}/{fullSongProgress.total} sections
                      </span>
                    )}
                  </div>
                )}
                <button
                  onClick={clearArrangement}
                  className="w-full px-4 py-2 rounded-lg bg-red-600/25 hover:bg-red-600/40 text-red-200 text-sm font-semibold border border-red-500/30 transition-colors"
                  title="Clear arrangement sections and all generated drum patterns/grids"
                >
                  🗑️ Clear Arrangement + Patterns
                </button>
              </div>

              {/* Brain Panel UI */}
              {sections.length > 0 && (
                <div className="p-4 border-b border-slate-800">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">🧠 Brain Panel</h3>
                  <BrainPanel
                    sectionId={selectedMeasureRange?.sectionId}
                    sectionLabel={selectedMeasureRange?.sectionLabel}
                    styleHint={drumOptions.style}
                    locked={false}
                  />
                </div>
              )}

              {sections.length > 0 && (
                <div>
                  {/* Selection Info & Actions */}
                  {selectedSectionIds.size > 0 ? (
                    <div className="p-4 bg-gradient-to-r from-indigo-900/40 to-purple-900/40 border-b border-indigo-500/30">
                      <div className="text-sm text-indigo-200 font-semibold mb-3">
                        ✨ {selectedSectionIds.size} section{selectedSectionIds.size > 1 ? 's' : ''} selected
                      </div>
                      <div className="space-y-2 text-xs text-slate-200">
                        <p className="leading-relaxed">
                          Use the Drum Builder panel in the center column to generate patterns for the highlighted
                          sections. The older quick-generate path has been removed so there is a single source of
                          truth for drum creation.
                        </p>
                        <button
                          className="text-indigo-300 hover:text-indigo-100 underline"
                          onClick={() => setSelectedSectionIds(new Set())}
                        >
                          Clear selection (show all)
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 bg-yellow-900/20 border-b border-yellow-500/30">
                      <div className="text-xs text-yellow-300">
                        💡 Click sections on timeline to select them
                      </div>
                    </div>
                  )}
                  
                  {/* SectionControls moved to be nested under waveform in center column */}
                </div>
              )}
            </div>
        </div>
      </div>
      {debugMode && (
        <div className="fixed bottom-3 right-3 max-w-md text-xs bg-slate-900/95 border border-emerald-500/40 rounded-lg p-3 shadow-xl z-50 space-y-3">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-emerald-300">DrumGen Debug</span>
            <div className="flex items-center gap-2">
              <button
                className="px-2 py-[1px] text-[10px] border border-emerald-500/60 rounded hover:bg-emerald-600/20"
                onClick={injectDebugTestGroove}
              >
                Inject Test Groove
              </button>
              <button
                className="text-slate-400 hover:text-slate-100"
                onClick={() => setDebugMode(false)}
              >
                ✕
              </button>
            </div>
          </div>
          <div className="border border-slate-800/60 rounded p-2">
            <div className="font-semibold text-slate-200 mb-1">Last Generation</div>
            {debugDrumGen ? (
              <div className="space-y-1">
                <div>sectionId: <span className="text-emerald-200">{debugDrumGen.payloadSectionId ?? "∅"}</span></div>
                <div>drum_track: {debugDrumGen.hasDrumTrack ? "yes" : "no"}</div>
                <div>drum_track notes: {debugDrumGen.drumTrackNotes}</div>
                <div>legacy midi_notes: {debugDrumGen.hasLegacyNotes ? "yes" : "no"}</div>
                <div>legacy note count: {debugDrumGen.legacyNotesCount}</div>
              </div>
            ) : (
              <div className="text-slate-500">No generation run yet.</div>
            )}
          </div>
          <div>
            <div className="font-semibold text-slate-200 mb-1">Section Tracks</div>
            {sectionDebugSummaries.length === 0 ? (
              <div className="text-slate-500">No sectionDrumTracks yet.</div>
            ) : (
              <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                {sectionDebugSummaries.map((summary) => (
                  <div
                    key={summary.id}
                    className="border border-slate-700/70 rounded px-2 py-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-emerald-200">{summary.id}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400">{summary.noteCount} notes</span>
                        <button
                          className="px-1 py-[1px] text-[10px] border border-emerald-500/60 rounded hover:bg-emerald-600/20"
                          onClick={() => handleDebugJumpToSection(summary.id)}
                        >
                          Jump
                        </button>
                      </div>
                    </div>
                    <div className="text-slate-400">
                      bars: {summary.minBar === null || summary.maxBar === null ? "–" : `${summary.minBar} → ${summary.maxBar}`}
                    </div>
                    {summary.instruments.length > 0 && (
                      <div className="text-slate-500 truncate">
                        inst: {summary.instruments.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Modals */}
      <ManualArrangementModal
        isOpen={showManualModal}
        onClose={() => setShowManualModal(false)}
        onSubmit={handleManualArrangement}
        duration={tracks[0]?.seconds || 240}
      />
      
      <InternetSongLookupModal
        isOpen={showLookupModal}
        onClose={() => setShowLookupModal(false)}
        onSelect={handleSongLookup}
      />

      <DrumPlayerModal isOpen={showDrumPlayer} onClose={() => setShowDrumPlayer(false)} />

      <DrummerPersonaModal
        open={showDrummerPersonaModal}
        onClose={() => setShowDrummerPersonaModal(false)}
        selectedDrummer={selectedDrummer}
        onSelect={(drummer) => {
          setSelectedDrummer(drummer);
        }}
      />
    </div>
  );
}
