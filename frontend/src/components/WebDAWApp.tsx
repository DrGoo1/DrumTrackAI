import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { GridResolution, getTicksPerSubdivision, getSubdivisionsPerBar } from "../utils/pianoRollGrid";
import { inferLimbFromInstrument, inferLimbFromLane, type LimbId } from "../constants/limbs";
import { DrumPianoRoll, type DrumSectionRegion } from "./drums/DrumPianoRoll";
import { useMidi } from "../midi/midiStore";
import type { MidiClip, MidiNote as MidiClipNote } from "../midi/types";
import { getMidiPitchForInstrument } from "../utils/drumTrackUtils";
import {
  applyDrumGenerationResult,
  DrumGenerationDebugSnapshot,
  DrumTrackPlacementContext,
} from "./drumGenerationHandlers";
import StylometerFlower, { type StylometerValues } from "./StylometerFlower";
import { GROOVE_WEIGHT_PRESETS } from "../types/grooveWeight";
import { NoteInspector } from "./drums/NoteInspector";
import { Tooltip } from "./Tooltip";
import {
  attachSentientProfilesWithOverrides,
  getSentientProfileSessionState,
  preloadSentientProfile,
  subscribeSentientProfileSession,
  type SentientProfileEntry,
} from "../api/sentientProfileSession";
import { sentientProfileBadge } from "../utils/sentientUi";
import SentientDebugPanel from "./SentientDebugPanel";
import { buildSentientDebugState } from "../utils/sentientDebugState";

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
    <div className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-xl max-h-[85vh] overflow-hidden rounded-xl border border-slate-700 bg-slate-950 shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-800 p-4">
          <div>
            <div className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-amber-300 via-fuchsia-400 to-purple-400 bg-clip-text text-transparent">
              Choose Your Drummer!
            </div>
          </div>
          <Tooltip content="Close" placement="top" maxWidthClassName="w-20">
            <button
              className="text-slate-400 hover:text-slate-100"
              onClick={onClose}
              type="button"
            >
              ✕
            </button>
          </Tooltip>
        </div>

        <div className="p-4 space-y-3 overflow-y-auto max-h-[calc(85vh-64px)]">
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200 leading-relaxed">
            DrumTracKAI has analyzed signature drum tracks from famous drummers to determine the specific stylistic
            nuances that make them special, and incorporated these techniques into focused stylistic profiles.
            <div className="mt-2">
              Each profile represents a combination of multiple drummer styles from similar genres.
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

const MacroSlider = ({
  value,
  onChange,
  ariaLabel,
}: {
  value: number;
  onChange: (next: number) => void;
  ariaLabel: string;
}) => {
  const sliderRef = React.useRef<HTMLDivElement | null>(null);
  const pointerRef = React.useRef<number | null>(null);

  const updateFromClientX = React.useCallback(
    (clientX: number) => {
      const rect = sliderRef.current?.getBoundingClientRect();
      if (!rect) return;
      const ratio = clamp01((clientX - rect.left) / rect.width);
      onChange(Number(ratio.toFixed(4)));
    },
    [onChange],
  );

  const finishDrag = React.useCallback(() => {
    if (pointerRef.current !== null && sliderRef.current) {
      try {
        sliderRef.current.releasePointerCapture(pointerRef.current);
      } catch {
        // ignore
      }
    }
    pointerRef.current = null;
  }, []);

  return (
    <div
      ref={sliderRef}
      role="slider"
      tabIndex={0}
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={Number(value.toFixed(3))}
      className="relative w-full h-6 cursor-pointer select-none focus:outline-none focus:ring-2 focus:ring-cyan-400/70 rounded"
      style={{ touchAction: "none" }}
      onPointerDown={(e) => {
        e.preventDefault();
        pointerRef.current = e.pointerId;
        e.currentTarget.setPointerCapture(e.pointerId);
        updateFromClientX(e.clientX);
      }}
      onPointerMove={(e) => {
        if (pointerRef.current !== e.pointerId) return;
        e.preventDefault();
        updateFromClientX(e.clientX);
      }}
      onPointerUp={(e) => {
        if (pointerRef.current !== e.pointerId) return;
        finishDrag();
      }}
      onPointerCancel={(e) => {
        if (pointerRef.current !== e.pointerId) return;
        finishDrag();
      }}
      onKeyDown={(e) => {
        if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
        e.preventDefault();
        const dir = e.key === "ArrowRight" ? 1 : -1;
        const step = e.shiftKey ? 0.05 : 0.01;
        onChange(clamp01(value + dir * step));
      }}
    >
      <div
        className="absolute top-1/2 left-0 right-0 h-1 bg-slate-700/80 rounded-full pointer-events-none"
        style={{ transform: "translateY(-50%)" }}
      />
      <div
        className="absolute top-1/2 left-0 h-1 bg-cyan-400 rounded-full pointer-events-none"
        style={{ width: `${clamp01(value) * 100}%`, transform: "translateY(-50%)" }}
      />
      <div
        className="absolute top-1/2 h-3 w-3 rounded-full bg-white border border-cyan-400 shadow-[0_0_6px_rgba(34,211,238,0.7)] pointer-events-none"
        style={{ left: `calc(${clamp01(value) * 100}% - 6px)`, transform: "translateY(-50%)" }}
      />
    </div>
  );
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
  const [sectionGenConfigs, setSectionGenConfigs] = useState<Record<string, DrumGenerationConfig>>({});
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
  const [selectedBarIndex, setSelectedBarIndex] = useState<number | null>(null);
  const [miniSelectedNoteIds, setMiniSelectedNoteIds] = useState<string[]>([]);
  const [barClipboard, setBarClipboard] = useState<DrumNoteEvent[] | null>(null);
  const [barAddInstrumentId, setBarAddInstrumentId] = useState<DrumInstrumentId>("snare_center");
  const [barAddStepIndex, setBarAddStepIndex] = useState<number>(0);

  const stylometerSongBaselineRef = useRef<{ style: string; drummerStyle: string } | null>(null);
  const stylometerSectionBaselineRef = useRef<Record<string, { style: string; drummerStyle: string }>>({});

  const [stylometerOpen, setStylometerOpen] = useState<boolean>(false);
  const [stylometerPos, setStylometerPos] = useState<{ x: number; y: number }>({ x: 24, y: 72 });
  const stylometerDragRef = useRef<
    | {
        pointerId: number;
        offsetX: number;
        offsetY: number;
      }
    | null
  >(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const onKeyDown = (ev: KeyboardEvent) => {
      if (ev.key !== "s" && ev.key !== "S") return;

      const target = ev.target as HTMLElement | null;
      const tag = (target?.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || (target as any)?.isContentEditable) {
        return;
      }

      ev.preventDefault();
      setStylometerOpen((v) => !v);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

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
  const [sentientState, setSentientState] = useState<SentientProfileEntry | null>(null);
  const [gridResolution, setGridResolution] = useState<GridResolution>("16th");
  const [gridPixelsPerBeat, setGridPixelsPerBeat] = useState(80);
  const [scrollPercent, setScrollPercent] = useState(0);

  const sentientBadge = useMemo(() => sentientProfileBadge(sentientState), [sentientState]);

  useEffect(() => {
    const id = selectedDrummer?.id;
    if (!id) return;
    void preloadSentientProfile(id);
  }, [selectedDrummer?.id]);

  useEffect(() => {
    const id = selectedDrummer?.id ?? "";
    if (!id) {
      setSentientState(null);
      return;
    }
    setSentientState(getSentientProfileSessionState(id));
    const unsub = subscribeSentientProfileSession((entry) => {
      if (entry.drummerId === id) setSentientState(entry);
    });
    return unsub;
  }, [selectedDrummer?.id]);

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
  const drumPlaybackStartCtxSecRef = useRef<number>(0);
  const drumPlaybackStartPlayheadSecRef = useRef<number>(0);
  const playheadClockModeRef = useRef<"engine" | "raf">("engine");

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

    const builtInDefaults: Record<DrumPlayerChannelId, string> = {
      kick: "/samples/drums/kick.wav",
      kick_sub: "/samples/drums/kick.wav",
      snare_top: "/samples/drums/snare.wav",
      snare_bottom: "/samples/drums/snare.wav",
      tom1: "/samples/drums/tom.wav",
      tom2: "/samples/drums/tom.wav",
      tom3: "/samples/drums/tom.wav",
      tom4: "/samples/drums/tom.wav",
      tom5: "/samples/drums/tom.wav",
      tom_fx: "/samples/drums/tom.wav",
      hat: "/samples/drums/hihat.wav",
      ride: "/samples/drums/ride.wav",
      spot_ride: "/samples/drums/ride.wav",
      crash: "/samples/drums/crash.wav",
    };

    const hasAnySavedMapping = Object.keys(map).length > 0;
    const requiredChannels: DrumPlayerChannelId[] = [
      "kick",
      "snare_top",
      "hat",
      "tom1",
      "ride",
      "crash",
    ];
    const missingRequired = requiredChannels.some((ch) => !(ch in map));

    // If the user hasn't picked a kit yet (or mapping is partial), load a built-in kit
    // so EGMD playback is audible on all core instruments.
    if (!hasAnySavedMapping || missingRequired) {
      for (const [ch, url] of Object.entries(builtInDefaults)) {
        const channel = ch as DrumPlayerChannelId;
        if (drumLoadedRef.current[channel] === -1) continue;
        await eng.loadSampleForChannel(channel, url);
        drumLoadedRef.current[channel] = -1;
      }
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

  type SectionGrooveOverrides = {
    grooveSource?: string;
    grooveMode?: string;
    styleGroup?: string;
    selectedEgmdPhraseId?: number | null;
    egmdOverrideMode?: 'single' | 'by_type' | 'by_index';
    egmdPhraseByType?: Record<string, number>;
    egmdPhraseByIndex?: Record<string, number>;
  };

  const [grooveSource, setGrooveSource] = useState<string>("pattern");
  const [grooveMode, setGrooveMode] = useState<string>("enhanced");
  const [styleGroup, setStyleGroup] = useState<string>("rock");
  const [lastEgmdPhraseInfo, setLastEgmdPhraseInfo] = useState<any | null>(null);

  const sentientDebugState = useMemo(
    () => buildSentientDebugState(sentientState?.profile, lastEgmdPhraseInfo),
    [sentientState?.profile, lastEgmdPhraseInfo],
  );

  const [sectionGrooveOverrides, setSectionGrooveOverrides] = useState<Record<string, SectionGrooveOverrides>>({});

  // EGMD clip picker state/effects are declared further below (after arrangementSource)

  const syncSectionMidiNotes = useCallback(
    (sectionId: string, track: DrumTrackForDCSM, overridePlacement?: DrumTrackPlacementContext) => {
      if (!sectionId || !track?.notes?.length) {
        return;
      }
      const placement = overridePlacement ?? sectionPlacementContexts[sectionId];
      const midiNotes = convertTrackToMidiNotes(track, placement);
      const nextIds = midiNotes.map((note) => note.id);
      setNotes((prev) => {
        const existingIds = new Set(sectionNoteIdsRef.current[sectionId] ?? []);
        const preserved = existingIds.size ? prev.filter((note) => !existingIds.has(note.id)) : prev;
        return [...preserved, ...midiNotes];
      });

      // Update the ref after we used it to compute the preserved set.
      // This prevents the replacement pass from accidentally preserving old notes.
      sectionNoteIdsRef.current = {
        ...sectionNoteIdsRef.current,
        [sectionId]: nextIds,
      };
      setSectionNoteIds((prev) => ({
        ...prev,
        [sectionId]: nextIds,
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

  const openDrummerPersonaModal = useCallback(() => {
    console.log('[DCSM] Opening Drummer Persona modal');
    setShowManualModal(false);
    setShowLookupModal(false);
    setShowDrumPlayer(false);
    setShowDrummerPersonaModal(true);
  }, [setShowManualModal, setShowLookupModal, setShowDrumPlayer]);
  
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

  const [egmdOverrideMode, setEgmdOverrideMode] = useState<'single' | 'by_type' | 'by_index'>('single');
  const [egmdPhraseByType, setEgmdPhraseByType] = useState<Record<string, number>>({});
  const [egmdPhraseByIndex, setEgmdPhraseByIndex] = useState<Record<string, number>>({});

  const resolveGrooveSettings = useCallback(
    (sectionId?: string | null) => {
      const ov = sectionId ? sectionGrooveOverrides?.[sectionId] ?? null : null;
      const effGrooveSource = (ov?.grooveSource ?? grooveSource) as string;
      const effGrooveMode = (ov?.grooveMode ?? grooveMode) as string;
      const effStyleGroup = (ov?.styleGroup ?? styleGroup) as string;
      const effPhraseId =
        typeof ov?.selectedEgmdPhraseId !== "undefined" ? ov.selectedEgmdPhraseId : selectedEgmdPhraseId;
      const effOverrideMode = (ov?.egmdOverrideMode ?? egmdOverrideMode) as 'single' | 'by_type' | 'by_index';
      const effByType = ov?.egmdPhraseByType ?? egmdPhraseByType;
      const effByIndex = ov?.egmdPhraseByIndex ?? egmdPhraseByIndex;
      return {
        grooveSource: effGrooveSource,
        grooveMode: effGrooveMode,
        styleGroup: effStyleGroup,
        selectedEgmdPhraseId: effPhraseId,
        egmdOverrideMode: effOverrideMode,
        egmdPhraseByType: effByType,
        egmdPhraseByIndex: effByIndex,
      };
    },
    [
      egmdOverrideMode,
      egmdPhraseByIndex,
      egmdPhraseByType,
      grooveMode,
      grooveSource,
      sectionGrooveOverrides,
      selectedEgmdPhraseId,
      styleGroup,
    ],
  );

  const applyTrackToMidiClip = useCallback(
    (
      sectionId?: string | null,
      track?: DrumTrackForDCSM | null,
      legacyNotes?: any[] | null,
      placement?: DrumTrackPlacementContext,
    ) => {
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
        const resolved = resolveGrooveSettings(sectionId);
        updates.disableGrooveShaping =
          resolved.grooveSource === "egmd_phrases" && String(resolved.grooveMode || "").toLowerCase() === "exact";
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
      resolveGrooveSettings,
    ],
  );

  const isScratchEntry = tracks.length === 0;
  const isScratchWorkflow = arrangementSource === "scratch" || isScratchEntry;

  useEffect(() => {
    if (!isScratchWorkflow) return;
    // Scratch workflow: default to EGMD phrases, but allow groove mode selection.
    if (grooveSource !== "egmd_phrases") {
      setGrooveSource("egmd_phrases");
    }
  }, [isScratchWorkflow, grooveSource]);

  useEffect(() => {
    if (grooveSource !== "egmd_phrases") {
      setEgmdPhraseOptions([]);
      setSelectedEgmdPhraseId(null);
      setEgmdOverrideMode('single');
      setEgmdPhraseByType({});
      setEgmdPhraseByIndex({});
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

  const ensureSectionSelection = useCallback(
    (sectionId?: string | null) => {
      if (!sectionId) return;
      setSelectedSectionIds(new Set([sectionId]));
      const targetSection = sections.find((s) => s.id === sectionId) || null;
      if (targetSection) {
        const nextRange = sectionToMeasureRange(
          targetSection,
          bpm,
          timeSig,
          songMap,
          tempoFlattenToleranceBpm,
          drumTempoMode,
        );
        if (nextRange) {
          setSelectedMeasureRange(nextRange);
        }
      }
    },
    [
      sections,
      bpm,
      timeSig,
      songMap,
      tempoFlattenToleranceBpm,
      drumTempoMode,
      setSelectedSectionIds,
      setSelectedMeasureRange,
    ],
  );

  const handleClearAudio = useCallback(() => {
    const confirmed = window.confirm('Clear all uploaded audio tracks?');
    if (!confirmed) return;
    setTracks([]);
    setSections([]);
    setNotes([]);
    setSongMap(null);
    setSelectedSectionIds(new Set());
    setSelectedMeasureRange(null);
    setArrangementSource(null);
  }, [setTracks, setSections, setNotes, setSongMap, setSelectedSectionIds, setSelectedMeasureRange, setArrangementSource]);

  const injectDebugTestGroove = useCallback(() => {
    console.log('[DrumGenDebug] injectDebugTestGroove requested');
  }, []);

  const sectionDebugSummaries = useMemo(() => {
    const summaries: Array<{
      id: string;
      noteCount: number;
      minBar: number | null;
      maxBar: number | null;
      instruments: string[];
    }> = [];
    for (const [sectionId, track] of Object.entries(sectionDrumTracks || {})) {
      const events: any[] = Array.isArray((track as any)?.events) ? (track as any).events : [];
      const noteCount = events.length;
      let minBar: number | null = null;
      let maxBar: number | null = null;
      const instruments = new Set<string>();
      for (const e of events) {
        const barIndex = typeof e?.barIndex === 'number' ? e.barIndex : null;
        if (barIndex !== null) {
          minBar = minBar === null ? barIndex : Math.min(minBar, barIndex);
          maxBar = maxBar === null ? barIndex : Math.max(maxBar, barIndex);
        }
        if (typeof e?.instrument_id === 'string') instruments.add(e.instrument_id);
        if (typeof e?.instrumentId === 'string') instruments.add(e.instrumentId);
      }
      summaries.push({
        id: sectionId,
        noteCount,
        minBar,
        maxBar,
        instruments: Array.from(instruments).slice(0, 10),
      });
    }
    summaries.sort((a, b) => a.id.localeCompare(b.id));
    return summaries;
  }, [sectionDrumTracks]);
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

  const hasGeneratedDrums = useMemo(() => {
    if (fullSongDrumTrack?.notes?.length) return true;
    return Object.entries(sectionDrumTracks ?? {}).some(([id, track]) => {
      if (id === "__global__") return false;
      if (!track) return false;
      return Array.isArray(track.notes) && track.notes.length > 0;
    });
  }, [fullSongDrumTrack, sectionDrumTracks]);

  const scheduleDrumsBetween = useCallback(
    async (fromSec: number, toSec: number) => {
      const eng = drumEngineRef.current;
      const track = activeDrumTrackRef.current;
      if (!eng || !track) return;
      if (!Array.isArray(track.notes) || track.notes.length === 0) return;
      if (!(bpm > 0)) return;

      // Align drum scheduling to the same clock as the cursor: Engine's currentTime.
      // We schedule into the drum AudioContext relative to "now".
      const ctx = eng.audioContext;
      if (!ctx) return;
      const ctxNow = ctx.currentTime;

      // If we don't have a running HTML5 audio clock (no stems loaded), fall back
      // to playhead seconds which advances via RAF.
      const engineNow =
        playheadClockModeRef.current === "engine"
          ? Engine.getCurrentTimeSeconds()
          : toSec;

      const beatsPerBarLocal = (timeSig?.[0] ?? 4) || 4;
      const ticksPerBeat = track.resolution_ppq || 960;
      const ticksPerBarLocal = ticksPerBeat * beatsPerBarLocal;

      const beatTimes = Array.isArray(songMap?.beatTimes) ? songMap!.beatTimes! : [];
      const tempoPts = Array.isArray(midiSong?.tempoMap)
        ? midiSong.tempoMap
            .map((p: any) => ({ tSec: Number(p?.tSec) || 0, bpm: Number(p?.bpm) || 0 }))
            .filter((p: any) => Number.isFinite(p.tSec) && Number.isFinite(p.bpm) && p.bpm > 0)
            .sort((a: any, b: any) => a.tSec - b.tSec)
        : [];

      const timeAtBeats = (beatsIn: number): number => {
        const beats = Math.max(0, Number.isFinite(beatsIn) ? beatsIn : 0);

        // Prefer beatTimes (authoritative from analysis/align).
        if (beatTimes.length >= 2) {
          const maxIdx = beatTimes.length - 1;
          const idx0 = Math.max(0, Math.min(maxIdx, Math.floor(beats)));
          const idx1 = Math.max(0, Math.min(maxIdx, idx0 + 1));
          const t0 = Number(beatTimes[idx0] ?? 0);
          const t1 = Number(beatTimes[idx1] ?? t0);
          const frac = Math.max(0, Math.min(1, beats - idx0));
          if (idx0 === idx1) return Number.isFinite(t0) ? t0 : 0;
          if (!Number.isFinite(t0) || !Number.isFinite(t1)) return Number.isFinite(t0) ? t0 : 0;
          return t0 + (t1 - t0) * frac;
        }

        // Otherwise use tempo map (piecewise-constant bpm segments).
        if (tempoPts.length >= 1) {
          let remaining = beats;
          for (let i = 0; i < tempoPts.length; i++) {
            const cur = tempoPts[i];
            const next = tempoPts[i + 1];
            const span = next ? Math.max(0, next.tSec - cur.tSec) : Number.POSITIVE_INFINITY;
            const segBeats = (span / 60) * cur.bpm;
            if (remaining <= segBeats) {
              return cur.tSec + (remaining * 60) / cur.bpm;
            }
            remaining -= segBeats;
          }
          const last = tempoPts[tempoPts.length - 1];
          return last.tSec + (remaining * 60) / last.bpm;
        }

        // Final fallback: constant bpm.
        return (beats * 60) / bpm;
      };

      for (const n of track.notes) {
        const bar = n.barIndex ?? 0;
        const tick = n.tickInBar ?? 0;
        const totalTicks = bar * ticksPerBarLocal + tick;
        const beats = totalTicks / ticksPerBeat;
        const tSec = timeAtBeats(beats);
        if (tSec < fromSec || tSec >= toSec) continue;
        const ch = instrumentToChannel(n.instrumentId as any);
        if (!ch) continue;

        // Schedule relative to current Engine time so the hit occurs when the cursor reaches tSec.
        const delta = tSec - engineNow;
        const whenSec = ctxNow + delta;
        const safeWhen = Math.max(ctxNow + 0.002, whenSec);

        eng.playChannelOneShot(ch, {
          whenSec: safeWhen,
          gain: Math.max(0.2, Math.min(1.5, (n.velocity ?? 100) / 100)),
        });
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

  useEffect(() => {
    // Reset bar scope selection when section changes.
    setSelectedBarIndex(null);
    setMiniSelectedNoteIds([]);
  }, [activeSectionId]);

  useEffect(() => {
    setMiniSelectedNoteIds([]);
  }, [selectedBarIndex]);
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
    bpm: 120, bars: 8, density: 0.7, swing: 0, humanize: 0.55,
    style: 'rock', label: 'verse', swing_preset: 'off', vel_preset: 'accent24', fill_preset: 'random',
    drum_velocity: 0.85, cymbal_velocity: 0.70, kick_velocity: 0.90, snare_velocity: 0.85,
    tom_velocity: 0.80, hihat_velocity: 0.65, crash_velocity: 0.90, ride_velocity: 0.70,
    drum_density: 0.7, cymbal_density: 0.6, hihat_density: 0.8, ride_density: 0.4, crash_density: 0.2,
    fill_density: 0.7, fill_location: 'end', fill_frequency: 0.25,
    hihat_complexity: 0.5, hihat_pattern: 'eighths', hihat_open_ratio: 0.2, hihat_ghost_notes: 0.3,
    ride_complexity: 0.4, ride_pattern: 'quarters', ride_vs_hihat_ratio: 0.3, ride_bell_ratio: 0.1,
    bass_line_mode: 'auto', bass_kick_sync: 0.7, bass_lock_downbeats: true,
    tom_usage: 0.3, crash_frequency: 0.2, ghost_note_density: 0.35, dynamic_range: 0.65
  });

  useEffect(() => {
    // Capture a baseline as soon as we have a style (and optionally a drummer).
    // This keeps the Stylemeter anchored to the user's initial intent.
    if (stylometerSongBaselineRef.current) return;
    const style = (drumOptions?.style || "").toString().trim();
    if (!style) return;
    const drummerStyle = (selectedDrummer?.style || "").toString().trim();
    stylometerSongBaselineRef.current = { style, drummerStyle };
  }, [drumOptions?.style, selectedDrummer?.style]);

  const stylometerValues: StylometerValues = useMemo(() => {
    const scope: "song" | "section" | "bar" = selectedBarIndex !== null ? "bar" : selectedMeasureRange ? "section" : "song";

    const sectionCfg =
      scope !== "song" && selectedMeasureRange?.sectionId
        ? sectionGenConfigs[selectedMeasureRange.sectionId] ?? null
        : null;

    const baseline =
      scope !== "song" && selectedMeasureRange?.sectionId
        ? stylometerSectionBaselineRef.current[selectedMeasureRange.sectionId] ?? null
        : stylometerSongBaselineRef.current;

    const selectedStyle = ((baseline?.style ?? sectionCfg?.style ?? drumOptions?.style) || "rock").toLowerCase();
    const profileStyle = ((baseline?.drummerStyle ?? selectedDrummer?.style) || "").toLowerCase();

    const baseGenres: StylometerValues["genres"] = {
      rock: 0,
      jazz: 0,
      funk: 0,
      metal: 0,
      blues: 0,
      pop: 0,
      latin: 0,
      hiphop: 0,
      soul: 0,
    };

    const bump = (key: keyof StylometerValues["genres"], amt: number) => {
      baseGenres[key] = Math.max(0, Math.min(1, (baseGenres[key] || 0) + amt));
    };

    const styleToGenreKey = (s: string): keyof StylometerValues["genres"] | null => {
      if (s === "hip-hop" || s === "hiphop") return "hiphop";
      if (s === "r&b" || s === "rnb") return "soul";
      if (
        s === "rock" ||
        s === "jazz" ||
        s === "funk" ||
        s === "metal" ||
        s === "blues" ||
        s === "pop" ||
        s === "latin" ||
        s === "soul"
      ) {
        return s as any;
      }
      return null;
    };

    const styleKey = styleToGenreKey(selectedStyle);
    const profileKey = styleToGenreKey(profileStyle);

    if (styleKey) bump(styleKey, 0.65);
    if (profileKey) bump(profileKey, 0.55);

    if (grooveSource === "egmd_phrases") {
      const sg = (styleGroup || "").toLowerCase();
      const sgKey = styleToGenreKey(sg);
      if (sgKey) bump(sgKey, grooveMode === "exact" ? 0.35 : 0.25);
    }

    // Make the readout more decisive: sharpen and re-normalize so winners stand out.
    const keys = Object.keys(baseGenres) as Array<keyof StylometerValues["genres"]>;
    let sum = 0;
    for (const k of keys) {
      // Gamma > 1 makes strong influences stronger and weak influences fade out.
      const v = Math.max(0, Math.min(1, baseGenres[k] || 0));
      const sharpened = Math.pow(v, 1.8);
      baseGenres[k] = sharpened;
      sum += sharpened;
    }
    if (sum > 0) {
      for (const k of keys) {
        baseGenres[k] = Math.max(0, Math.min(1, (baseGenres[k] || 0) / sum));
      }
    }

    // Derive a single groove fingerprint score from the active groove map.
    // We measure how strongly the weighting deviates from neutral (1.0) across the 16th grid,
    // then compress to 0..1 so it's a relative, style-differentiating scalar.
    let grooveScore = 0;
    if (activeGrooveMap) {
      const steps = Array.from({ length: 16 }, () => 1.0);
      const counts = Array.from({ length: 16 }, () => 0);
      for (const barKey of Object.keys(activeGrooveMap)) {
        const barIndex = Number(barKey);
        if (!Number.isFinite(barIndex)) continue;
        const bar = (activeGrooveMap as any)[barIndex];
        if (!bar) continue;
        for (let s = 0; s < 16; s += 1) {
          const entry = bar[s];
          if (!entry) continue;
          const preset = GROOVE_WEIGHT_PRESETS[(entry.weight || "neutral") as any];
          const profileWeight = preset?.weights?.[s]?.weight ?? 1.0;
          const forceMultiplier = entry.forceHit ? 1.15 : entry.forceSilent ? 0.65 : 1.0;
          steps[s] += profileWeight * forceMultiplier;
          counts[s] += 1;
        }
      }
      for (let s = 0; s < 16; s += 1) {
        if (counts[s] > 0) {
          steps[s] = steps[s] / (counts[s] + 1);
        }
      }

      // Root-mean-square deviation from neutral.
      const rms = Math.sqrt(
        steps.reduce((acc, v) => {
          const d = (Number.isFinite(v) ? v : 1.0) - 1.0;
          return acc + d * d;
        }, 0) / steps.length,
      );

      // Empirical normalization: typical preset deviations land around ~0.15-0.35.
      grooveScore = Math.max(0, Math.min(1, rms / 0.35));
    }

    // Controls: Song/Section uses config knobs, Bar uses actual edited notes in the selected bar.
    const readCfg = sectionCfg ?? null;
    const humanizeAmountCfg = typeof readCfg?.humanizeAmount === "number" ? readCfg.humanizeAmount : (drumOptions?.humanize ?? 0.6);
    const swingAmountCfg = typeof readCfg?.swingAmount === "number" ? readCfg.swingAmount : (drumOptions?.swing ?? 0);
    const ghostAmountCfg = typeof readCfg?.ghostNoteAmount === "number" ? readCfg.ghostNoteAmount : (drumOptions?.ghost_note_density ?? 0.35);
    const fillAmountCfg = typeof readCfg?.fillDensity === "number" ? readCfg.fillDensity : (drumOptions?.fill_density ?? 0.4);
    const intensityCfg = typeof readCfg?.intensity === "number" ? readCfg.intensity : (drumOptions?.density ?? 0.6);
    const variationCfg = typeof readCfg?.variation === "number" ? readCfg.variation : (drumOptions?.dynamic_range ?? drumOptions?.humanize ?? 0.5);

    let intensity = clamp01(intensityCfg);
    let variation = clamp01(variationCfg);
    let humanizeAmount = clamp01(humanizeAmountCfg);
    let swingAmount = clamp01(swingAmountCfg);
    let ghostAmount = clamp01(ghostAmountCfg);
    let fillDensity = clamp01(fillAmountCfg);

    if (scope === "bar" && activeDrumTrack && selectedBarIndex !== null) {
      const barNotes = activeDrumTrack.notes.filter((n) => (n.barIndex ?? 0) === selectedBarIndex);
      if (barNotes.length) {
        const velocities = barNotes.map((n) => Number(n.velocity ?? 0)).filter((v) => Number.isFinite(v) && v > 0);
        const avgVel = velocities.length ? velocities.reduce((a, b) => a + b, 0) / velocities.length : 90;
        const velVar = velocities.length
          ? velocities.reduce((a, v) => a + Math.pow(v - avgVel, 2), 0) / velocities.length
          : 0;

        const timingOffsets = barNotes
          .map((n) => Number((n.timingOffsetMs ?? n.microTimingMs ?? 0) as any))
          .filter((v) => Number.isFinite(v));
        const timingAbsAvg = timingOffsets.length
          ? timingOffsets.reduce((a, v) => a + Math.abs(v), 0) / timingOffsets.length
          : 0;

        const ghostFrac = barNotes.length
          ? barNotes.filter((n) => Boolean((n as any).isGhost)).length / barNotes.length
          : 0;
        const fillFrac = barNotes.length
          ? barNotes.filter((n) => (n.aspect || "") === "fill").length / barNotes.length
          : 0;

        intensity = clamp01(avgVel / 127);
        variation = clamp01(Math.sqrt(velVar) / 35);
        humanizeAmount = clamp01(timingAbsAvg / 10);
        ghostAmount = clamp01(ghostFrac / 0.35);
        fillDensity = clamp01(fillFrac / 0.25);
        // swing is currently not directly observable from note data in this editor, so keep config value.
        swingAmount = clamp01(swingAmountCfg);
      }
    }

    return {
      genres: baseGenres,
      grooveScore,
      controls: {
        intensity,
        variation,
        humanize: humanizeAmount,
        swing: swingAmount,
        ghosts: ghostAmount,
        fills: fillDensity,
      },
    };
  }, [activeDrumTrack, activeGrooveMap, drumOptions, grooveMode, grooveSource, sectionGenConfigs, selectedBarIndex, selectedDrummer?.style, selectedMeasureRange, styleGroup]);

  const stylometerGenreLabel = useMemo(() => {
    const entries = Object.entries(stylometerValues.genres)
      .map(([k, v]) => ({ k, v: Number(v) }))
      .filter((e) => Number.isFinite(e.v))
      .sort((a, b) => b.v - a.v);
    const top = entries[0];
    const second = entries[1];
    const pretty = (k: string) => {
      if (k === "hiphop") return "Hip-Hop";
      if (k === "soul") return "Soul";
      return k.charAt(0).toUpperCase() + k.slice(1);
    };
    if (!top || top.v <= 0) return "";
    if (second && second.v >= 0.28) {
      return `${pretty(top.k)}-${pretty(second.k)}`;
    }
    return pretty(top.k);
  }, [stylometerValues.genres]);

  const stylometerScopeLabel = useMemo(() => {
    if (selectedBarIndex !== null) {
      return `Bar: ${selectedBarIndex + 1}`;
    }
    if (selectedMeasureRange?.sectionId) {
      const section = sections.find((s) => s.id === selectedMeasureRange.sectionId);
      const label = (section?.label || section?.id || "Section").toString();
      return `Section: ${label}`;
    }
    return "Song";
  }, [sections, selectedBarIndex, selectedMeasureRange?.sectionId]);

  const handleResetStylometerBaseline = useCallback(() => {
    const drummerStyle = (selectedDrummer?.style || "").toString();
    const style = (drumOptions?.style || "rock").toString();
    stylometerSongBaselineRef.current = { style, drummerStyle };

    const sectionId = selectedMeasureRange?.sectionId;
    if (sectionId) {
      const sectionStyle = (sectionGenConfigs?.[sectionId]?.style || style).toString();
      stylometerSectionBaselineRef.current[sectionId] = {
        style: sectionStyle,
        drummerStyle,
      };
    }
  }, [drumOptions?.style, sectionGenConfigs, selectedDrummer?.style, selectedMeasureRange?.sectionId]);

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

  const [sectionGrooveModalOpen, setSectionGrooveModalOpen] = useState(false);
  const [sectionGrooveModalSectionId, setSectionGrooveModalSectionId] = useState<string>("");
  const [sectionGrooveQuery, setSectionGrooveQuery] = useState("");
  const [sectionGrooveTag, setSectionGrooveTag] = useState("");
  const [sectionGrooveLoading, setSectionGrooveLoading] = useState(false);
  const [sectionGrooveResults, setSectionGrooveResults] = useState<any[]>([]);
  const [sectionSelectedGrooveId, setSectionSelectedGrooveId] = useState<string>("");
  const [sectionFillGrooveId, setSectionFillGrooveId] = useState<string>("");
  const [sectionFillBarRelativeText, setSectionFillBarRelativeText] = useState<string>("last");
  const [sectionGrooveSelections, setSectionGrooveSelections] = useState<
    Record<string, { selectedGrooveId?: string; fillGrooveId?: string; fillBarRelativeText?: string }>
  >({});

  const grooveAudioRef = useRef<HTMLAudioElement | null>(null);
  const [auditioningGrooveId, setAuditioningGrooveId] = useState<string>("");

  const stopGrooveAudition = useCallback(() => {
    const audio = grooveAudioRef.current;
    if (!audio) return;
    try {
      audio.pause();
      audio.currentTime = 0;
    } catch {
      // ignore
    }
    grooveAudioRef.current = null;
    setAuditioningGrooveId("");
  }, []);

  const auditionGroove = useCallback(
    async (grooveId: string) => {
      const nextId = String(grooveId || "").trim();
      if (!nextId) return;
      if (auditioningGrooveId === nextId) {
        stopGrooveAudition();
        return;
      }
      stopGrooveAudition();
      const url = `/api/grooves/${encodeURIComponent(nextId)}/audio`;
      const audio = new Audio(url);
      grooveAudioRef.current = audio;
      setAuditioningGrooveId(nextId);
      audio.onended = () => {
        if (auditioningGrooveId === nextId) {
          setAuditioningGrooveId("");
        }
        grooveAudioRef.current = null;
      };
      try {
        await audio.play();
      } catch (e) {
        console.warn("Groove audition failed", e);
        stopGrooveAudition();
      }
    },
    [auditioningGrooveId, stopGrooveAudition],
  );

  const sectionQuickGrooveTags = [
    "four_on_floor",
    "backbeat_2_4",
    "halftime",
    "shuffle",
    "sixteenth_note_hats",
    "paradiddle",
    "rudiment",
  ];

  const searchSectionGrooves = useCallback(
    async (nextQuery?: string, nextTag?: string) => {
      const q = (nextQuery ?? sectionGrooveQuery).trim();
      const t = (nextTag ?? sectionGrooveTag).trim();
      setSectionGrooveLoading(true);
      try {
        const params = new URLSearchParams();
        if (q) params.set("q", q);
        if (t) params.set("tags", t);
        params.set("limit", "24");
        const res = await fetch(`/api/grooves/search?${params.toString()}`);
        const json = await res.json();
        setSectionGrooveResults(Array.isArray(json?.items) ? json.items : []);
      } catch (e) {
        console.warn("section groove search failed", e);
        setSectionGrooveResults([]);
      } finally {
        setSectionGrooveLoading(false);
      }
    },
    [sectionGrooveQuery, sectionGrooveTag],
  );

  const openSectionGrooveModal = (sectionId: string) => {
    if (!sectionId) return;
    const existing = sectionGrooveSelections[sectionId] || {};
    setSectionGrooveModalSectionId(sectionId);
    setSectionSelectedGrooveId(existing.selectedGrooveId || "");
    setSectionFillGrooveId(existing.fillGrooveId || "");
    setSectionFillBarRelativeText(existing.fillBarRelativeText || "last");
    setSectionGrooveModalOpen(true);
  };

  const closeSectionGrooveModal = () => {
    setSectionGrooveModalOpen(false);
  };

  const resolveRelativeBarIndex = (raw: string, bars: number): number | null => {
    const normalized = String(raw || "").trim().toLowerCase();
    if (!bars || bars <= 0) return null;
    if (normalized === "last" || normalized === "-1") return Math.max(0, bars - 1);
    if (!normalized) return null;
    const n = Math.floor(Number(normalized));
    if (!Number.isFinite(n)) return null;
    return Math.max(0, Math.min(Math.max(0, bars - 1), n));
  };

  const handleGenerateFullSongWithGrooves = async (opts?: { ignoreGrooveSelections?: boolean }) => {
    if (!sections.length) {
      setErr("No sections available to build drums for yet.");
      return;
    }
    if (!selectedDrummer) {
      openDrummerPersonaModal();
      return;
    }
    if (bulkGenerating || generatingDrums) {
      return;
    }

    setBulkGenerating(true);
    setFullSongProgress({ completed: 0, total: 1 });
    setFullSongStatus({ type: "progress", message: "Building drums for full song…" });
    try {
      const primaryTrackKey = tracks[0]?.key;
      if (primaryTrackKey) {
        try {
          await analyzeSectionTempos(primaryTrackKey, sections);
        } catch (tempoErr) {
          console.warn("Tempo analysis during full-song generation failed", tempoErr);
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
          const measureRange = sectionToMeasureRange(
            section,
            bpm,
            timeSig,
            songMap,
            tempoFlattenToleranceBpm,
            drumTempoMode,
          );
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

      const baselineDefaults = deriveBaselineDrumOptions(
        bpm,
        timeSig,
        drumOptions.style || selectedDrummer?.style || "rock",
        selectedDrummer?.id || "",
      );
      const effectiveDrumOptions = { ...drumOptions, ...baselineDefaults };
      setDrumOptions((prev) => ({ ...prev, ...baselineDefaults }));

      setSelectedMeasureRange(fullRange);
      setSelectedSectionIds(new Set(["full-song"]));

      void opts;

      const fullSongConfig: DrumGenerationConfig = {
        sectionId: "full-song",
        startMeasure: fullRange.startMeasure,
        endMeasure: fullRange.endMeasure,
        tempos: fullRange.tempos,
        timeSignature: fullRange.timeSignature,
        style: effectiveDrumOptions.style || drumOptions.style || "rock",
        drummer: selectedDrummer?.id || "jeff_porcaro",
        intensity: clamp01(Math.min(0.7, effectiveDrumOptions.density ?? 0.55)),
        variation: clamp01(
          Math.min(
            0.6,
            Math.max(0.35, effectiveDrumOptions.dynamic_range ?? effectiveDrumOptions.humanize ?? 0.45),
          ),
        ),
        generationMode: "full_ai",
        humanize: true,
        fillLocations: (() => {
          const bars = Math.max(1, fullRange.measureCount);
          const fills = new Set<number>();
          let cursor = 0;
          for (let i = 0; i < songSections.length; i += 1) {
            const secBars = Math.max(1, Number(songSections[i]?.bars ?? 1));
            cursor += secBars;
            const fillBar = cursor - 1;
            if (fillBar >= 0 && fillBar < bars - 1) {
              fills.add(fillBar);
            }
          }
          fills.add(bars - 1);
          return Array.from(fills).sort((a, b) => a - b);
        })(),
        fillType: effectiveDrumOptions.fill_preset ?? "auto",
        fillDensity: clamp01(Math.min(0.55, effectiveDrumOptions.fill_density ?? 0.35)),
        humanizeAmount: clamp01(Math.min(0.75, effectiveDrumOptions.humanize ?? 0.62)),
        ghostNoteAmount: clamp01(Math.min(0.6, effectiveDrumOptions.ghost_note_density ?? 0.25)),
        swingAmount: clamp01(effectiveDrumOptions.swing ?? 0),
        buildScope: "full_song",
        guideEnabled: false,
        songStyle: derivedSongStyle,
        songSections,
        fillControls: {
          fillType: effectiveDrumOptions.fill_preset ?? "auto",
          density: clamp01(Math.min(0.55, effectiveDrumOptions.fill_density ?? 0.35)),
          frequency: "all_transitions",
        },
      };

      setSectionGenConfigs((prev) => ({
        ...prev,
        ["full-song"]: fullSongConfig,
      }));

      stylometerSongBaselineRef.current = {
        style: (fullSongConfig.style || "rock").toString(),
        drummerStyle: (selectedDrummer?.style || "").toString(),
      };
      stylometerSectionBaselineRef.current["full-song"] = {
        style: (fullSongConfig.style || "rock").toString(),
        drummerStyle: (selectedDrummer?.style || "").toString(),
      };

      const applied = await executeDrumGeneration(fullSongConfig, { suppressSpinner: true });
      setFullSongProgress({ completed: 1, total: 1 });

      if (!applied) {
        setFullSongStatus({
          type: "error",
          message: "Finished, but the generator returned no drum data for the full song.",
        });
      } else {
        setFullSongStatus({ type: "success", message: "🥁 Completed drum build for the full song." });
      }
    } catch (fullSongError: any) {
      console.error("❌ Full-song drum generation failed:", fullSongError);
      const errorMessage = `Full-song drum generation failed: ${fullSongError?.message || fullSongError}`;
      setErr(errorMessage);
      setFullSongStatus({
        type: "error",
        message: `❌ Full-song generation failed: ${String(fullSongError?.message || fullSongError)}`,
      });
    } finally {
      setBulkGenerating(false);
    }
  };

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

  const focusMainEditorBar = useCallback(
    (barIndex: number) => {
      if (!Number.isFinite(barIndex) || barIndex < 0) return;
      setSelectedBarIndex(barIndex);

      const beatsPerBar = Math.max(1, Number(timeSig?.[0] ?? 4) || 4);
      const secondsPerBar = (60 / Math.max(1, Number(bpm) || 120)) * beatsPerBar;
      scrollToTime(barIndex * secondsPerBar);

      const pianoEl = pianoRollScrollRef.current;
      if (pianoEl) {
        const barWidthPx = Math.max(1, gridPixelsPerBeat * beatsPerBar);
        pianoEl.scrollLeft = Math.max(0, barIndex * barWidthPx);
      }
    },
    [bpm, gridPixelsPerBeat, scrollToTime, timeSig],
  );

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

  const handleSongMapSelectGlobal = useCallback(() => {
    setScopedControlsMode("global");
    setScopedControlsSectionId(null);
    setMiniEditorOpen(false);
  }, []);

  const handleSongMapSelectSection = useCallback(
    (sectionId: string) => {
      if (!sectionId) return;
      setScopedControlsMode("section");
      setScopedControlsSectionId(sectionId);
      setMiniEditorOpen(false);
      setSelectedSectionIds(new Set([sectionId]));

      const section = sections.find((s) => s.id === sectionId);
      if (section) {
        const measureRange = sectionToMeasureRange(
          section,
          bpm,
          timeSig,
          songMap,
          tempoFlattenToleranceBpm,
          drumTempoMode,
        );
        setSelectedMeasureRange(measureRange);
      } else {
        setSelectedMeasureRange(null);
      }

      window.requestAnimationFrame(() => {
        scrollToSelectedSection();
        setSongMapFlashNonce((v) => v + 1);
        setSoftFocusPulseNonce((v) => v + 1);
      });
    },
    [
      bpm,
      drumTempoMode,
      scrollToSelectedSection,
      sections,
      setSelectedMeasureRange,
      setSelectedSectionIds,
      songMap,
      tempoFlattenToleranceBpm,
      timeSig,
    ],
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
          const engineCandidate =
            playheadClockModeRef.current === "engine" ? Engine.getCurrentTimeSeconds() : NaN;
          const next =
            playheadClockModeRef.current === "engine" && Number.isFinite(engineCandidate) && engineCandidate > p + 1e-3
              ? engineCandidate
              : p + dt;

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
    setSelectedBarIndex(null);
    setPlayhead(0);
    setArrangementSource(null);
    setSongMap(null);
    setSectionDrumTracks({});
    setSectionGrooveMaps({});
    setSectionGenConfigs({});
    setSectionPlacementContexts({});
    setSectionNoteIds({});
    setNotes([]);

    // Reset Stylometer baseline snapshots so a new song/style starts fresh.
    stylometerSongBaselineRef.current = null;
    stylometerSectionBaselineRef.current = {};
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
      const normalizedDrummerId = (value: any): string => String(value || "").trim();

      let payload: DrumGenerationConfig = {
        ...config,
        publicDrummerId:
          normalizedDrummerId(selectedDrummer?.id) ||
          normalizedDrummerId(config.publicDrummerId) ||
          normalizedDrummerId(config.drummer) ||
          undefined,
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

      const resolved = resolveGrooveSettings(config.sectionId);
      const isEgmd = resolved.grooveSource === "egmd_phrases";

      const egmdSelectedPhrase =
        isEgmd && resolved.selectedEgmdPhraseId !== null && typeof resolved.selectedEgmdPhraseId !== "undefined"
          ? egmdPhraseOptions.find((p) => Number(p?.phrase_id) === Number(resolved.selectedEgmdPhraseId)) ?? null
          : null;
      payload = {
        ...payload,
        grooveSource: isEgmd ? "egmd_phrases" : undefined,
        grooveMode: isEgmd ? resolved.grooveMode : undefined,
        styleGroup: isEgmd ? resolved.styleGroup : undefined,
        egmdPhraseId:
          isEgmd && resolved.selectedEgmdPhraseId !== null && typeof resolved.selectedEgmdPhraseId !== "undefined"
            ? resolved.selectedEgmdPhraseId
            : undefined,
        egmdMidiPath: isEgmd ? (egmdSelectedPhrase?.midi_path ? String(egmdSelectedPhrase.midi_path) : undefined) : undefined,
        egmdPhraseOverrides:
          isEgmd && resolved.egmdOverrideMode !== 'single'
            ? {
                mode: resolved.egmdOverrideMode === 'by_type' ? 'by_type' : 'by_index',
                byType: resolved.egmdOverrideMode === 'by_type' ? resolved.egmdPhraseByType : undefined,
                byIndex: resolved.egmdOverrideMode === 'by_index' ? resolved.egmdPhraseByIndex : undefined,
              }
            : undefined,
      };

      payload = (await attachSentientProfilesWithOverrides(payload as any)) as any;
      console.log('🥁 Generating drums:', payload);
      console.log('[DrumGenPayload] style/drummer', {
        sectionId: payload.sectionId,
        style: (payload as any).style,
        drummer: (payload as any).drummer,
        publicDrummerId: (payload as any).publicDrummerId,
        grooveSource: (payload as any).grooveSource,
        grooveMode: (payload as any).grooveMode,
        styleGroup: (payload as any).styleGroup,
      });

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

      try {
        const metaDump = {
          builder_version: (resultMetadata as any)?.builder_version ?? (resultMetadata as any)?.builderVersion,
          performance_from_llm: (resultMetadata as any)?.performance_from_llm ?? (resultMetadata as any)?.performanceFromLlm,
          egmdPhrase: (resultMetadata as any)?.egmdPhrase,
          egmdSections0: Array.isArray((resultMetadata as any)?.egmdSections)
            ? (resultMetadata as any)?.egmdSections?.[0]
            : undefined,
          roadmapDebug0: Array.isArray((resultMetadata as any)?.roadmapDebug)
            ? (resultMetadata as any)?.roadmapDebug?.[0]
            : undefined,
        };
        console.log("[DrumGenResult.metadata dump]", metaDump);
        console.log("[DrumGenResult.metadata dump json]", JSON.stringify(metaDump, null, 2));
      } catch (e) {
        console.warn("[DrumGenResult.metadata dump] failed", e);
      }

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
      return appliedHighRes;
    } finally {
      if (!suppressSpinner) {
        setGeneratingDrums(false);
      }
    }
    return appliedHighRes;
  }

  const [llmStatusBusy, setLlmStatusBusy] = useState(false);
  const [llmStatusResult, setLlmStatusResult] = useState<any>(null);
  const [llmStatusError, setLlmStatusError] = useState<string | null>(null);

  const [globalDefaultsExpanded, setGlobalDefaultsExpanded] = useState(false);
  const [sectionControlsExpanded, setSectionControlsExpanded] = useState(true);
  const [scopedControlsMode, setScopedControlsMode] = useState<"global" | "section">("global");
  const [scopedControlsSectionId, setScopedControlsSectionId] = useState<string | null>(null);
  const [miniEditorOpen, setMiniEditorOpen] = useState(false);
  const [songMapFlashNonce, setSongMapFlashNonce] = useState(0);
  const [softFocusPulseNonce, setSoftFocusPulseNonce] = useState(0);
  const [softFocusActive, setSoftFocusActive] = useState(false);

  useEffect(() => {
    if (!softFocusPulseNonce) return;
    setSoftFocusActive(true);
    const t = window.setTimeout(() => setSoftFocusActive(false), 900);
    return () => window.clearTimeout(t);
  }, [softFocusPulseNonce]);

  async function handleCheckLocalLlmStatus() {
    setLlmStatusBusy(true);
    setLlmStatusError(null);
    try {
      const apiBase = resolveApiBaseNormalized();
      const url = `${apiBase}/api/llm/status`;
      const resp = await fetch(url, { method: 'GET' });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error((data as any)?.error || 'LLM status check failed');
      }
      setLlmStatusResult(data);
    } catch (e: any) {
      setLlmStatusResult(null);
      setLlmStatusError(String(e?.message || e));
    } finally {
      setLlmStatusBusy(false);
    }
  }

  async function handleGenerateDrums(config: DrumGenerationConfig) {
    try {
      const normalizedConfigDrummer = String((config as any)?.publicDrummerId || config.drummer || "").trim();
      const resolvedDrummerId = String(selectedDrummer?.id || normalizedConfigDrummer || "").trim();
      const resolvedStyle = String(selectedDrummer?.style || config.style || "rock").trim();

      if (config.sectionId && config.sectionId !== "full-song") {
        const selection = sectionGrooveSelections[config.sectionId];
        if (selection?.selectedGrooveId) {
          (config as any).selectedGrooveId = selection.selectedGrooveId;
          (config as any).grooveUse = "use_as_groove";
        }
        if (selection?.fillGrooveId) {
          const bars = Math.max(1, (config.endMeasure ?? 0) - (config.startMeasure ?? 0) + 1);
          const rel = resolveRelativeBarIndex(selection.fillBarRelativeText || "last", bars);
          if (rel !== null) {
            (config as any).fillGrooveId = selection.fillGrooveId;
            (config as any).fillBarIndex = Math.max(0, (config.startMeasure ?? 0) + rel);
          }
        }
      }
      // Persist the last-used generator settings per section so the Stylemeter can reflect
      // section-level intent even after you switch edit scopes.
      if (config.sectionId) {
        setSectionGenConfigs((prev) => ({
          ...prev,
          [config.sectionId]: config,
        }));

        if (!stylometerSectionBaselineRef.current[config.sectionId]) {
          stylometerSectionBaselineRef.current[config.sectionId] = {
            style: (config.style || "").toString(),
            drummerStyle: resolvedDrummerId ? (selectedDrummer?.style || "").toString() : "",
          };
        }
      }

      if (!stylometerSongBaselineRef.current) {
        stylometerSongBaselineRef.current = {
          style: (drumOptions?.style || config.style || "rock").toString(),
          drummerStyle: resolvedDrummerId ? (selectedDrummer?.style || "").toString() : "",
        };
      }
      await executeDrumGeneration({
        ...config,
        style: resolvedStyle || config.style,
        drummer: resolvedDrummerId,
        publicDrummerId: resolvedDrummerId || undefined,
      });
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

    const drummerId = String(selectedDrummer?.id || '').trim();
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

  function deriveBaselineDrumOptions(
    tempoBpm: number,
    meter: [number, number],
    style: string,
    drummerId: string,
  ) {
    const tempo = Number.isFinite(tempoBpm) && tempoBpm > 0 ? tempoBpm : 120;
    const beatsPerBar = Number.isFinite(meter?.[0]) ? meter[0] : 4;
    const denom = Number.isFinite(meter?.[1]) ? meter[1] : 4;
    const normalizedStyle = String(style || 'rock').toLowerCase();
    const normalizedDrummer = String(drummerId || '').toLowerCase();

    const isCompound = beatsPerBar === 6 && denom === 8;
    const isFast = tempo >= 170;
    const isSlow = tempo <= 80;

    let density = 0.62;
    let swing = 0.0;
    let humanize = 0.72;
    let ghost = 0.45;
    let fillDensity = 0.55;
    let fillPreset: any = 'auto';
    let dynamicRange = 0.72;

    if (normalizedStyle.includes('jazz')) {
      density = 0.52;
      swing = 0.28;
      ghost = 0.55;
      humanize = 0.78;
      dynamicRange = 0.78;
      fillDensity = 0.4;
    } else if (normalizedStyle.includes('funk')) {
      density = 0.68;
      swing = 0.12;
      ghost = 0.62;
      humanize = 0.7;
      dynamicRange = 0.7;
      fillDensity = 0.45;
    } else if (normalizedStyle.includes('hip') || normalizedStyle.includes('trap')) {
      density = 0.5;
      swing = 0.18;
      ghost = 0.35;
      humanize = 0.6;
      dynamicRange = 0.55;
      fillDensity = 0.35;
    } else if (normalizedStyle.includes('metal')) {
      density = 0.78;
      swing = 0.0;
      ghost = 0.25;
      humanize = 0.58;
      dynamicRange = 0.65;
      fillDensity = 0.7;
    } else if (normalizedStyle.includes('latin')) {
      density = 0.7;
      swing = 0.08;
      ghost = 0.5;
      humanize = 0.7;
      dynamicRange = 0.7;
      fillDensity = 0.5;
    } else if (normalizedStyle.includes('pop')) {
      density = 0.6;
      swing = 0.03;
      ghost = 0.35;
      humanize = 0.66;
      dynamicRange = 0.62;
      fillDensity = 0.45;
    }

    if (isCompound) {
      swing = Math.max(swing, 0.12);
      ghost = Math.min(0.75, ghost + 0.08);
    }
    if (isFast) {
      density = Math.max(0.45, density - 0.08);
      fillDensity = Math.max(0.35, fillDensity - 0.1);
      humanize = Math.max(0.5, humanize - 0.06);
    }
    if (isSlow) {
      density = Math.min(0.85, density + 0.06);
      humanize = Math.min(0.85, humanize + 0.05);
    }

    if (normalizedDrummer.includes('bonham') || normalizedDrummer.includes('grohl')) {
      density = Math.min(0.9, density + 0.05);
      dynamicRange = Math.min(0.9, dynamicRange + 0.08);
      ghost = Math.max(0.2, ghost - 0.08);
    }
    if (normalizedDrummer.includes('purdie') || normalizedDrummer.includes('gadd')) {
      ghost = Math.min(0.85, ghost + 0.08);
      swing = Math.min(0.45, swing + 0.05);
    }
    if (normalizedDrummer.includes('porcaro')) {
      humanize = Math.min(0.85, humanize + 0.03);
    }

    return {
      density: clamp01(density),
      swing: clamp01(swing),
      humanize: clamp01(humanize),
      ghost_note_density: clamp01(ghost),
      dynamic_range: clamp01(dynamicRange),
      fill_density: clamp01(fillDensity),
      fill_preset: fillPreset,
    };
  }

  async function handleGenerateFullSong() {
    if (!sections.length) {
      setErr('No sections available to build drums for yet.');
      return;
    }
    if (!selectedDrummer) {
      openDrummerPersonaModal();
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

      const baselineDefaults = deriveBaselineDrumOptions(
        bpm,
        timeSig,
        drumOptions.style || selectedDrummer?.style || 'rock',
        selectedDrummer?.id || '',
      );
      const effectiveDrumOptions = { ...drumOptions, ...baselineDefaults };
      setDrumOptions((prev) => ({ ...prev, ...baselineDefaults }));

      setSelectedMeasureRange(fullRange);
      setSelectedSectionIds(new Set(["full-song"]));

      const fullSongConfig: DrumGenerationConfig = {
        sectionId: "full-song",
        startMeasure: fullRange.startMeasure,
        endMeasure: fullRange.endMeasure,
        tempos: fullRange.tempos,
        timeSignature: fullRange.timeSignature,
        style: effectiveDrumOptions.style || drumOptions.style || "rock",
        drummer: selectedDrummer?.id || "jeff_porcaro",
        intensity: clamp01(Math.min(0.7, effectiveDrumOptions.density ?? 0.55)),
        variation: clamp01(Math.min(0.6, Math.max(0.35, effectiveDrumOptions.dynamic_range ?? effectiveDrumOptions.humanize ?? 0.45))),
        generationMode: "full_ai",
        humanize: true,
        fillLocations: (() => {
          const bars = Math.max(1, fullRange.measureCount);
          const fills = new Set<number>();
          let cursor = 0;
          for (let i = 0; i < songSections.length; i += 1) {
            const secBars = Math.max(1, Number(songSections[i]?.bars ?? 1));
            cursor += secBars;
            const fillBar = cursor - 1;
            if (fillBar >= 0 && fillBar < bars - 1) {
              fills.add(fillBar);
            }
          }
          fills.add(bars - 1);
          return Array.from(fills).sort((a, b) => a - b);
        })(),
        fillType: effectiveDrumOptions.fill_preset ?? "auto",
        fillDensity: clamp01(Math.min(0.55, effectiveDrumOptions.fill_density ?? 0.35)),
        humanizeAmount: clamp01(Math.min(0.75, effectiveDrumOptions.humanize ?? 0.62)),
        ghostNoteAmount: clamp01(Math.min(0.6, effectiveDrumOptions.ghost_note_density ?? 0.25)),
        swingAmount: clamp01(effectiveDrumOptions.swing ?? 0),
        buildScope: "full_song",
        guideEnabled: false,
        songStyle: derivedSongStyle,
        songSections,
        fillControls: {
          fillType: effectiveDrumOptions.fill_preset ?? "auto",
          density: clamp01(Math.min(0.55, effectiveDrumOptions.fill_density ?? 0.35)),
          frequency: "all_transitions",
        },
      };

      // Persist full-song config for Stylometer section scope.
      setSectionGenConfigs((prev) => ({
        ...prev,
        ["full-song"]: fullSongConfig,
      }));

      // Establish/refresh baselines for this full-song build.
      stylometerSongBaselineRef.current = {
        style: (fullSongConfig.style || "rock").toString(),
        drummerStyle: (selectedDrummer?.style || "").toString(),
      };
      stylometerSectionBaselineRef.current["full-song"] = {
        style: (fullSongConfig.style || "rock").toString(),
        drummerStyle: (selectedDrummer?.style || "").toString(),
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
      setFullSongStatus({
        type: 'error',
        message: `❌ Full-song generation failed: ${String(fullSongError?.message || fullSongError)}`,
      });
    } finally {
      setBulkGenerating(false);
    }
  }

  async function handleRegenerateFullSongWithSelectedDrummer() {
    if (!sections.length) {
      setErr('No sections available to build drums for yet.');
      return;
    }
    if (!selectedDrummer) {
      openDrummerPersonaModal();
      return;
    }
    if (bulkGenerating || generatingDrums) {
      return;
    }

    const confirmed = window.confirm(
      'Rebuild the entire song using the newly selected drummer profile? This will overwrite all generated drum tracks for the current arrangement.',
    );
    if (!confirmed) {
      return;
    }

    setSectionDrumTracks({});
    setSectionGrooveMaps({});
    setSectionPlacementContexts({});
    setSectionNoteIds({});
    setDebugDrumGen(null);
    await handleGenerateFullSong();
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
    <>
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <div className="flex-1 min-w-0 flex flex-col">
        <div className="h-12 bg-slate-900 border-b border-slate-800 flex items-center justify-between px-3">
          <div />
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                className={
                  "px-3 py-1 rounded border text-xs font-semibold " +
                  (stylometerOpen
                    ? "bg-cyan-600/20 border-cyan-400/50 text-cyan-100"
                    : "bg-slate-800 border-slate-700 text-slate-200 hover:border-slate-500")
                }
                onMouseDown={(e) => {
                  e.preventDefault();
                  setStylometerOpen(true);
                }}
              >
                Open Stylometer
              </button>
              <button
                type="button"
                className="px-3 py-1 rounded border text-xs font-semibold bg-slate-800 border-slate-700 text-slate-200 hover:border-slate-500 disabled:opacity-40 disabled:cursor-not-allowed"
                onMouseDown={(e) => {
                  e.preventDefault();
                  setStylometerOpen(false);
                }}
                disabled={!stylometerOpen}
              >
                Close
              </button>
            </div>
            <button className="px-2 py-1 rounded bg-emerald-600" onClick={async()=>{ await ensureDrumEngineReady(); playheadClockModeRef.current = tracks.length ? "engine" : "raf"; drumPlaybackStartCtxSecRef.current = drumEngineRef.current?.audioContext?.currentTime ?? 0; drumPlaybackStartPlayheadSecRef.current = playhead; lastDrumScheduleSecRef.current = playhead; await Engine.play(playhead); setPlaying(true); }}>Play</button>
            <button className="px-2 py-1 rounded bg-slate-700" onClick={async()=>{ await Engine.pause(); setPlaying(false); }}>Pause</button>
            <button className="px-2 py-1 rounded bg-slate-700" onClick={async()=>{ await Engine.stop(); setPlaying(false); setPlayhead(0); lastDrumScheduleSecRef.current = 0; drumPlaybackStartPlayheadSecRef.current = 0; drumPlaybackStartCtxSecRef.current = drumEngineRef.current?.audioContext?.currentTime ?? 0; }}>Stop</button>
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

        <div className="flex-1 min-w-0 overflow-hidden flex relative">
          {stylometerOpen && (
            <div
              className="fixed z-[80]"
              style={{ left: stylometerPos.x, top: stylometerPos.y }}
            >
              <div className="w-[360px] max-w-[90vw] rounded-xl border border-slate-700 bg-slate-950/95 shadow-2xl overflow-hidden">
                <div
                  className="flex items-center justify-between gap-2 px-3 py-2 border-b border-slate-800 bg-slate-900 cursor-move select-none"
                  onPointerDown={(e) => {
                    e.preventDefault();
                    stylometerDragRef.current = {
                      pointerId: e.pointerId,
                      offsetX: e.clientX - stylometerPos.x,
                      offsetY: e.clientY - stylometerPos.y,
                    };
                    (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
                  }}
                  onPointerMove={(e) => {
                    const drag = stylometerDragRef.current;
                    if (!drag || drag.pointerId !== e.pointerId) return;
                    e.preventDefault();
                    const nextX = Math.max(8, Math.min(window.innerWidth - 80, e.clientX - drag.offsetX));
                    const nextY = Math.max(8, Math.min(window.innerHeight - 80, e.clientY - drag.offsetY));
                    setStylometerPos({ x: nextX, y: nextY });
                  }}
                  onPointerUp={(e) => {
                    const drag = stylometerDragRef.current;
                    if (!drag || drag.pointerId !== e.pointerId) return;
                    stylometerDragRef.current = null;
                    try {
                      (e.currentTarget as HTMLDivElement).releasePointerCapture(e.pointerId);
                    } catch {
                      // ignore
                    }
                  }}
                  onPointerCancel={(e) => {
                    const drag = stylometerDragRef.current;
                    if (!drag || drag.pointerId !== e.pointerId) return;
                    stylometerDragRef.current = null;
                    try {
                      (e.currentTarget as HTMLDivElement).releasePointerCapture(e.pointerId);
                    } catch {
                      // ignore
                    }
                  }}
                >
                  <div className="text-sm font-semibold text-slate-100">Stylometer</div>
                  <button
                    type="button"
                    className="px-2 py-1 rounded border border-slate-700 bg-slate-900 text-xs text-slate-200 hover:border-slate-500"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      setStylometerOpen(false);
                    }}
                  >
                    Close
                  </button>
                </div>
                <div className="p-2">
                  <StylometerFlower
                    values={stylometerValues}
                    title="Stylometer"
                    subtitle="Live fingerprint: groove numbers + feel controls"
                    genreLabel={stylometerGenreLabel}
                    scopeLabel={stylometerScopeLabel}
                    onResetBaseline={handleResetStylometerBaseline}
                  />
                </div>
              </div>
            </div>
          )}
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
                        <Tooltip content="Zoom out" placement="top" maxWidthClassName="w-28">
                          <button
                            type="button"
                            className="px-2 py-1 rounded border border-slate-700 bg-slate-900 text-xs text-slate-200"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              setGridPixelsPerBeat((prev) => Math.max(10, Math.min(240, prev - 5)));
                            }}
                          >
                            -
                          </button>
                        </Tooltip>
                        <input
                          type="range"
                          min={10}
                          max={240}
                          step={5}
                          value={gridPixelsPerBeat}
                          onChange={(e) => setGridPixelsPerBeat(Number(e.target.value))}
                          className="flex-1 accent-cyan-400"
                        />
                        <Tooltip content="Zoom in" placement="top" maxWidthClassName="w-24">
                          <button
                            type="button"
                            className="px-2 py-1 rounded border border-slate-700 bg-slate-900 text-xs text-slate-200"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              setGridPixelsPerBeat((prev) => Math.max(10, Math.min(240, prev + 5)));
                            }}
                          >
                            +
                          </button>
                        </Tooltip>
                        <span className="text-[11px] text-slate-500 w-12 text-right">Wide</span>
                      </div>
                    </div>
                    <div className="flex-1 min-w-[220px]">
                      <p className="text-[11px] uppercase tracking-wide text-slate-400">
                        Linked Scroll Position
                      </p>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-[11px] text-slate-500 w-12">Start</span>
                        <Tooltip content="Scroll left" placement="top" maxWidthClassName="w-28">
                          <button
                            type="button"
                            className="px-2 py-1 rounded border border-slate-700 bg-slate-900 text-xs text-slate-200"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              onScrollSliderChange({ target: { value: String(Math.max(0, Math.min(100, scrollPercent - 1))) } } as any);
                            }}
                          >
                            -
                          </button>
                        </Tooltip>
                        <input
                          type="range"
                          min={0}
                          max={100}
                          step={1}
                          value={scrollPercent}
                          onChange={onScrollSliderChange}
                          className="flex-1 accent-fuchsia-500"
                        />
                        <Tooltip content="Scroll right" placement="top" maxWidthClassName="w-28">
                          <button
                            type="button"
                            className="px-2 py-1 rounded border border-slate-700 bg-slate-900 text-xs text-slate-200"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              onScrollSliderChange({ target: { value: String(Math.max(0, Math.min(100, scrollPercent + 1))) } } as any);
                            }}
                          >
                            +
                          </button>
                        </Tooltip>
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
              <div className="py-4 px-0">
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
                  onSectionContextMenu={(sectionId: string) => {
                    if (!sectionId) return;
                    setSelectedSectionIds(new Set([sectionId]));
                    const section = sections.find((s) => s.id === sectionId);
                    if (section) {
                      const measureRange = sectionToMeasureRange(
                        section,
                        bpm,
                        timeSig,
                        songMap,
                        tempoFlattenToleranceBpm,
                        drumTempoMode,
                      );
                      setSelectedMeasureRange(measureRange);
                    }
                    openSectionGrooveModal(sectionId);
                  }}
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
                      setScopedControlsMode("section");
                      setScopedControlsSectionId(sectionId);
                      setMiniEditorOpen(false);
                      
                      // Set measure range for drum builder
                      const section = sections.find(s => s.id === sectionId);
                      if (section) {
                        const measureRange = sectionToMeasureRange(section, bpm, timeSig, songMap, tempoFlattenToleranceBpm, drumTempoMode);
                        setSelectedMeasureRange(measureRange);
                        console.log('🎯 Selected measure range:', measureRange);
                      }

                      window.requestAnimationFrame(() => {
                        scrollToSelectedSection();
                        setSoftFocusPulseNonce((v) => v + 1);
                      });
                    }
                  }}
                />
              </div>

              {/* Musical Arrangement - Nested Below Waveform */}
              {sections.length > 0 && (
                <div className="hidden border-t border-slate-800">
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
            <div className="flex-1 overflow-y-auto py-4 px-0 space-y-4">

              <div
                className={
                  "rounded-lg border border-slate-800 bg-slate-900/60 p-3 transition-shadow " +
                  (softFocusActive ? "ring-2 ring-fuchsia-500/40 shadow-[0_0_0_2px_rgba(217,70,239,0.15)]" : "")
                }
              >
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
                      <div className="h-[820px]">
                        <DrumEditorPane
                          drumTrack={activeDrumTrack}
                          timeSignature={selectedMeasureRange.timeSignature ?? timeSig}
                          grooveWeights={activeGrooveMap}
                          selectedSectionIds={selectedSectionIds}
                          onSectionSelect={(sectionId) => {
                            handleSongMapSelectSection(sectionId);
                          }}
                          selectedBarIndex={selectedBarIndex}
                          onBarSelect={setSelectedBarIndex}
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
                        Run Section Generation for this section to unlock high-resolution editing, expressive
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

              <div className="sticky top-0 z-30 rounded-lg border border-slate-800 bg-slate-950/90 backdrop-blur p-3">
                <div className="flex flex-col gap-2 mb-2">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-[11px] uppercase tracking-wide text-slate-400">Song Map</div>
                      <div className="text-xs text-slate-300">Select Global controls or pick a section below</div>
                    </div>
                  </div>
                  <div className="flex justify-center">
                    <button
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        handleSongMapSelectGlobal();
                      }}
                      className={
                        "px-5 py-2 rounded-lg border text-sm font-semibold tracking-wide " +
                        (scopedControlsMode === "global"
                          ? "bg-slate-500/20 border-slate-400/70 text-slate-100"
                          : "bg-slate-900 border-slate-700 text-slate-100 hover:border-slate-500")
                      }
                    >
                      GLOBAL SONG CONTROLS
                    </button>
                  </div>
                </div>

                {sections.length === 0 ? (
                  <div className="text-xs text-slate-500">No sections yet — create/analyze an arrangement to populate the Song Map.</div>
                ) : (
                  <div className="relative h-12 bg-slate-900/60 border border-slate-800 rounded overflow-hidden">
                    {(() => {
                      const total = Math.max(
                        0.001,
                        Math.max(...sections.map((s) => s.end)) - Math.min(...sections.map((s) => s.start)),
                      );
                      const minStart = Math.min(...sections.map((s) => s.start));
                      const colorFor = (label: string) => {
                        const v = (label || "").toLowerCase();
                        if (v.includes("intro")) return "rgba(249,115,22,0.45)"; // orange
                        if (v.includes("verse")) return "rgba(59,130,246,0.45)"; // blue
                        if (v.includes("chorus")) return "rgba(34,197,94,0.45)"; // green
                        if (v.includes("bridge")) return "rgba(168,85,247,0.45)"; // purple
                        if (v.includes("outro")) return "rgba(239,68,68,0.45)"; // red
                        return "rgba(148,163,184,0.30)"; // slate
                      };

                      return sections.map((section) => {
                        const leftPct = ((section.start - minStart) / total) * 100;
                        const widthPct = Math.max(0.75, ((section.end - section.start) / total) * 100);
                        const isActive = scopedControlsMode === "section" && scopedControlsSectionId === section.id;
                        const measureRange = sectionToMeasureRange(
                          section,
                          bpm,
                          timeSig,
                          songMap,
                          tempoFlattenToleranceBpm,
                          drumTempoMode,
                        );
                        const startBarDisplay = Math.max(1, (measureRange?.startMeasure ?? 0) + 1);
                        const barCountDisplay = Math.max(0, measureRange?.measureCount ?? 0);
                        return (
                          <Tooltip
                            key={section.id}
                            content={`${section.label}`}
                            placement="top"
                            maxWidthClassName="w-56"
                            wrapperClassName={
                              "absolute inset-y-0 border-r border-slate-950/70 px-2 text-left transition-all " +
                              (isActive ? "ring-2 ring-fuchsia-400/60 z-10" : "hover:brightness-110")
                            }
                            wrapperStyle={{
                              left: `${leftPct}%`,
                              width: `${widthPct}%`,
                              backgroundColor: colorFor(section.label),
                            }}
                          >
                            <button
                              type="button"
                              onMouseDown={(e) => {
                                e.preventDefault();
                                handleSongMapSelectSection(section.id);
                              }}
                              className="h-full w-full"
                            >
                              <div className="h-full flex flex-col justify-center leading-tight">
                                <span className="text-sm font-semibold text-white truncate drop-shadow">
                                  {section.label}
                                </span>
                                <span className="text-[11px] text-white/90 truncate drop-shadow">
                                  Bar {startBarDisplay} · {barCountDisplay} bars
                                </span>
                              </div>
                            </button>
                          </Tooltip>
                        );
                      });
                    })()}
                  </div>
                )}
              </div>

              <div className="px-4">
                <div className="w-full rounded-lg border border-slate-800 bg-slate-900/70 p-4 space-y-5">
                  <div className="text-lg font-semibold text-white">Drum Track Creation</div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <div className="rounded-lg border border-emerald-700/40 bg-emerald-900/10 p-3 space-y-2">
                        <div className="text-sm font-semibold text-slate-100">Tempo / Time Signature</div>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                          <div>
                            <label className="text-[11px] text-slate-300">Time Signature</label>
                            <select
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={`${timeSig?.[0] ?? 4}/${timeSig?.[1] ?? 4}`}
                              onChange={(e) => {
                                const raw = String(e.target.value || "");
                                const [numRaw, denRaw] = raw.split("/");
                                const num = Math.max(1, Math.min(12, Math.round(Number(numRaw) || 4)));
                                const den = Math.max(1, Math.min(16, Math.round(Number(denRaw) || 4)));
                                setTimeSig([num, den]);
                              }}
                            >
                              <option value="4/4">4/4</option>
                              <option value="3/4">3/4</option>
                              <option value="2/4">2/4</option>
                              <option value="6/8">6/8</option>
                              <option value="12/8">12/8</option>
                              <option value="5/4">5/4</option>
                              <option value="7/8">7/8</option>
                            </select>
                          </div>
                          <div>
                            <label className="text-[11px] text-slate-300">BPM</label>
                            <input
                              type="number"
                              min={20}
                              max={300}
                              step={1}
                              value={Math.round(bpm || 120)}
                              onChange={(e) => {
                                const next = Number(e.target.value);
                                if (!Number.isFinite(next)) return;
                                setBpm(Math.max(20, Math.min(300, Math.round(next))));
                              }}
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                            />
                          </div>
                          <div>
                            <label className="text-[11px] text-slate-300">Beats / Bar</label>
                            <input
                              type="number"
                              min={1}
                              max={12}
                              step={1}
                              value={timeSig?.[0] ?? 4}
                              onChange={(e) => {
                                const next = Math.max(1, Math.min(12, Math.round(Number(e.target.value) || 4)));
                                setTimeSig([next, timeSig?.[1] ?? 4]);
                              }}
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                            />
                          </div>
                          <div>
                            <label className="text-[11px] text-slate-300">Beat Unit</label>
                            <select
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={timeSig?.[1] ?? 4}
                              onChange={(e) => {
                                const denom = Math.max(1, Math.min(16, Math.round(Number(e.target.value) || 4)));
                                setTimeSig([timeSig?.[0] ?? 4, denom]);
                              }}
                            >
                              <option value={2}>2</option>
                              <option value={4}>4</option>
                              <option value={8}>8</option>
                              <option value={16}>16</option>
                            </select>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-lg border border-amber-700/40 bg-amber-900/10 p-3 space-y-2">
                        <div className="text-sm font-semibold text-slate-100">Arrangement Tools</div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              setShowManualModal(true);
                            }}
                            className="px-3 py-1.5 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                          >
                            Manual Arrangement…
                          </button>
                          <button
                            type="button"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              setShowLookupModal(true);
                            }}
                            className="px-3 py-1.5 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                          >
                            Internet Lookup…
                          </button>
                          <button
                            type="button"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              setShowDrumPlayer(true);
                            }}
                            className="px-3 py-1.5 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                          >
                            Drum Player…
                          </button>
                        </div>
                        <div className="text-[11px] text-slate-400">Create sections first, then generate drums globally or per section.</div>
                      </div>

                      <div className="rounded-lg border border-amber-700/40 bg-amber-900/10 p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="text-sm font-semibold text-slate-100">Arrangement Builder</div>
                          <button
                            className="px-2 py-1 text-[11px] rounded bg-slate-800 border border-slate-700 text-slate-200"
                            type="button"
                            onMouseDown={(e) => {
                              e.preventDefault();
                              setScratchArrangement((prev) => [...prev, { label: "verse", bars: 8 }]);
                            }}
                          >
                            Add
                          </button>
                        </div>

                        <div>
                          <div className="text-[11px] text-slate-300 mb-1">Style</div>
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

                        <div className="space-y-2">
                          {scratchArrangement.map((row, idx) => (
                            <div key={`${idx}-${row.label}`} className="grid grid-cols-[1fr_72px_28px] gap-2 items-center">
                              <select
                                className="px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                                value={row.label}
                                onChange={(e) => {
                                  const v = e.target.value;
                                  setScratchArrangement((prev) => prev.map((r, i) => (i === idx ? { ...r, label: v } : r)));
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
                                  setScratchArrangement((prev) => prev.map((r, i) => (i === idx ? { ...r, bars: v } : r)));
                                }}
                                className="px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              />

                              <button
                                type="button"
                                className="h-7 rounded bg-rose-900/40 border border-rose-800 text-rose-200"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setScratchArrangement((prev) => prev.filter((_, i) => i !== idx));
                                }}
                              >
                                ×
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="rounded-lg border border-cyan-700/40 bg-cyan-900/10 p-3 space-y-2">
                        <div className="text-sm font-semibold text-slate-100">Groove Tools</div>
                        <div className="text-[11px] uppercase tracking-wide text-slate-500">Global Groove / Database Grooves</div>

                        <div>
                          <label className="text-[11px] text-slate-300">Overall Density</label>
                          <div className="flex items-center gap-2">
                            <Tooltip content="Decrease overall density">
                              <button
                                type="button"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setDrumOptions((prev) => ({ ...prev, density: clamp01((prev?.density ?? 0.6) - 0.05) }));
                                }}
                                className="px-2 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                              >
                                -
                              </button>
                            </Tooltip>
                            <Tooltip content="Overall density: how busy/complex the generated pattern is">
                              <MacroSlider
                                value={clamp01(drumOptions?.density ?? 0.6)}
                                onChange={(next) => setDrumOptions((prev) => ({ ...prev, density: clamp01(next) }))}
                                ariaLabel="Overall density"
                              />
                            </Tooltip>
                            <Tooltip content="Increase overall density">
                              <button
                                type="button"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setDrumOptions((prev) => ({ ...prev, density: clamp01((prev?.density ?? 0.6) + 0.05) }));
                                }}
                                className="px-2 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                              >
                                +
                              </button>
                            </Tooltip>
                            <div className="w-12 text-right text-[11px] text-slate-400 tabular-nums">
                              {Math.round(clamp01(drumOptions?.density ?? 0.6) * 100)}%
                            </div>
                          </div>
                        </div>

                        <div>
                          <label className="text-[11px] text-slate-300">Pocket &amp; Swing</label>
                          <div className="flex items-center gap-2">
                            <Tooltip content="Decrease pocket/swing">
                              <button
                                type="button"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setDrumOptions((prev) => ({ ...prev, swing: clamp01((prev?.swing ?? 0) - 0.05) }));
                                }}
                                className="px-2 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                              >
                                -
                              </button>
                            </Tooltip>
                            <Tooltip content="Pocket & swing: timing feel / shuffle amount">
                              <MacroSlider
                                value={clamp01(drumOptions?.swing ?? 0)}
                                onChange={(next) => setDrumOptions((prev) => ({ ...prev, swing: clamp01(next) }))}
                                ariaLabel="Pocket and swing"
                              />
                            </Tooltip>
                            <Tooltip content="Increase pocket/swing">
                              <button
                                type="button"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setDrumOptions((prev) => ({ ...prev, swing: clamp01((prev?.swing ?? 0) + 0.05) }));
                                }}
                                className="px-2 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                              >
                                +
                              </button>
                            </Tooltip>
                            <div className="w-12 text-right text-[11px] text-slate-400 tabular-nums">
                              {Math.round(clamp01(drumOptions?.swing ?? 0) * 100)}%
                            </div>
                          </div>
                        </div>

                        <div>
                          <label className="text-[11px] text-slate-300">Humanize</label>
                          <div className="flex items-center gap-2">
                            <Tooltip content="Decrease humanize">
                              <button
                                type="button"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setDrumOptions((prev) => ({ ...prev, humanize: clamp01((prev?.humanize ?? 0.6) - 0.05) }));
                                }}
                                className="px-2 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                              >
                                -
                              </button>
                            </Tooltip>
                            <Tooltip content="Humanize: timing/velocity variation for realism">
                              <MacroSlider
                                value={clamp01(drumOptions?.humanize ?? 0.6)}
                                onChange={(next) => setDrumOptions((prev) => ({ ...prev, humanize: clamp01(next) }))}
                                ariaLabel="Humanize"
                              />
                            </Tooltip>
                            <Tooltip content="Increase humanize">
                              <button
                                type="button"
                                onMouseDown={(e) => {
                                  e.preventDefault();
                                  setDrumOptions((prev) => ({ ...prev, humanize: clamp01((prev?.humanize ?? 0.6) + 0.05) }));
                                }}
                                className="px-2 py-1 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                              >
                                +
                              </button>
                            </Tooltip>
                            <div className="w-12 text-right text-[11px] text-slate-400 tabular-nums">
                              {Math.round(clamp01(drumOptions?.humanize ?? 0.6) * 100)}%
                            </div>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          <div>
                            <label className="text-[11px] text-slate-300">Groove Source</label>
                            <select
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={grooveSource}
                              onChange={(e) => {
                                const next = e.target.value;
                                setGrooveSource(next);
                                if (next === "egmd_phrases") {
                                  setGrooveMode("enhanced");
                                }
                              }}
                            >
                              <option value="pattern">Built-in</option>
                              <option value="egmd_phrases">E-GMD Phrases</option>
                            </select>
                          </div>

                          <div>
                            <label className="text-[11px] text-slate-300">EGMD Mode</label>
                            <select
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={grooveMode}
                              disabled={grooveSource !== "egmd_phrases"}
                              onChange={(e) => setGrooveMode(e.target.value)}
                            >
                              <option value="exact">Exact Clip</option>
                              <option value="enhanced">Enhanced</option>
                            </select>
                          </div>

                          <div>
                            <label className="text-[11px] text-slate-300">Style Group</label>
                            <select
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={styleGroup}
                              disabled={grooveSource !== "egmd_phrases"}
                              onChange={(e) => setStyleGroup(e.target.value)}
                            >
                              <option value="rock">Rock</option>
                              <option value="jazz">Jazz</option>
                              <option value="funk">Funk</option>
                              <option value="metal">Metal</option>
                              <option value="blues">Blues</option>
                              <option value="pop">Pop</option>
                              <option value="latin">Latin</option>
                              <option value="hiphop">Hip-Hop</option>
                              <option value="soul">Soul</option>
                            </select>
                          </div>

                          <div>
                            <label className="text-[11px] text-slate-300">EGMD Phrase</label>
                            <select
                              className="w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                              value={selectedEgmdPhraseId === null ? "" : String(selectedEgmdPhraseId)}
                              disabled={grooveSource !== "egmd_phrases"}
                              onChange={(e) => {
                                const raw = e.target.value;
                                if (!raw) {
                                  setSelectedEgmdPhraseId(null);
                                  return;
                                }
                                const next = Number(raw);
                                setSelectedEgmdPhraseId(Number.isFinite(next) ? next : null);
                              }}
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
                        </div>
                      </div>

                      <div className="rounded-lg border border-indigo-700/40 bg-indigo-900/10 p-3 space-y-2">
                        <div className="text-sm font-semibold text-slate-100">Groove Library</div>
                        {(() => {
                          const sectionId = scopedControlsSectionId;
                          if (!sectionId) {
                            return (
                              <div className="text-xs text-slate-400">
                                Select a section (in Advanced Drum Tools) to choose a groove for that section.
                              </div>
                            );
                          }
                          const selection = sectionGrooveSelections?.[sectionId] ?? {};
                          return (
                            <div className="space-y-2">
                              <div className="text-[11px] text-slate-400">
                                Section: <span className="text-slate-200">{sections.find((s) => s.id === sectionId)?.label || sectionId}</span>
                              </div>
                              <div className="text-[11px] text-slate-400">
                                Groove: <span className="text-slate-200">{selection.selectedGrooveId || "(none)"}</span>
                              </div>
                              <div className="text-[11px] text-slate-400">
                                Fill: <span className="text-slate-200">{selection.fillGrooveId || "(none)"}</span>
                                {selection.fillGrooveId ? (
                                  <>
                                    {" "}
                                    <span className="text-slate-500">@</span>{" "}
                                    <span className="text-slate-200">{selection.fillBarRelativeText || "last"}</span>
                                  </>
                                ) : null}
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    openSectionGrooveModal(sectionId);
                                  }}
                                  className="px-3 py-1.5 rounded border border-indigo-600/50 bg-indigo-900/20 hover:border-indigo-400 text-xs text-indigo-100"
                                >
                                  Open Groove Library
                                </button>
                                <button
                                  type="button"
                                  disabled={!selection.selectedGrooveId && !selection.fillGrooveId}
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    setSectionGrooveSelections((prev) => {
                                      const next = { ...(prev ?? {}) };
                                      delete next[sectionId];
                                      return next;
                                    });
                                  }}
                                  className="px-3 py-1.5 rounded border border-slate-700 bg-slate-900 hover:border-slate-500 text-xs text-slate-200 disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                  Clear
                                </button>
                              </div>
                            </div>
                          );
                        })()}
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-center">
                    <button
                      className="w-full max-w-md px-3 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-sm font-semibold"
                      type="button"
                      onMouseDown={(e) => {
                        e.preventDefault();
                        setDrumOptions((prev) => ({ ...prev, bpm, style: scratchStyle }));
                        setStyleGroup(scratchStyle);
                        buildScratchSong();
                      }}
                    >
                      Create Arrangement
                    </button>
                  </div>

                  <div className="rounded-lg border border-rose-700/40 bg-rose-900/10 p-3">
                    <div className="text-sm font-semibold text-slate-100 mb-2">Select Drummer</div>
                    <DrummerSelector
                      onSelect={(drummer) => {
                        setSelectedDrummer(drummer);
                        console.log("Selected drummer:", drummer.display_name);
                      }}
                      selectedDrummer={selectedDrummer}
                    />
                    <div
                      className={
                        "mt-2 text-xs " +
                        (sentientBadge.tone === "good"
                          ? "text-emerald-300"
                          : sentientBadge.tone === "warn"
                            ? "text-amber-300"
                            : sentientBadge.tone === "bad"
                              ? "text-rose-300"
                              : "text-slate-400")
                      }
                    >
                      {sentientBadge.label}
                    </div>
                    <div className="mt-3">
                      <SentientDebugPanel profile={sentientState?.profile} selection={sentientDebugState} />
                    </div>
                  </div>

                  <button
                    type="button"
                    disabled={bulkGenerating || generatingDrums}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleGenerateFullSong();
                    }}
                    className="w-full px-4 py-3 rounded-lg bg-gradient-to-r from-orange-600 to-rose-600 hover:from-orange-500 hover:to-rose-500 font-semibold text-white shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Generate Complete Song
                  </button>

                  <div className="pt-2 border-t border-slate-800" />

                  <div className="text-xl font-bold text-white">Advanced Drum Tools</div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                      <div className="text-lg font-bold text-slate-100">Global</div>
                      <select
                        className="mt-1 w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                        value="global"
                        onChange={() => {
                          // single option
                        }}
                      >
                        <option value="global">Global (Song)</option>
                      </select>
                    </div>

                    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                      <div className="text-lg font-bold text-slate-100">Section</div>
                      <select
                        className="mt-1 w-full px-2 py-1 bg-slate-800 text-slate-100 text-sm rounded border border-slate-700"
                        value={scopedControlsSectionId ?? ""}
                        onChange={(e) => {
                          const next = String(e.target.value || "");
                          if (!next) return;
                          handleSongMapSelectSection(next);
                          setScopedControlsMode("section");
                        }}
                      >
                        <option value="">Select a section from the Song Map…</option>
                        {sections.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                      <div className="mt-1 text-[11px] text-slate-400">Select a section from the Song Map above.</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3">
                      <div className="text-base font-semibold text-slate-100 mb-2">Global Tools</div>
                      <DrumOptionsPanel
                        options={drumOptions}
                        onChange={setDrumOptions}
                        drummerType={selectedDrummer?.style || selectedDrummer?.display_name || ""}
                      />

                      <div className="mt-3 rounded-lg border border-indigo-700/40 bg-indigo-900/10 p-3">
                        <div className="text-sm font-semibold text-slate-100">Notes</div>
                        <div className="mt-1 text-xs text-slate-400">
                          Global tools set the default behavior used across the song unless a section explicitly overrides it.
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                        <div className="text-base font-semibold text-slate-100">Section Tools</div>
                        {!scopedControlsSectionId ? (
                          <div className="text-xs text-slate-400 mt-1">Select a section from the Song Map to enable section tools.</div>
                        ) : (
                          <div className="text-xs text-slate-300 mt-1">
                            Editing: {sections.find((s) => s.id === scopedControlsSectionId)?.label || scopedControlsSectionId}
                          </div>
                        )}
                      </div>

                      <div className="flex items-center justify-between gap-3">
                        <div className="text-[11px] uppercase tracking-wide text-slate-500">Mini Editor</div>
                        <button
                          type="button"
                          onMouseDown={(e) => {
                            e.preventDefault();
                            setMiniEditorOpen((v) => !v);
                          }}
                          disabled={!scopedControlsSectionId}
                          className="shrink-0 px-3 py-1.5 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500 text-xs text-slate-200"
                        >
                          {miniEditorOpen ? "Hide Mini Editor" : "Show Mini Editor"}
                        </button>
                      </div>

                      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                        <DrumBuilderPanelV2
                          selectedRange={selectedMeasureRange}
                          onGenerate={handleGenerateDrums}
                          globalStyle={drumOptions.style || "rock"}
                          globalDrummer={selectedDrummer?.id || "jeff_porcaro"}
                          globalIntensity={Math.round(clamp01(drumOptions.density ?? 0.6) * 100)}
                          busy={generatingDrums || bulkGenerating}
                        />
                      </div>

                      {miniEditorOpen && (
                        <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
                          <div className="text-[11px] uppercase tracking-wide text-slate-500">Mini Editor</div>
                          {(() => {
                            const fallbackSectionId =
                              activeSectionId && activeSectionId !== "full-song" ? activeSectionId : null;
                            const effectiveSectionId = scopedControlsSectionId || fallbackSectionId;
                            if (!effectiveSectionId) {
                              return <div className="text-xs text-slate-400">Select a section to show section-relative bars.</div>;
                            }

                            const section = sections.find((s) => s.id === effectiveSectionId);
                            if (!section) {
                              return <div className="text-xs text-slate-400">Section not found.</div>;
                            }

                            const measureRange = sectionToMeasureRange(
                              section,
                              bpm,
                              timeSig,
                              songMap,
                              tempoFlattenToleranceBpm,
                              drumTempoMode,
                            );

                            const start = Math.max(0, measureRange?.startMeasure ?? 0);
                            const count = Math.max(0, measureRange?.measureCount ?? 0);

                            const directSectionTrack = sectionDrumTracks[effectiveSectionId] ?? null;
                            const activeSectionTrackFallback =
                              activeDrumTrack && activeSectionId === effectiveSectionId ? activeDrumTrack : null;

                            const bestOverlapTrack = (() => {
                              const keys = Object.keys(sectionDrumTracks ?? {}).filter(
                                (k) => k && k !== "__global__" && k !== "full-song",
                              );
                              if (!keys.length) return null;

                              const sectionStartBar = start;
                              const sectionEndBar = start + Math.max(0, count - 1);

                              let best: { id: string; overlap: number } | null = null;
                              for (const candidateId of keys) {
                                const track = sectionDrumTracks[candidateId];
                                if (!track?.notes?.length) continue;

                                const placement = sectionPlacementContexts?.[candidateId];
                                const candStart = Number.isFinite(Number(placement?.startMeasure))
                                  ? Number(placement?.startMeasure)
                                  : Math.min(
                                      ...track.notes
                                        .map((n) => Number(n.barIndex ?? 0))
                                        .filter((v) => Number.isFinite(v)),
                                    );
                                const candEnd = Number.isFinite(Number(placement?.endMeasure))
                                  ? Number(placement?.endMeasure)
                                  : Math.max(
                                      ...track.notes
                                        .map((n) => Number(n.barIndex ?? 0))
                                        .filter((v) => Number.isFinite(v)),
                                    );

                                if (!Number.isFinite(candStart) || !Number.isFinite(candEnd)) continue;
                                const overlap = Math.max(
                                  0,
                                  Math.min(sectionEndBar, candEnd) - Math.max(sectionStartBar, candStart) + 1,
                                );
                                if (overlap <= 0) continue;
                                if (!best || overlap > best.overlap) {
                                  best = { id: candidateId, overlap };
                                }
                              }

                              return best ? sectionDrumTracks[best.id] : null;
                            })();

                            const sectionTrack =
                              directSectionTrack ??
                              activeSectionTrackFallback ??
                              bestOverlapTrack ??
                              (fullSongDrumTrack && fullSongDrumTrack.notes?.length ? fullSongDrumTrack : null);
                            if (!sectionTrack) {
                              const keys = Object.keys(sectionDrumTracks ?? {});
                              return (
                                <div className="text-xs text-slate-400">
                                  No drum track generated for this section yet.
                                  {keys.length ? (
                                    <div className="mt-1 text-[10px] text-slate-500">Tracks: {keys.join(", ")}</div>
                                  ) : null}
                                </div>
                              );
                            }

                            if (!count) {
                              return <div className="text-xs text-slate-400">No bars for this section yet.</div>;
                            }

                            const minTrackBarIndex = sectionTrack.notes.length
                              ? Math.min(...sectionTrack.notes.map((n) => n.barIndex ?? 0))
                              : 0;

                            const trackLooksGlobalIndexed = sectionTrack.notes.length ? minTrackBarIndex >= start : true;
                            const trackLooksOneBased = sectionTrack.notes.length
                              ? minTrackBarIndex >= 1 && !sectionTrack.notes.some((n) => (n.barIndex ?? 0) === 0)
                              : false;
                            const trackBarIndexOffset = trackLooksOneBased ? 1 : 0;

                            return (
                              <div className="overflow-x-auto">
                                <div className="flex gap-2 min-w-max">
                                  {Array.from({ length: count }).map((_, relIdx) => {
                                    const globalBar = start + relIdx;
                                    const isActive = selectedBarIndex === globalBar;
                                    const trackBar = trackLooksGlobalIndexed ? globalBar : relIdx;
                                    const miniNotes = sectionTrack.notes
                                      .filter((n) => (n.barIndex ?? 0) === trackBar + trackBarIndexOffset)
                                      .map((n) => ({
                                        ...n,
                                        barIndex: 0,
                                      }));

                                    const miniTrack: DrumTrackForDCSM = {
                                      ...sectionTrack,
                                      track_id: `${sectionTrack.track_id}-mini-${effectiveSectionId}-${globalBar}`,
                                      notes: miniNotes,
                                    };

                                    return (
                                      <div key={`mini-bar-preview-${effectiveSectionId}-${relIdx}`} className="w-[168px]">
                                        <Tooltip
                                          content={`Section bar ${relIdx + 1} (global bar ${globalBar + 1})`}
                                          placement="top"
                                          maxWidthClassName="w-64"
                                          wrapperClassName="w-full"
                                        >
                                          <button
                                            type="button"
                                            onMouseDown={(e) => {
                                              e.preventDefault();
                                              focusMainEditorBar(globalBar);
                                            }}
                                            className={
                                              "w-full text-left rounded-lg border overflow-hidden " +
                                              (isActive
                                                ? "border-fuchsia-400/60 bg-fuchsia-500/10"
                                                : "border-slate-800 bg-slate-950/40 hover:border-slate-600")
                                            }
                                          >
                                          <div className="px-2 py-1 flex items-center justify-between">
                                            <div
                                              className={
                                                "text-[11px] font-semibold " +
                                                (isActive ? "text-fuchsia-100" : "text-slate-200")
                                              }
                                            >
                                              Bar {relIdx + 1}
                                            </div>
                                            <div className="text-[10px] text-slate-400">{globalBar + 1}</div>
                                          </div>
                                          <div className="h-[86px]">
                                            <DrumPianoRoll
                                              drumTrack={miniTrack}
                                              timeSignature={measureRange?.timeSignature ?? timeSig}
                                              bpm={bpm}
                                              playing={false}
                                              gridResolution={gridResolution}
                                              currentAspect="all"
                                              selectedNoteIds={miniSelectedNoteIds}
                                              onNoteSelect={setMiniSelectedNoteIds}
                                              pixelsPerBeat={(() => {
                                                const ts = measureRange?.timeSignature ?? timeSig;
                                                const beatsPerBar = Math.max(1, Number(ts?.[0] ?? 4) || 4);
                                                const previewWidthPx = 160;
                                                return Math.max(8, Math.floor(previewWidthPx / beatsPerBar));
                                              })()}
                                              totalSongBars={1}
                                              visibleStartMeasure={0}
                                              visibleMeasureCount={1}
                                              compact
                                            />
                                          </div>
                                          </button>
                                        </Tooltip>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            );
                          })()}
                        </div>
                      )}

                      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
                        <div className="text-[11px] uppercase tracking-wide text-slate-500">Bar Details</div>
                        {(() => {
                          const sectionId =
                            scopedControlsSectionId ||
                            (activeSectionId && activeSectionId !== "full-song" ? activeSectionId : null);
                          if (!sectionId) {
                            return <div className="text-xs text-slate-400">Select a section first.</div>;
                          }

                          const section = sections.find((s) => s.id === sectionId);
                          if (!section) {
                            return <div className="text-xs text-slate-400">Section not found.</div>;
                          }

                          const measureRange = sectionToMeasureRange(
                            section,
                            bpm,
                            timeSig,
                            songMap,
                            tempoFlattenToleranceBpm,
                            drumTempoMode,
                          );
                          const start = Math.max(0, measureRange?.startMeasure ?? 0);
                          const count = Math.max(0, measureRange?.measureCount ?? 0);
                          const placementForSection = {
                            startMeasure: start,
                            endMeasure: start + Math.max(0, count - 1),
                            tempos: measureRange?.tempos ?? [Number.isFinite(bpm) && bpm > 0 ? bpm : 120],
                            timeSignature: measureRange?.timeSignature ?? timeSig,
                            startTimeSec: measureRange?.startTime,
                          } satisfies DrumTrackPlacementContext;

                          if (selectedBarIndex === null) {
                            return <div className="text-xs text-slate-400">Click a mini bar preview to select a bar.</div>;
                          }

                          const inSection = selectedBarIndex >= start && selectedBarIndex < start + count;
                          if (!inSection) {
                            return (
                              <div className="text-xs text-slate-400">
                                Selected bar {selectedBarIndex + 1} is outside this section.
                              </div>
                            );
                          }

                          const sectionTrack =
                            sectionDrumTracks[sectionId] ?? (activeSectionId === sectionId ? activeDrumTrack : null);
                          if (!sectionTrack) {
                            return <div className="text-xs text-slate-400">No editable section track found for this section.</div>;
                          }

                          const minTrackBarIndex = sectionTrack.notes.length
                            ? Math.min(...sectionTrack.notes.map((n) => n.barIndex ?? 0))
                            : 0;

                          const trackLooksGlobalIndexed = sectionTrack.notes.length ? minTrackBarIndex >= start : true;
                          const trackLooksOneBased = sectionTrack.notes.length
                            ? minTrackBarIndex >= 1 && !sectionTrack.notes.some((n) => (n.barIndex ?? 0) === 0)
                            : false;
                          const trackBarIndexOffset = trackLooksOneBased ? 1 : 0;

                          const relIdx = selectedBarIndex - start;
                          const trackBar = (trackLooksGlobalIndexed ? selectedBarIndex : relIdx) + trackBarIndexOffset;
                          const barNotes = sectionTrack.notes.filter((n) => (n.barIndex ?? 0) === trackBar);

                          const canEdit = Boolean(sectionId && sectionId !== "full-song");

                          const applyTrackUpdate = (next: DrumTrackForDCSM) => {
                            setSectionDrumTracks((prev) => ({
                              ...prev,
                              [sectionId]: next,
                            }));
                            syncSectionMidiNotes(sectionId, next, sectionPlacementContexts[sectionId] ?? placementForSection);
                            applyTrackToMidiClip(sectionId, next, null, sectionPlacementContexts[sectionId] ?? placementForSection);
                            setMiniSelectedNoteIds([]);
                          };

                          const resolvedPpq = Number(sectionTrack.resolution_ppq) > 0 ? Number(sectionTrack.resolution_ppq) : 960;
                          const beatsPerBar = Math.max(
                            1,
                            Number((placementForSection.timeSignature ?? timeSig)?.[0] ?? 4) || 4,
                          );
                          const ticksPerBar = resolvedPpq * beatsPerBar;
                          const ticksPerSub = (() => {
                            try {
                              return getTicksPerSubdivision(resolvedPpq, placementForSection.timeSignature ?? timeSig, gridResolution);
                            } catch {
                              return Math.max(1, Math.round(resolvedPpq / 4));
                            }
                          })();
                          const subdivisionsPerBar = getSubdivisionsPerBar(gridResolution);

                          const instrumentCounts = (() => {
                            const map = new Map<string, number>();
                            for (const n of barNotes) {
                              const k = String((n as any)?.instrumentId ?? "?");
                              map.set(k, (map.get(k) ?? 0) + 1);
                            }
                            return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
                          })();

                          return (
                            <div className="space-y-2">
                              <div className="flex items-start justify-between gap-3">
                                <div>
                                  <div className="text-xs text-slate-200 font-semibold">Bar {relIdx + 1}</div>
                                  <div className="text-[11px] text-slate-400">
                                    Global bar {selectedBarIndex + 1} · Notes: {barNotes.length}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <button
                                    type="button"
                                    disabled={!canEdit}
                                    onMouseDown={(e) => {
                                      e.preventDefault();
                                      if (!canEdit) return;
                                      const kept = sectionTrack.notes.filter((n) => (n.barIndex ?? 0) !== trackBar);
                                      applyTrackUpdate({ ...sectionTrack, notes: kept });
                                    }}
                                    className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500 text-[11px] text-slate-200"
                                  >
                                    Clear Bar
                                  </button>
                                  <button
                                    type="button"
                                    disabled={!canEdit || trackBar - 1 < trackBarIndexOffset}
                                    onMouseDown={(e) => {
                                      e.preventDefault();
                                      if (!canEdit) return;
                                      const srcBar = trackBar - 1;
                                      const srcNotes = sectionTrack.notes.filter((n) => (n.barIndex ?? 0) === srcBar);
                                      if (!srcNotes.length) return;
                                      const dedupe = sectionTrack.notes.filter((n) => (n.barIndex ?? 0) !== trackBar);
                                      const suffix = Math.random().toString(36).slice(2, 8);
                                      const copied = srcNotes.map((n, idx) => ({
                                        ...n,
                                        id: `${n.id}-dup-${suffix}-${idx}`,
                                        barIndex: trackBar,
                                      }));
                                      applyTrackUpdate({ ...sectionTrack, notes: [...dedupe, ...copied] });
                                    }}
                                    className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500 text-[11px] text-slate-200"
                                  >
                                    Duplicate Prev
                                  </button>
                                </div>
                              </div>

                              <div className="flex flex-wrap items-center gap-2">
                                <button
                                  type="button"
                                  disabled={!canEdit}
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    if (!canEdit) return;
                                    setBarClipboard(barNotes.map((n) => ({ ...n, barIndex: 0 })));
                                  }}
                                  className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500 text-[11px] text-slate-200"
                                >
                                  Copy Bar
                                </button>
                                <button
                                  type="button"
                                  disabled={!canEdit || !barClipboard?.length}
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    if (!canEdit) return;
                                    if (!barClipboard?.length) return;
                                    const kept = sectionTrack.notes.filter((n) => (n.barIndex ?? 0) !== trackBar);
                                    const suffix = Math.random().toString(36).slice(2, 8);
                                    const pasted = barClipboard.map((n, idx) => ({
                                      ...n,
                                      id: `${n.id}-paste-${suffix}-${idx}`,
                                      barIndex: trackBar,
                                    }));
                                    applyTrackUpdate({ ...sectionTrack, notes: [...kept, ...pasted] });
                                  }}
                                  className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500 text-[11px] text-slate-200"
                                >
                                  Paste Bar
                                </button>
                                <button
                                  type="button"
                                  disabled={!canEdit || !barNotes.length}
                                  onMouseDown={(e) => {
                                    e.preventDefault();
                                    if (!canEdit) return;
                                    if (!barNotes.length) return;
                                    const nextNotes = sectionTrack.notes.map((n) => {
                                      if ((n.barIndex ?? 0) !== trackBar || n.locked) return n;
                                      const snapped =
                                        Math.round((n.tickInBar ?? 0) / Math.max(1, ticksPerSub)) * Math.max(1, ticksPerSub);
                                      const clamped = Math.max(0, Math.min(Math.max(0, ticksPerBar - 1), snapped));
                                      return {
                                        ...n,
                                        tickInBar: clamped,
                                      };
                                    });
                                    applyTrackUpdate({ ...sectionTrack, notes: nextNotes });
                                  }}
                                  className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500 text-[11px] text-slate-200"
                                >
                                  Quantize Bar ({gridResolution})
                                </button>
                              </div>

                              <div className="rounded border border-slate-800 bg-slate-950/30 p-2">
                                <div className="text-[10px] uppercase tracking-wide text-slate-500 mb-2">Add Note</div>
                                <div className="flex flex-wrap items-center gap-2">
                                  <select
                                    className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                                    value={barAddInstrumentId}
                                    onChange={(e) => setBarAddInstrumentId(e.target.value as DrumInstrumentId)}
                                    disabled={!canEdit}
                                  >
                                    {(
                                      [
                                        "kick",
                                        "snare_center",
                                        "snare_rim",
                                        "snare_ghost",
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
                                      ] as DrumInstrumentId[]
                                    ).map((id) => (
                                      <option key={id} value={id}>
                                        {id.replaceAll("_", " ")}
                                      </option>
                                    ))}
                                  </select>

                                  <Tooltip content="Step within bar" placement="top" maxWidthClassName="w-40">
                                    <select
                                      className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100"
                                      value={String(barAddStepIndex)}
                                      onChange={(e) => {
                                        const next = Number(e.target.value);
                                        setBarAddStepIndex(Number.isFinite(next) ? next : 0);
                                      }}
                                      disabled={!canEdit}
                                    >
                                      {Array.from({ length: subdivisionsPerBar }).map((_, idx) => (
                                        <option key={`step-${idx}`} value={String(idx)}>
                                          {idx + 1}/{subdivisionsPerBar}
                                        </option>
                                      ))}
                                    </select>
                                  </Tooltip>

                                  <button
                                    type="button"
                                    disabled={!canEdit}
                                    onMouseDown={(e) => {
                                      e.preventDefault();
                                      if (!canEdit) return;
                                      const tickInBar = Math.max(
                                        0,
                                        Math.min(Math.max(0, ticksPerBar - 1), barAddStepIndex * ticksPerSub),
                                      );
                                      const suffix = Math.random().toString(36).slice(2, 8);
                                      const id = `baradd-${sectionId}-${trackBar}-${tickInBar}-${suffix}`;
                                      const limb = inferLimbFromInstrument(barAddInstrumentId);
                                      const newNote: DrumNoteEvent = {
                                        id,
                                        barIndex: trackBar,
                                        tickInBar,
                                        tickLength: Math.max(1, Math.round(ticksPerSub * 0.95)),
                                        channel: 9,
                                        midiPitch: getMidiPitchForInstrument(barAddInstrumentId),
                                        velocity: 100,
                                        instrumentId: barAddInstrumentId,
                                        aspect: "groove",
                                        limbId: limb ?? undefined,
                                        isGhost: false,
                                        isAccent: false,
                                        isFlam: false,
                                        isDrag: false,
                                      };
                                      applyTrackUpdate({ ...sectionTrack, notes: [...sectionTrack.notes, newNote] });
                                      setMiniSelectedNoteIds([id]);
                                    }}
                                    className="px-2.5 py-1 rounded border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed bg-slate-900 hover:border-slate-500 text-[11px] text-slate-200"
                                  >
                                    Add
                                  </button>
                                </div>
                              </div>

                              {instrumentCounts.length ? (
                                <div className="text-[11px] text-slate-400">
                                  {instrumentCounts.slice(0, 8).map(([k, v]) => `${k}:${v}`).join(" · ")}
                                </div>
                              ) : (
                                <div className="text-[11px] text-slate-500">No notes in this bar.</div>
                              )}

                              {miniSelectedNoteIds.length > 0 && (
                                <div className="rounded border border-slate-800 bg-slate-950/70">
                                  <NoteInspector
                                    selectedNotes={sectionTrack.notes.filter((n) => miniSelectedNoteIds.includes(n.id))}
                                    onUpdateNotes={(patch) => {
                                      if (!miniSelectedNoteIds.length) return;
                                      const nextNotes = sectionTrack.notes.map((n) =>
                                        miniSelectedNoteIds.includes(n.id) && !n.locked ? { ...n, ...patch } : n,
                                      );
                                      applyTrackUpdate({ ...sectionTrack, notes: nextNotes });
                                    }}
                                    onNudgeTicks={(deltaTicks) => {
                                      if (!Number.isFinite(ticksPerBar) || ticksPerBar <= 0) return;

                                      const nextNotes = sectionTrack.notes.map((n) => {
                                        if (!miniSelectedNoteIds.includes(n.id) || n.locked) return n;

                                        const currentBar = Number(n.barIndex ?? 0);
                                        const currentTick = Number(n.tickInBar ?? 0);
                                        if (!Number.isFinite(currentBar) || !Number.isFinite(currentTick)) return n;

                                        const abs = currentBar * ticksPerBar + currentTick + deltaTicks;
                                        const absClamped = Math.max(0, abs);
                                        const nextBar = Math.floor(absClamped / ticksPerBar);
                                        const nextTick = ((absClamped % ticksPerBar) + ticksPerBar) % ticksPerBar;
                                        return {
                                          ...n,
                                          barIndex: nextBar,
                                          tickInBar: nextTick,
                                        };
                                      });

                                      applyTrackUpdate({ ...sectionTrack, notes: nextNotes });
                                    }}
                                    gridResolution={gridResolution}
                                    ppq={sectionTrack.resolution_ppq}
                                    timeSignature={placementForSection.timeSignature ?? timeSig}
                                    onClose={() => setMiniSelectedNoteIds([])}
                                  />
                                </div>
                              )}

                              {!canEdit && (
                                <div className="text-[11px] text-slate-500">
                                  Bar edits are enabled for section tracks (not full-song-only playback).
                                </div>
                              )}
                            </div>
                          );
                        })()}
                      </div>

                      <div className="rounded-lg border border-indigo-700/40 bg-indigo-900/10 p-3">
                        <div className="text-sm font-semibold text-slate-100">Notes</div>
                        <div className="mt-1 text-xs text-slate-400">
                          Section tools apply to the selected section only. Use Global tools for baseline behavior.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          </div>
        </div>

      </div>

      {sectionGrooveModalOpen && (
        <div className="fixed inset-0 z-[70]">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={closeSectionGrooveModal}
            role="presentation"
          />
          <div className="absolute inset-0 flex items-center justify-center p-4">
            <div className="w-full max-w-2xl rounded-lg border border-indigo-700/40 bg-slate-900 shadow-2xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-indigo-700/30 bg-indigo-900/10">
                <div>
                  <div className="text-sm font-semibold text-slate-100">Groove Library</div>
                  <div className="text-xs text-slate-400">Choose a groove/fill for this section.</div>
                </div>
                <button
                  className="text-slate-400 hover:text-slate-100"
                  onClick={closeSectionGrooveModal}
                  type="button"
                >
                  ✕
                </button>
              </div>

              <div className="p-4 space-y-3">
                <div className="text-xs text-slate-400">
                  Section:{" "}
                  <span className="text-slate-200">
                    {(() => {
                      const s = sections.find((row) => row.id === sectionGrooveModalSectionId);
                      return (s?.label || s?.id || sectionGrooveModalSectionId || "Section").toString();
                    })()}
                  </span>
                </div>

                <input
                  value={sectionGrooveQuery}
                  onChange={(e) => setSectionGrooveQuery(e.target.value)}
                  placeholder="Search grooves (e.g. four on the floor, bonham, paradiddle)"
                  className="w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-sm text-white"
                />

                <div className="flex flex-wrap gap-2">
                  {sectionQuickGrooveTags.map((tag) => (
                    <button
                      key={tag}
                      type="button"
                      className={`text-xs px-2 py-1 rounded border ${
                        sectionGrooveTag === tag
                          ? "bg-indigo-600 border-indigo-500 text-white"
                          : "bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"
                      }`}
                      onClick={() => {
                        const next = sectionGrooveTag === tag ? "" : tag;
                        setSectionGrooveTag(next);
                        void searchSectionGrooves(undefined, next);
                      }}
                    >
                      {tag}
                    </button>
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="px-3 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold disabled:opacity-50"
                    disabled={sectionGrooveLoading}
                    onClick={() => void searchSectionGrooves()}
                  >
                    {sectionGrooveLoading ? "Searching…" : "Search"}
                  </button>

                  <div className="flex items-center gap-2 text-xs text-slate-300">
                    <span>Fill bar (relative)</span>
                    <input
                      value={sectionFillBarRelativeText}
                      onChange={(e) => setSectionFillBarRelativeText(e.target.value)}
                      className="w-24 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100"
                    />
                    <span className="opacity-70">(0..N, last, -1)</span>
                  </div>

                  <button
                    type="button"
                    className="ml-auto text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700"
                    onClick={() => {
                      setSectionGrooveQuery("");
                      setSectionGrooveTag("");
                      setSectionGrooveResults([]);
                      setSectionSelectedGrooveId("");
                      setSectionFillGrooveId("");
                      setSectionFillBarRelativeText("last");
                    }}
                  >
                    Clear
                  </button>
                </div>

                {(sectionSelectedGrooveId || sectionFillGrooveId) && (
                  <div className="text-xs text-slate-300 space-y-1">
                    {sectionSelectedGrooveId && (
                      <div>
                        Selected groove: <span className="text-slate-100">{sectionSelectedGrooveId}</span>
                      </div>
                    )}
                    {sectionFillGrooveId && (
                      <div>
                        Fill: <span className="text-slate-100">{sectionFillGrooveId}</span> @ bar{" "}
                        <span className="text-slate-100">{sectionFillBarRelativeText || "last"}</span>
                      </div>
                    )}
                  </div>
                )}

                {sectionGrooveResults.length > 0 && (
                  <div className="space-y-2 max-h-[40vh] overflow-y-auto pr-1">
                    {sectionGrooveResults.slice(0, 24).map((item) => (
                      <div key={String(item?.id)} className="bg-slate-800/60 border border-slate-700 rounded p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-white truncate">{item?.title || item?.id}</div>
                            <div className="text-[11px] text-slate-400">{item?.source}</div>
                            {(item?.tempo_bpm || item?.meter || item?.bars) && (
                              <div className="text-[11px] text-slate-500">
                                {item?.tempo_bpm ? `${Math.round(Number(item.tempo_bpm))} BPM` : ""}
                                {item?.meter ? ` · ${String(item.meter)}` : ""}
                                {item?.bars ? ` · ${String(item.bars)} bars` : ""}
                              </div>
                            )}
                            <div className="mt-1 flex flex-wrap gap-1">
                              {(item?.tags || []).slice(0, 10).map((t: string) => (
                                <span
                                  key={t}
                                  className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-200"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                          <div className="flex flex-col gap-2 shrink-0">
                            <button
                              type="button"
                              className={`text-xs px-2 py-1 rounded border ${
                                auditioningGrooveId === String(item?.id)
                                  ? "bg-amber-600 border-amber-500 text-slate-950"
                                  : "bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700"
                              }`}
                              title={item?.has_audio ? "Play preview" : "Try preview (audio may be unavailable)"}
                              onClick={() => void auditionGroove(String(item?.id || ""))}
                            >
                              {auditioningGrooveId === String(item?.id) ? "Stop" : "Audition"}
                            </button>
                            <button
                              type="button"
                              className="text-xs px-2 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white"
                              onClick={() => setSectionSelectedGrooveId(String(item?.id || ""))}
                            >
                              Use as groove
                            </button>
                            <button
                              type="button"
                              className="text-xs px-2 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white"
                              onClick={() => setSectionFillGrooveId(String(item?.id || ""))}
                            >
                              Use as fill
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="px-4 py-3 border-t border-slate-800 flex items-center gap-2">
                <button
                  type="button"
                  className="px-3 py-2 rounded bg-slate-800 border border-slate-700 hover:bg-slate-700 text-sm"
                  onClick={closeSectionGrooveModal}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="ml-auto px-4 py-2 rounded bg-gradient-to-r from-orange-600 to-rose-600 hover:from-orange-500 hover:to-rose-500 font-semibold text-white"
                  onClick={() => {
                    if (!sectionGrooveModalSectionId) {
                      closeSectionGrooveModal();
                      return;
                    }
                    setSectionGrooveSelections((prev) => ({
                      ...prev,
                      [sectionGrooveModalSectionId]: {
                        selectedGrooveId: sectionSelectedGrooveId ? sectionSelectedGrooveId : undefined,
                        fillGrooveId: sectionFillGrooveId ? sectionFillGrooveId : undefined,
                        fillBarRelativeText: sectionFillGrooveId
                          ? (sectionFillBarRelativeText || "last")
                          : undefined,
                      },
                    }));
                    closeSectionGrooveModal();
                  }}
                >
                  Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {debugMode && (
        <div className="fixed inset-0 z-[80]">
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => setDebugMode(false)}
            role="presentation"
          />
          <div className="absolute inset-0 flex items-start justify-center p-4 overflow-y-auto">
            <div className="w-full max-w-3xl rounded-lg border border-slate-700 bg-slate-900 shadow-2xl">
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <div className="text-sm font-semibold text-slate-100">Debug</div>
                <button
                  className="text-slate-400 hover:text-slate-100"
                  onClick={() => setDebugMode(false)}
                  type="button"
                >
                  ✕
                </button>
              </div>
              <div className="p-4 space-y-3">
                <div className="border border-slate-800/60 rounded p-2">
                  <div className="font-semibold text-slate-200 mb-1">Last Generation</div>
                  {debugDrumGen ? (
                    <div className="space-y-1">
                      <div>sectionId: <span className="text-emerald-200">{debugDrumGen.payloadSectionId ?? "∅"}</span></div>
                      <div>drum_track: {debugDrumGen.hasDrumTrack ? "yes" : "no"}</div>
                      <div>drum_track notes: {debugDrumGen.drumTrackNotes}</div>
                      <div>legacy midi_notes: {debugDrumGen.hasLegacyNotes ? "yes" : "no"}</div>
                      <div>legacy note count: {debugDrumGen.legacyNotesCount}</div>
                      {Array.isArray((debugDrumGen as any).roadmapDebug) && (debugDrumGen as any).roadmapDebug.length > 0 && (
                        <div className="mt-2 border-t border-slate-800/60 pt-2">
                          <div className="font-semibold text-slate-200 mb-1">Roadmap Debug</div>
                          <div className="max-h-40 overflow-y-auto pr-1 space-y-1">
                            {(debugDrumGen as any).roadmapDebug.map((row: any, idx: number) => (
                              <div key={idx} className="border border-slate-800/60 rounded px-2 py-1">
                                <div className="flex items-center justify-between">
                                  <span className="font-semibold text-emerald-200">sec {String(row?.sectionIndex ?? idx)}</span>
                                  {typeof row?.shuffleMode === 'string' && (
                                    <span className="text-slate-400">{row.shuffleMode}</span>
                                  )}
                                </div>
                                <div className="text-slate-400">
                                  fill: {String(row?.fillFamily ?? '–')} ({String(row?.fillLength ?? '–')}) +{Number(row?.fillAdded ?? 0)}
                                </div>
                                <div className="text-slate-500">
                                  kick: tgt {Number(row?.kickDensityTarget ?? 0).toFixed?.(2) ?? String(row?.kickDensityTarget ?? '–')}, +{Number(row?.insertedKick ?? 0)} drop {Number(row?.droppedKick ?? 0)}
                                </div>
                                <div className="text-slate-500">
                                  snare: ghost tgt {Number(row?.ghostDensityTarget ?? 0).toFixed?.(2) ?? String(row?.ghostDensityTarget ?? '–')}, +{Number(row?.insertedGhost ?? 0)} drop {Number(row?.droppedGhostish ?? 0)}
                                </div>
                                {row?.reduction !== undefined && (
                                  <div className="text-slate-500">
                                    dropout: r={Number(row?.reduction ?? 0).toFixed?.(2) ?? String(row?.reduction)} stripped {Number(row?.dropoutStripped ?? 0)}
                                  </div>
                                )}
                                {(row?.extraCrashes || row?.rideBellified || row?.hatsOpened) && (
                                  <div className="text-slate-500">
                                    cym: crashes+{Number(row?.extraCrashes ?? 0)} bell {Number(row?.rideBellified ?? 0)} hatOpen+{Number(row?.hatsOpened ?? 0)}
                                  </div>
                                )}
                                {row?.endingStopTime && (
                                  <div className="text-amber-200">ending: stop-time removed {Number(row?.endingStopTimeRemoved ?? 0)}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
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
            </div>
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
    </>
  );
}
