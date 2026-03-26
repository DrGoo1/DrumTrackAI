import type { DrumGenerationConfig, DrumTrackForDCSM } from "../types/drumTrack";
import type { GrooveWeightMap } from "../types/grooveWeight";
import type { MidiNote as PianoRollNote } from "./PianoRoll";

type GrooveWeightMapLike = GrooveWeightMap | undefined;

export type DrumTrackPlacementContext = {
  startMeasure: number;
  endMeasure: number;
  tempos: number[];
  timeSignature: [number, number];
  startTimeSec?: number;
};

export type DrumGenerationResultShape = {
  drum_track?: DrumTrackForDCSM;
  drumTrack?: DrumTrackForDCSM;
  track?: DrumTrackForDCSM;
  data?: {
    drum_track?: DrumTrackForDCSM;
  };
  midi_notes?: any[];
  midiNotes?: any[];
  legacyNotes?: any[];
  groove_weight_map?: GrooveWeightMapLike;
  metadata?: {
    groove_weight_map?: GrooveWeightMapLike;
    [key: string]: unknown;
  };
};

export type DrumGenerationDebugSnapshot = {
  payloadSectionId: string | null;
  [key: string]: any;
  payloadGrooveSource?: string | null;
  payloadGrooveMode?: string | null;
  payloadEgmdPhraseId?: number | null;
  payloadEgmdMidiPath?: string | null;
  hasDrumTrack: boolean;
  drumTrackNotes: number;
  hasLegacyNotes: boolean;
  legacyNotesCount: number;
  builderVersion?: string | null;
  performanceFromLlm?: boolean | null;
  egmdExactMode?: boolean | null;
  egmdPhraseUsed?: any | null;
  egmdMidiPathUsed?: string | null;
  grooveSourceUsed?: string | null;
  grooveModeUsed?: string | null;
  roadmapDebug?: any[] | null;
};

export type ApplyDrumGenerationDeps = {
  bpm: number | null;
  timeSig: [number, number];
  setSectionDrumTracks: (
    updater: (prev: Record<string, DrumTrackForDCSM>) => Record<string, DrumTrackForDCSM>,
  ) => void;
  setSectionGrooveMaps: (
    updater: (prev: Record<string, GrooveWeightMapLike>) => Record<string, GrooveWeightMapLike>,
  ) => void;
  setNotes: (updater: (prev: PianoRollNote[]) => PianoRollNote[]) => void;
  syncSectionMidiNotes: (
    sectionId: string,
    track: DrumTrackForDCSM,
    placement?: DrumTrackPlacementContext,
  ) => void;
  ensureSectionSelection: (sectionId: string) => void;
  applyTrackToMidiClip: (
    sectionId?: string | null,
    track?: DrumTrackForDCSM | null,
    legacyNotes?: any[] | null,
    placement?: DrumTrackPlacementContext,
  ) => void;
  setDebugDrumGen?: (snapshot: DrumGenerationDebugSnapshot) => void;
};

export type ApplyDrumGenerationOptions = {
  placementContext?: DrumTrackPlacementContext;
  convertTrackToMidiNotes?: (
    track: DrumTrackForDCSM,
    placement: DrumTrackPlacementContext,
  ) => PianoRollNote[];
  gridSec?: number;
  hydrateLegacyNote?: (note: any, idx: number, gridSec: number, prefix: string) => PianoRollNote;
  legacyNotePrefix?: string;
  synthesizeLegacyTrack?: (
    legacyNotes: any[],
    sectionId: string,
    config: DrumGenerationConfig,
    fallbackBpm: number,
  ) => DrumTrackForDCSM | null;
};

export const GLOBAL_FALLBACK_SECTION_ID = "__global__";

const MAX_DRUM_TRACK_SCAN_DEPTH = 4;

const alignTrackBarsToPlacement = (
  track: DrumTrackForDCSM,
  placement: DrumTrackPlacementContext,
): DrumTrackForDCSM => {
  if (!track?.notes?.length) {
    return track;
  }
  const offset = placement.startMeasure ?? 0;
  if (!offset) {
    return track;
  }
  const minBar = track.notes.reduce((min, note) => {
    const value = Number(note.barIndex ?? 0);
    return Number.isFinite(value) ? Math.min(min, value) : min;
  }, Number.POSITIVE_INFINITY);

  if (!Number.isFinite(minBar) || minBar >= offset) {
    return track;
  }

  let mutated = false;
  const adjustedNotes = track.notes.map((note) => {
    const current = Number(note.barIndex ?? 0);
    if (!Number.isFinite(current)) {
      return note;
    }
    mutated = true;
    return {
      ...note,
      barIndex: current + offset,
    };
  });

  return mutated ? { ...track, notes: adjustedNotes } : track;
};

const tileTrackAcrossPlacement = (
  track: DrumTrackForDCSM,
  placement: DrumTrackPlacementContext,
): DrumTrackForDCSM => {
  if (!track?.notes?.length) {
    return track;
  }
  const targetBars = Math.max(1, (placement.endMeasure ?? 0) - (placement.startMeasure ?? 0) + 1);
  if (targetBars <= 1) {
    return track;
  }

  const bars = track.notes
    .map((n) => Number(n.barIndex ?? 0))
    .filter((v) => Number.isFinite(v));
  if (!bars.length) {
    return track;
  }
  const minBar = Math.min(...bars);
  const maxBar = Math.max(...bars);
  const generatedBars = Math.max(1, maxBar - minBar + 1);
  if (generatedBars >= targetBars) {
    return track;
  }

  const reps = Math.ceil(targetBars / generatedBars);
  const baseNotes = track.notes;
  const tiled: typeof baseNotes = [];
  for (let rep = 0; rep < reps; rep += 1) {
    for (const note of baseNotes) {
      const current = Number(note.barIndex ?? 0);
      if (!Number.isFinite(current)) {
        continue;
      }
      const nextBar = current + rep * generatedBars;
      if (nextBar < placement.startMeasure) {
        continue;
      }
      if (nextBar > placement.endMeasure) {
        continue;
      }
      tiled.push({
        ...note,
        id: `${String(note.id)}-r${rep}`,
        barIndex: nextBar,
      });
    }
  }

  return tiled.length ? { ...track, notes: tiled } : track;
};

const normalizeTickInBarOverflow = (
  track: DrumTrackForDCSM,
  placement: DrumTrackPlacementContext,
): DrumTrackForDCSM => {
  if (!track?.notes?.length) {
    return track;
  }
  const ppq = Number(track.resolution_ppq) > 0 ? Number(track.resolution_ppq) : 960;
  const beatsPerBar = placement.timeSignature?.[0] ?? 4;
  const ticksPerBar = ppq * Math.max(1, beatsPerBar);
  if (!Number.isFinite(ticksPerBar) || ticksPerBar <= 0) {
    return track;
  }

  const barValues = track.notes
    .map((n) => Number(n.barIndex ?? 0))
    .filter((v) => Number.isFinite(v));
  const minBar = barValues.length ? Math.min(...barValues) : 0;
  const maxBar = barValues.length ? Math.max(...barValues) : 0;
  const barRange = maxBar - minBar;

  let mutated = false;
  const normalized = track.notes.map((note) => {
    const rawBar = Number(note.barIndex ?? 0);
    const rawTick = Number(note.tickInBar ?? 0);
    if (!Number.isFinite(rawBar) || !Number.isFinite(rawTick)) {
      return note;
    }

    // If tickInBar is already within the bar, we normally leave it alone.
    // However, some generator outputs appear to collapse barIndex while encoding
    // absolute tick offsets inside tickInBar. In that case, treat rawTick as absolute.
    const treatTickAsAbsolute = barRange === 0 && rawTick >= ticksPerBar;

    if (!treatTickAsAbsolute && rawTick >= 0 && rawTick < ticksPerBar) {
      return note;
    }

    const absTicks = treatTickAsAbsolute ? rawTick : rawBar * ticksPerBar + rawTick;
    const carryBars = Math.floor(absTicks / ticksPerBar);
    const nextTick = ((absTicks % ticksPerBar) + ticksPerBar) % ticksPerBar;
    mutated = true;
    return {
      ...note,
      barIndex: (treatTickAsAbsolute ? (placement.startMeasure ?? 0) : 0) + carryBars,
      tickInBar: nextTick,
    };
  });

  return mutated ? { ...track, notes: normalized } : track;
};

export const deepFindDrumTrack = (
  obj: unknown,
  depth = 0,
): DrumTrackForDCSM | undefined => {
  if (!obj || typeof obj !== "object" || depth > MAX_DRUM_TRACK_SCAN_DEPTH) {
    return undefined;
  }

  if (Array.isArray(obj)) {
    for (const item of obj) {
      const found = deepFindDrumTrack(item, depth + 1);
      if (found) {
        return found;
      }
    }
    return undefined;
  }

  const candidate = obj as Partial<DrumTrackForDCSM>;
  if (Array.isArray(candidate.notes)) {
    return candidate as DrumTrackForDCSM;
  }

  for (const key of Object.keys(candidate)) {
    const found = deepFindDrumTrack((candidate as Record<string, unknown>)[key], depth + 1);
    if (found) {
      return found;
    }
  }

  return undefined;
};

export const normalizeDrumTrackFromResult = (
  result: DrumGenerationResultShape,
): DrumTrackForDCSM | undefined => {
  return (
    (result.drum_track as DrumTrackForDCSM | undefined) ??
    (result.drumTrack as DrumTrackForDCSM | undefined) ??
    (result.track as DrumTrackForDCSM | undefined) ??
    (result.data?.drum_track as DrumTrackForDCSM | undefined) ??
    deepFindDrumTrack(result)
  );
};

export const normalizeLegacyNotesFromResult = (result: DrumGenerationResultShape): any[] | undefined => {
  return (
    (result.midi_notes as any[] | undefined) ??
    (result.midiNotes as any[] | undefined) ??
    (result.legacyNotes as any[] | undefined)
  );
};

function quantizeTick(value: number, step: number) {
  if (!Number.isFinite(value) || !Number.isFinite(step) || step <= 0) return value;
  return Math.round(value / step) * step;
}

function stepFromQuantizationBase(base: unknown, ppq: number) {
  const b = typeof base === "string" ? base.toLowerCase() : "";
  if (!Number.isFinite(ppq) || ppq <= 0) return null;
  if (b === "8th") return ppq / 2;
  if (b === "16th") return ppq / 4;
  if (b === "32nd") return ppq / 8;
  if (b === "64th") return ppq / 16;
  return ppq / 4;
}

function quantizeDrumTrackToGrid(
  track: DrumTrackForDCSM,
  timeSignature: [number, number],
): DrumTrackForDCSM {
  const ppq = Number(track.resolution_ppq || 960);
  const beatsPerBar = Number(timeSignature?.[0] || 4);
  const ticksPerBar = ppq * beatsPerBar;
  const step = stepFromQuantizationBase(track.performance_spec?.quantizationBase, ppq);
  if (!step || !Number.isFinite(ticksPerBar) || ticksPerBar <= 0) return track;

  const notes = track.notes.map((n) => {
    const tickInBarRaw = Number(n.tickInBar ?? 0);
    const tickLenRaw = Number(n.tickLength ?? 0);
    const tickInBar = Math.max(0, Math.min(ticksPerBar - 1, quantizeTick(tickInBarRaw, step)));
    const tickLength = Math.max(step, quantizeTick(Math.max(1, tickLenRaw), step));
    return {
      ...n,
      tickInBar,
      tickLength,
    };
  });

  return {
    ...track,
    notes,
  };
}

export function applyDrumGenerationResult(
  result: DrumGenerationResultShape,
  payload: DrumGenerationConfig,
  deps: ApplyDrumGenerationDeps,
  options: ApplyDrumGenerationOptions = {},
): boolean {
  const {
    bpm,
    timeSig,
    setSectionDrumTracks,
    setSectionGrooveMaps,
    setNotes,
    syncSectionMidiNotes,
    ensureSectionSelection,
    applyTrackToMidiClip,
    setDebugDrumGen,
  } = deps;

  const {
    placementContext,
    convertTrackToMidiNotes,
    gridSec,
    hydrateLegacyNote,
    legacyNotePrefix = "legacy",
    synthesizeLegacyTrack,
  } = options;

  const drumTrackCandidate = normalizeDrumTrackFromResult(result);
  const legacyNotesCandidate = normalizeLegacyNotesFromResult(result);
  const sectionId = payload.sectionId ?? null;
  const metadata = (result as any)?.metadata ?? (result as any)?.data?.metadata ?? null;

  const debugSnapshot: DrumGenerationDebugSnapshot = {
    payloadSectionId: sectionId,
    payloadGrooveSource: (payload as any)?.grooveSource ?? null,
    payloadGrooveMode: (payload as any)?.grooveMode ?? null,
    payloadEgmdPhraseId: (payload as any)?.egmdPhraseId ?? null,
    payloadEgmdMidiPath: (payload as any)?.egmdMidiPath ?? null,
    hasDrumTrack: Boolean(drumTrackCandidate),
    drumTrackNotes: drumTrackCandidate?.notes?.length ?? 0,
    hasLegacyNotes: Array.isArray(legacyNotesCandidate),
    legacyNotesCount: legacyNotesCandidate?.length ?? 0,
    builderVersion: metadata?.builder_version ?? metadata?.builderVersion ?? null,
    performanceFromLlm: metadata?.performance_from_llm ?? metadata?.performanceFromLlm ?? null,
    egmdExactMode: metadata?.egmd_exact_mode ?? null,
    egmdPhraseUsed: metadata?.egmdPhrase ?? null,
    egmdMidiPathUsed: metadata?.egmd_midi_path ?? null,
    grooveSourceUsed: metadata?.groove_source ?? null,
    grooveModeUsed: metadata?.groove_mode ?? null,
    roadmapDebug: Array.isArray(metadata?.roadmapDebug) ? metadata.roadmapDebug : null,
  };

  setDebugDrumGen?.(debugSnapshot);
  console.log("🥁 DCSM debug:", debugSnapshot);

  if (drumTrackCandidate?.notes?.length) {
    const effectiveSectionId = sectionId ?? GLOBAL_FALLBACK_SECTION_ID;

    const isEgmdExact =
      (payload.grooveSource || "").toLowerCase() === "egmd_phrases" &&
      (payload.grooveMode || "").toLowerCase() === "exact";

    const isFullSongBuild =
      String((payload as any)?.buildScope || "").toLowerCase() === "full_song" ||
      sectionId === "full-song";

    if (sectionId) {
      const placementForSection = placementContext ?? {
        startMeasure: payload.startMeasure,
        endMeasure: payload.endMeasure,
        tempos: payload.tempos,
        timeSignature: payload.timeSignature,
      };

      const normalizedCandidate = placementForSection
        ? normalizeTickInBarOverflow(drumTrackCandidate, placementForSection)
        : drumTrackCandidate;

      const alignedBaseTrack = placementForSection
        ? alignTrackBarsToPlacement(normalizedCandidate, placementForSection)
        : normalizedCandidate;

      const shouldTile = placementForSection ? (!isFullSongBuild || isEgmdExact) : false;
      const alignedTrack = shouldTile
        ? tileTrackAcrossPlacement(alignedBaseTrack, placementForSection)
        : alignedBaseTrack;

      const quantizedTrack = isEgmdExact
        ? alignedTrack
        : quantizeDrumTrackToGrid(
            alignedTrack,
            placementForSection.timeSignature ?? payload.timeSignature ?? timeSig,
          );

      try {
        const counts: Record<string, number> = {};
        for (const n of quantizedTrack.notes || []) {
          const id = String((n as any)?.instrumentId ?? (n as any)?.instrument_id ?? "");
          const key = id || "<missing>";
          counts[key] = (counts[key] || 0) + 1;
        }
        const top = Object.entries(counts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 12);
        const snapshot = {
          sectionId,
          unique: Object.keys(counts).length,
          top,

          // If we only see snare-like instruments, this is a strong signal the backend
          // is producing snare-only (as opposed to the grid hiding lanes).
          snareOnly:
            Object.keys(counts).length > 0 &&
            Object.keys(counts).every((k) => k.toLowerCase().startsWith("snare") || k === "<missing>"),
        };

        console.log("[DrumGen] instrumentId counts", snapshot);
        console.log("[DrumGen] instrumentId counts json", JSON.stringify(snapshot));
      } catch {
        // ignore
      }

      const minBar = quantizedTrack.notes.reduce((min, note) => {
        const v = Number(note.barIndex ?? 0);
        return Number.isFinite(v) ? Math.min(min, v) : min;
      }, Number.POSITIVE_INFINITY);
      const maxBar = quantizedTrack.notes.reduce((max, note) => {
        const v = Number(note.barIndex ?? 0);
        return Number.isFinite(v) ? Math.max(max, v) : max;
      }, 0);
      const placementSpan =
        Math.max(1, (placementForSection.endMeasure ?? 0) - (placementForSection.startMeasure ?? 0) + 1);
      const generatedSpan = Number.isFinite(minBar) ? Math.max(1, maxBar - minBar + 1) : null;
      console.info("[FullSongDebug] section applied", {
        sectionId,
        placement: {
          startMeasure: placementForSection.startMeasure,
          endMeasure: placementForSection.endMeasure,
          spanBars: placementSpan,
        },
        notes: quantizedTrack.notes.length,
        barRange: {
          minBar: Number.isFinite(minBar) ? minBar : null,
          maxBar,
          spanBars: generatedSpan,
        },
      });

      setSectionDrumTracks((prev) => ({
        ...prev,
        [sectionId]: quantizedTrack,
      }));

      const grooveMapFromResult =
        (result.groove_weight_map ?? result.metadata?.groove_weight_map) as GrooveWeightMapLike;
      if (grooveMapFromResult) {
        setSectionGrooveMaps((prev) => ({
          ...prev,
          [sectionId]: grooveMapFromResult,
        }));
      }

      if (placementContext) {
        syncSectionMidiNotes(sectionId, quantizedTrack, placementContext);
      } else {
        syncSectionMidiNotes(sectionId, quantizedTrack);
      }
      ensureSectionSelection(sectionId);

      applyTrackToMidiClip(sectionId, quantizedTrack, null, placementContext);
      console.info(
        `[DrumGen] Applied DCSM track (${quantizedTrack.notes.length} notes) to MIDI clip`,
      );
      return true;
    } else {
      console.warn(
        "⚠️ Received DCSM drum_track without sectionId; applying as global track",
      );
      console.info(
        "[DrumGen] Set sectionDrumTracks key:",
        effectiveSectionId,
        "notes=",
        drumTrackCandidate.notes.length,
      );
      if (convertTrackToMidiNotes) {
        const maxBarIndex = drumTrackCandidate.notes.reduce((max, note) => {
          const candidate = Number(note.barIndex ?? 0);
          return Number.isFinite(candidate) && candidate > max ? candidate : max;
        }, 0);
        const inferredPlacement: DrumTrackPlacementContext = {
          startMeasure: 0,
          endMeasure: Math.max(0, maxBarIndex),
          tempos: [typeof bpm === "number" && bpm > 0 ? bpm : 120],
          timeSignature: timeSig,
          startTimeSec: 0,
        };
        const convertedNotes = convertTrackToMidiNotes(drumTrackCandidate, inferredPlacement);
        if (convertedNotes.length) {
          setNotes((prev) => [...prev, ...convertedNotes]);
          console.info(
            `[DrumGen] Added ${convertedNotes.length} global piano-roll notes from DCSM track`,
          );
        }
      }
      setSectionDrumTracks((prev) => ({
        ...prev,
        [effectiveSectionId]: drumTrackCandidate,
      }));
      applyTrackToMidiClip(sectionId, drumTrackCandidate);
      console.info(
        `[DrumGen] Applied DCSM track (${drumTrackCandidate.notes.length} notes) to MIDI clip`,
      );
      return true;
    }
  }

  if (Array.isArray(legacyNotesCandidate)) {
    const ensureHydratedNotes = () => {
      if (!hydrateLegacyNote) {
        return legacyNotesCandidate;
      }
      const subdivision = typeof gridSec === "number" && Number.isFinite(gridSec) ? gridSec : 0.125;
      return legacyNotesCandidate.map((note, idx) => hydrateLegacyNote(note, idx, subdivision, legacyNotePrefix));
    };

    if (!legacyNotesCandidate.length) {
      console.warn("⚠️ Drum generation returned no notes");
    }

    if (sectionId) {
      if (synthesizeLegacyTrack) {
        const synthesizedTrack = synthesizeLegacyTrack(
          legacyNotesCandidate,
          sectionId,
          payload,
          typeof bpm === "number" ? bpm : 120,
        );
        if (synthesizedTrack) {
          console.warn(
            `⚠️ Drum builder returned legacy data for ${sectionId}; synthesized editable track.`,
          );
          console.info(
            `[DrumGen] Synthesized track has ${synthesizedTrack.notes?.length ?? 0} notes after legacy conversion`,
          );
          const placementForSection = placementContext ?? {
            startMeasure: payload.startMeasure,
            endMeasure: payload.endMeasure,
            tempos: payload.tempos,
            timeSignature: payload.timeSignature,
          };
          const alignedSynthTrack = placementForSection
            ? alignTrackBarsToPlacement(synthesizedTrack, placementForSection)
            : synthesizedTrack;
          setSectionDrumTracks((prev) => ({
            ...prev,
            [sectionId]: alignedSynthTrack,
          }));
          if (placementContext) {
            syncSectionMidiNotes(sectionId, alignedSynthTrack, placementContext);
          } else {
            syncSectionMidiNotes(sectionId, alignedSynthTrack);
          }
          ensureSectionSelection(sectionId);
          applyTrackToMidiClip(sectionId, alignedSynthTrack, null, placementContext);
          return true;
        }
      }

      const hydrated = ensureHydratedNotes();
      if (hydrated.length) {
        setNotes((prev) => [...prev, ...hydrated]);
      }
      applyTrackToMidiClip(sectionId, null, legacyNotesCandidate);
      return false;
    }

    const hydrated = ensureHydratedNotes();
    if (hydrated.length) {
      setNotes((prev) => [...prev, ...hydrated]);
      console.log(`🎵 Added ${hydrated.length} drum notes to piano roll`);
    } else {
      console.warn("⚠️ Drum generation returned no notes");
    }
    applyTrackToMidiClip(sectionId, null, legacyNotesCandidate);
    return false;
  }

  console.warn("⚠️ Drum generation returned no data for playback");
  return false;
}
