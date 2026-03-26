import { create } from "zustand";
import { resolveApiBaseNormalized } from "../../utils/apiBase";
import type { DrumGenerationConfig } from "../../types/drumTrack";
import {
  DEFAULT_INHERIT,
  createDefaultArrangement,
  createDefaultImportState,
  createDefaultGlobalDefaults,
  type V3CoachAnalysis,
  type V3CoachGoal,
  type V3CoachMetrics,
  type V3ScratchRow,
  type V3WorkflowMode,
  type V3FieldGroup,
  type V3InheritFlag,
  type V3SectionOverrideState,
  type V3BarEditState,
  type V3Store,
} from "./types";

function clone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T;
}

function v3SectionId(idx: number, section: { startSec: number; endSec: number }): string {
  return `v3-${idx}-${Number(section.startSec || 0).toFixed(3)}-${Number(section.endSec || 0).toFixed(3)}`;
}

function createDefaultSectionOverrideState(): V3SectionOverrideState {
  return {
    locked: false,
    inherit: { ...DEFAULT_INHERIT },
    overrides: {},
    inheritGlobalPresets: true,
    presetStack: [],
  };
}

function createDefaultBarEditState(): V3BarEditState {
  return {
    addedNotes: [],
    deletedNoteIds: [],
    tickDeltaByNoteId: {},
    forceFill: false,
    suppressFill: false,
  };
}

function pickOverrideGroups(overrides: Partial<DrumGenerationConfig>, group: V3FieldGroup): Partial<DrumGenerationConfig> {
  // This is intentionally conservative and explicit. We can expand field mappings as v3 panels are implemented.
  switch (group) {
    case "identity": {
      const { style, drummer, publicDrummerId, drummerPersona } = overrides;
      return { style, drummer, publicDrummerId, drummerPersona };
    }
    case "generation": {
      const {
        intensity,
        variation,
        generationMode,
        buildScope,
        songStyle,
        songSections,
        chorusRidePreference,
        cymbalFocusMode,
        hatsToRideBlend,
        hatsToRideThreshold,
        rideBellPercent,
        footHatPulseSubdivision,
        footHatPulseApply,
      } = overrides;
      return {
        intensity,
        variation,
        generationMode,
        buildScope,
        songStyle,
        songSections,
        chorusRidePreference,
        cymbalFocusMode,
        hatsToRideBlend,
        hatsToRideThreshold,
        rideBellPercent,
        footHatPulseSubdivision,
        footHatPulseApply,
      };
    }
    case "humanization": {
      const { humanize, humanizeAmount, ghostNoteAmount, swingAmount } = overrides;
      return { humanize, humanizeAmount, ghostNoteAmount, swingAmount };
    }
    case "fills": {
      const { fillType, fillDensity, fillControls, fillLocations } = overrides;
      return { fillType, fillDensity, fillControls, fillLocations };
    }
    case "rudiments": {
      const { rudimentControls, rudimentBlocks } = overrides;
      return { rudimentControls, rudimentBlocks };
    }
    case "groove": {
      const { grooveSource, grooveMode, styleGroup, grooveControls, selectedGrooveId, grooveUse, fillGrooveId, fillBarIndex } = overrides;
      return { grooveSource, grooveMode, styleGroup, grooveControls, selectedGrooveId, grooveUse, fillGrooveId, fillBarIndex };
    }
    case "egmd": {
      const { egmdPhraseId, egmdPhraseOverrides } = overrides;
      return { egmdPhraseId, egmdPhraseOverrides };
    }
    case "brain": {
      const { brainConfig } = overrides;
      return { brainConfig };
    }
    case "guide": {
      const { guideEnabled, guideInstrument } = overrides;
      return { guideEnabled, guideInstrument };
    }
    default:
      return {};
  }
}

export const useV3Store = create<V3Store>((set, get) => ({
  env: {
    apiBase: resolveApiBaseNormalized(),
  },

  workflowMode: "audio" as V3WorkflowMode,
  scratchArrangement: [{ label: "verse", bars: 8 }, { label: "chorus", bars: 8 }] as V3ScratchRow[],

  globalDefaults: createDefaultGlobalDefaults(),
  sectionOverrides: {},
  barEdits: {},
  auditionRequest: null,

  arrangement: createDefaultArrangement(),

  importState: createDefaultImportState(),

  generatedDrumTrack: null,

  playheadSec: 0,

  selection: {
    selectedSectionId: null,
    selectedBarIndex: null,
    selectedTrackId: null,
    selectedClipId: null,
    selectedNoteIds: [],
  },

  ui: {
    editorTab: "bar_tools",
    showLegacyParity: false,
    arrangementOwner: "v3",
    inspectorView: "both",
    presetPreview: false,
    drummerPickerOpen: false,
    drummerPickerTarget: { scope: "global" },
    autoGenerateNonce: 0,
  },

  coach: {
    availableGoals: null,
    selectedGoalIds: [],
    lastAnalysis: null,
    lastTrackMetrics: null,
    snapshot: null,
    snapshotPendingAfter: false,
  },

  // workflow
  setWorkflowMode: (mode) => set(() => ({ workflowMode: mode })),
  setScratchArrangement: (rows) => set(() => ({ scratchArrangement: clone(rows) })),

  // arrangement
  setTempoMap: (tempoMap) => set((s) => ({ arrangement: { ...s.arrangement, tempoMap: clone(tempoMap) } })),
  setBeatTimes: (beatTimes) =>
    set((s) => ({
      arrangement: {
        ...s.arrangement,
        beatTimes: (() => {
          if (!beatTimes) return undefined;
          const raw = clone(beatTimes) as any;
          if (!Array.isArray(raw) || raw.length < 2) return undefined;

          const asNums = raw.map((t: any) => Number(t)).filter((t: number) => Number.isFinite(t));
          if (asNums.length < 2) return undefined;

          const offset = Number.isFinite(asNums[0]) ? asNums[0] : 0;
          const normalized = asNums
            .map((t: number) => t - offset)
            .filter((t: number) => Number.isFinite(t));

          return normalized.length >= 2 ? normalized : undefined;
        })(),
      },
    })),
  setTimeSig: (numerator, denominator) => set((s) => ({ arrangement: { ...s.arrangement, timeSig: [numerator, denominator] } })),
  setSections: (sections) => set((s) => ({ arrangement: { ...s.arrangement, sections: clone(sections) } })),

  // import
  setImportState: (patch) => set((s) => ({ importState: { ...s.importState, ...clone(patch) } })),
  resetImport: () =>
    set((s) => ({
      importState: createDefaultImportState(),
      generatedDrumTrack: null,
      selection: {
        ...s.selection,
        selectedNoteIds: [],
        selectedBarIndex: null,
        selectedSectionId: null,
      },
    })),

  // generation
  setGeneratedDrumTrack: (track) =>
    set((s) => {
      const nextTrack = track ? clone(track) : null;

      const computeMetrics = (t: any): V3CoachMetrics | null => {
        if (!t || !Array.isArray(t.notes)) return null;
        const notes = t.notes as any[];
        const ppq = Number(t.resolution_ppq || 960) || 960;
        const tick16 = ppq / 4;
        const velocities: number[] = [];
        let absDevSum = 0;
        let devCount = 0;

        for (const n of notes) {
          const ti = Number((n as any)?.tickInBar ?? 0) || 0;
          const vel = Number((n as any)?.velocity ?? 0) || 0;
          if (Number.isFinite(vel) && vel > 0) velocities.push(vel);
          const q = Math.round(ti / tick16) * tick16;
          const dev = Math.abs(ti - q);
          if (Number.isFinite(dev)) {
            absDevSum += dev;
            devCount += 1;
          }
        }

        const meanAbsDev = devCount ? absDevSum / devCount : 0;
        const timing_score = Math.max(0, Math.min(1, 1 - meanAbsDev / Math.max(1e-6, tick16)));

        // velocity score: prefer moderate variance (not robotic, not chaotic)
        let velMean = 0;
        for (const v of velocities) velMean += v;
        velMean = velocities.length ? velMean / velocities.length : 0;
        let velVar = 0;
        for (const v of velocities) velVar += (v - velMean) * (v - velMean);
        const velStd = velocities.length ? Math.sqrt(velVar / velocities.length) : 0;
        const velStdNorm = Math.max(0, Math.min(1, velStd / 22));
        const velocity_score = velStdNorm;

        const humanization_score = Math.max(0, Math.min(1, (timing_score + velocity_score) / 2));
        const overall_score = humanization_score;

        return {
          timing_score,
          velocity_score,
          humanization_score,
          overall_score,
          note_count: notes.length,
        };
      };

      const metrics = computeMetrics(nextTrack);
      const shouldCaptureAfter = !!s.coach.snapshotPendingAfter;
      const snapshot = shouldCaptureAfter
        ? {
            ...(s.coach.snapshot || {}),
            after: { ts: Date.now(), metrics },
          }
        : s.coach.snapshot;

      return {
        generatedDrumTrack: nextTrack,
        coach: {
          ...s.coach,
          lastTrackMetrics: metrics,
          snapshot,
          snapshotPendingAfter: shouldCaptureAfter ? false : s.coach.snapshotPendingAfter,
        },
      };
    }),

  // transport
  setPlayheadSec: (sec) =>
    set(() => ({
      playheadSec: Number.isFinite(sec) ? Math.max(0, sec) : 0,
    })),

  // selection
  setSelectedSectionId: (sectionId) => set((s) => ({ selection: { ...s.selection, selectedSectionId: sectionId } })),
  setSelectedBarIndex: (barIndex) => set((s) => ({ selection: { ...s.selection, selectedBarIndex: barIndex } })),
  setSelectedClip: (trackId, clipId) =>
    set((s) => ({
      selection: { ...s.selection, selectedTrackId: trackId, selectedClipId: clipId },
    })),
  setSelectedNoteIds: (noteIds) => set((s) => ({ selection: { ...s.selection, selectedNoteIds: [...noteIds] } })),

  // ui
  setEditorTab: (tab) => set((s) => ({ ui: { ...s.ui, editorTab: tab } })),
  setShowLegacyParity: (on) => set((s) => ({ ui: { ...s.ui, showLegacyParity: on } })),
  setInspectorView: (view) => set((s) => ({ ui: { ...s.ui, inspectorView: view } })),
  setPresetPreview: (on) => set((s) => ({ ui: { ...s.ui, presetPreview: !!on } })),
  setDrummerPickerOpen: (open) => set((s) => ({ ui: { ...s.ui, drummerPickerOpen: !!open } })),
  setDrummerPickerTarget: (target) => set((s) => ({ ui: { ...s.ui, drummerPickerTarget: clone(target) } })),
  bumpAutoGenerateNonce: () =>
    set((s) => ({
      ui: {
        ...s.ui,
        autoGenerateNonce: Number(s.ui.autoGenerateNonce || 0) + 1,
      },
    })),

  // coach
  setCoachSelectedGoalIds: (goalIds) =>
    set((s) => ({
      coach: {
        ...s.coach,
        selectedGoalIds: Array.isArray(goalIds) ? [...goalIds.map((g) => String(g)).filter(Boolean)] : [],
      },
    })),

  fetchCoachGoals: async () => {
    const apiBase = get().env.apiBase || "";
    try {
      const res = await fetch(`${apiBase}/api/groove/goals`);
      const j = await res.json();
      const sound_first: V3CoachGoal[] = Array.isArray(j?.sound_first) ? (j.sound_first as any) : [];
      const technique_first: V3CoachGoal[] = Array.isArray(j?.technique_first) ? (j.technique_first as any) : [];
      set((s) => ({
        coach: {
          ...s.coach,
          availableGoals: { sound_first, technique_first },
        },
      }));
    } catch (e: any) {
      set((s) => ({
        coach: {
          ...s.coach,
          availableGoals: null,
          lastAnalysis: {
            ok: false,
            error: e?.message || String(e),
          } as V3CoachAnalysis,
        },
      }));
    }
  },

  runGrooveCoach: async () => {
    const apiBase = get().env.apiBase || "";
    const goals = get().coach.selectedGoalIds;
    const sectionId = get().selection.selectedSectionId || "all";

    let sectionLabel: string | undefined = undefined;
    try {
      if (sectionId && sectionId !== "all") {
        const secs: any[] = Array.isArray(get().arrangement.sections) ? (get().arrangement.sections as any) : [];
        for (let i = 0; i < secs.length; i++) {
          const s = secs[i];
          const sid = v3SectionId(i, { startSec: Number(s?.startSec || 0), endSec: Number(s?.endSec || 0) });
          if (sid === sectionId) {
            sectionLabel = String(s?.label || "").trim() || undefined;
            break;
          }
        }
      }
    } catch {
      // ignore
    }

    // Send current effective config so backend can avoid recommending deltas that clamp out.
    let currentConfig: any = undefined;
    try {
      if (sectionId && sectionId !== "all") {
        currentConfig = get().getEffectiveSectionConfig(String(sectionId));
      } else {
        currentConfig = get().globalDefaults;
      }
    } catch {
      currentConfig = get().globalDefaults;
    }
    try {
      const res = await fetch(`${apiBase}/api/groove/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ section_id: sectionId, section_label: sectionLabel, goals, current_config: currentConfig }),
      });
      const j = await res.json();
      set((s) => ({ coach: { ...s.coach, lastAnalysis: j as V3CoachAnalysis } }));
    } catch (e: any) {
      set((s) => ({
        coach: {
          ...s.coach,
          lastAnalysis: {
            ok: false,
            error: e?.message || String(e),
          } as V3CoachAnalysis,
        },
      }));
    }
  },

  applyCoachPatch: async () => {
    const apiBase = get().env.apiBase || "";
    const analysis = get().coach.lastAnalysis;
    const patch = (analysis as any)?.config_patch;
    if (!patch || typeof patch !== "object") return;

    const selectedSectionId = get().selection.selectedSectionId;
    const isSectionTarget = !!selectedSectionId;

    const currentGlobal = get().globalDefaults as any;
    const currentSection = selectedSectionId ? (get().sectionOverrides[selectedSectionId] as any) : null;

    // Snapshot BEFORE apply.
    set((s) => ({
      coach: {
        ...s.coach,
        snapshot: {
          before: {
            ts: Date.now(),
            target: isSectionTarget ? "section" : "global",
            sectionId: selectedSectionId || undefined,
            config: isSectionTarget ? clone(currentSection || {}) : clone(currentGlobal || {}),
            metrics: s.coach.lastTrackMetrics,
          },
        },
        snapshotPendingAfter: true,
      },
    }));

    try {
      const res = await fetch(`${apiBase}/api/groove/apply-patch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          config: isSectionTarget ? (currentSection?.overrides || {}) : currentGlobal,
          config_patch: patch,
        }),
      });
      const j = await res.json();
      const patched = (j as any)?.patched_config;
      if (!patched || typeof patched !== "object") return;

      if (!isSectionTarget) {
        // Only apply keys that exist in globalDefaults to avoid accidental shape drift.
        const next: any = { ...currentGlobal };
        for (const k of Object.keys(currentGlobal)) {
          if (k in patched) next[k] = patched[k];
        }
        if (currentGlobal.fillControls && patched.fillControls) next.fillControls = { ...currentGlobal.fillControls, ...patched.fillControls };
        if (currentGlobal.rudimentControls && patched.rudimentControls)
          next.rudimentControls = { ...currentGlobal.rudimentControls, ...patched.rudimentControls };
        if (currentGlobal.brainConfig && patched.brainConfig) next.brainConfig = { ...currentGlobal.brainConfig, ...patched.brainConfig };
        if (currentGlobal.grooveControls && patched.grooveControls) next.grooveControls = { ...currentGlobal.grooveControls, ...patched.grooveControls };

        set(() => ({ globalDefaults: next }));
      } else {
        // Apply to section overrides + flip inherit flags only for impacted groups.
        const secId = String(selectedSectionId);
        const prev = get().sectionOverrides[secId] ?? createDefaultSectionOverrideState();
        const prevOverrides = (prev as any).overrides || {};
        const nextOverrides = { ...prevOverrides, ...patched };

        const nextInherit = { ...(prev.inherit || DEFAULT_INHERIT) } as any;
        const touched = new Set<string>();
        const walk = (node: any, prefix: string) => {
          if (!node || typeof node !== "object") return;
          for (const k of Object.keys(node)) {
            const v = node[k];
            const p = prefix ? `${prefix}.${k}` : k;
            if (v && typeof v === "object" && "op" in v && "delta" in v) {
              touched.add(p);
            } else if (v && typeof v === "object") {
              walk(v, p);
            }
          }
        };
        // Use the patch object itself to decide which groups were targeted.
        walk(patch, "");
        const paths = Array.from(touched);
        const hasAny = (keys: string[]) => paths.some((p) => keys.some((k) => p === k || p.startsWith(`${k}.`)));
        if (hasAny(["humanize", "humanizeAmount", "ghostNoteAmount", "swingAmount"])) nextInherit.humanization = "override";
        if (hasAny(["fillControls", "fillType", "fillDensity", "fillLocations"])) nextInherit.fills = "override";
        if (hasAny(["rudimentControls", "rudimentBlocks"])) nextInherit.rudiments = "override";
        if (hasAny(["selectedGrooveId", "grooveUse", "fillGrooveId", "grooveControls", "grooveMode", "styleGroup", "grooveSource"]))
          nextInherit.groove = "override";
        if (hasAny(["brainConfig"])) nextInherit.brain = "override";
        if (hasAny(["guideEnabled", "guideInstrument"])) nextInherit.guide = "override";
        if (
          hasAny([
            "intensity",
            "variation",
            "generationMode",
            "buildScope",
            "songStyle",
            "songSections",
            "chorusRidePreference",
            "cymbalFocusMode",
            "hatsToRideBlend",
            "hatsToRideThreshold",
            "rideBellPercent",
            "footHatPulseSubdivision",
            "footHatPulseApply",
          ])
        ) {
          nextInherit.generation = "override";
        }

        set((s) => ({
          sectionOverrides: {
            ...s.sectionOverrides,
            [secId]: {
              ...prev,
              inherit: nextInherit,
              overrides: nextOverrides,
            },
          },
        }));
      }

      // Trigger regeneration with updated defaults.
      get().bumpAutoGenerateNonce();
    } catch (e: any) {
      set((s) => ({
        coach: {
          ...s.coach,
          lastAnalysis: {
            ...(analysis || {}),
            ok: false,
            error: e?.message || String(e),
          } as V3CoachAnalysis,
        },
      }));
    }
  },

  // global defaults
  setGlobalDefaults: (patch) => set((s) => ({ globalDefaults: { ...s.globalDefaults, ...clone(patch) } })),
  setGlobalPresetStack: (stack) =>
    set((s) => ({
      globalDefaults: {
        ...s.globalDefaults,
        presetStack: Array.isArray(stack) ? clone(stack) : [],
      },
    })),
  upsertGlobalPreset: (item) =>
    set((s) => {
      const prev = Array.isArray(s.globalDefaults.presetStack) ? s.globalDefaults.presetStack : [];
      const next = [...prev.filter((p) => p.presetId !== item.presetId), clone(item)];
      return { globalDefaults: { ...s.globalDefaults, presetStack: next } };
    }),
  removeGlobalPreset: (presetId) =>
    set((s) => {
      const prev = Array.isArray(s.globalDefaults.presetStack) ? s.globalDefaults.presetStack : [];
      return { globalDefaults: { ...s.globalDefaults, presetStack: prev.filter((p) => p.presetId !== presetId) } };
    }),

  // section overrides
  ensureSection: (sectionId) =>
    set((s) => {
      if (s.sectionOverrides[sectionId]) return s;
      return {
        sectionOverrides: {
          ...s.sectionOverrides,
          [sectionId]: createDefaultSectionOverrideState(),
        },
      };
    }),

  setSectionInheritGlobalPresets: (sectionId, inherit) =>
    set((s) => {
      const prev = s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState();
      return {
        sectionOverrides: {
          ...s.sectionOverrides,
          [sectionId]: {
            ...prev,
            inheritGlobalPresets: !!inherit,
          },
        },
      };
    }),
  setSectionPresetStack: (sectionId, stack) =>
    set((s) => {
      const prev = s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState();
      return {
        sectionOverrides: {
          ...s.sectionOverrides,
          [sectionId]: {
            ...prev,
            presetStack: Array.isArray(stack) ? clone(stack) : [],
          },
        },
      };
    }),
  upsertSectionPreset: (sectionId, item) =>
    set((s) => {
      const prev = s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState();
      const stack = Array.isArray(prev.presetStack) ? prev.presetStack : [];
      const next = [...stack.filter((p) => p.presetId !== item.presetId), clone(item)];
      return {
        sectionOverrides: {
          ...s.sectionOverrides,
          [sectionId]: {
            ...prev,
            presetStack: next,
          },
        },
      };
    }),
  removeSectionPreset: (sectionId, presetId) =>
    set((s) => {
      const prev = s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState();
      const stack = Array.isArray(prev.presetStack) ? prev.presetStack : [];
      return {
        sectionOverrides: {
          ...s.sectionOverrides,
          [sectionId]: {
            ...prev,
            presetStack: stack.filter((p) => p.presetId !== presetId),
          },
        },
      };
    }),

  // audition
  requestAuditionBarPreview: (sectionId, barIndex, startSec, endSec, notes) =>
    set((s) => {
      const prevId = typeof s.auditionRequest?.requestId === "number" ? s.auditionRequest.requestId : 0;
      const nextId = prevId + 1;
      return {
        auditionRequest: {
          requestId: nextId,
          mode: "bar",
          sectionId: String(sectionId),
          barIndex: Number(barIndex),
          startSec: Number(startSec),
          endSec: Number(endSec),
          notes: clone(notes || []),
        },
      };
    }),

  stopAudition: () =>
    set((s) => {
      const prevId = typeof s.auditionRequest?.requestId === "number" ? s.auditionRequest.requestId : 0;
      return {
        auditionRequest: {
          requestId: prevId + 1,
          mode: "stop",
        },
      };
    }),

  setSectionLocked: (sectionId, locked) =>
    set((s) => ({
      sectionOverrides: {
        ...s.sectionOverrides,
        [sectionId]: {
          ...(s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState()),
          locked,
        },
      },
    })),

  setSectionInheritFlag: (sectionId, group, flag) =>
    set((s) => ({
      sectionOverrides: {
        ...s.sectionOverrides,
        [sectionId]: {
          ...(s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState()),
          inherit: {
            ...((s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState()).inherit ?? DEFAULT_INHERIT),
            [group]: flag,
          },
        },
      },
    })),

  setSectionOverrides: (sectionId, patch) =>
    set((s) => ({
      sectionOverrides: {
        ...s.sectionOverrides,
        [sectionId]: {
          ...(s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState()),
          overrides: {
            ...((s.sectionOverrides[sectionId] ?? createDefaultSectionOverrideState()).overrides ?? {}),
            ...clone(patch),
          },
        },
      },
    })),

  clearSectionOverrides: (sectionId) =>
    set((s) => ({
      sectionOverrides: {
        ...s.sectionOverrides,
        [sectionId]: createDefaultSectionOverrideState(),
      },
    })),

  // per-bar edit layer
  ensureBarEdit: (sectionId, barIndex) =>
    set((s) => {
      const secKey = String(sectionId);
      const bi = Number(barIndex);
      if (!Number.isFinite(bi) || bi < 0) return s;
      const bySection = s.barEdits[secKey] || {};
      if (bySection[bi]) return s;
      return {
        barEdits: {
          ...s.barEdits,
          [secKey]: {
            ...bySection,
            [bi]: createDefaultBarEditState(),
          },
        },
      };
    }),

  addBarEditNote: (sectionId, barIndex, note) =>
    set((s) => {
      const secKey = String(sectionId);
      const bi = Number(barIndex);
      if (!Number.isFinite(bi) || bi < 0) return s;
      const bySection = s.barEdits[secKey] || {};
      const cur = bySection[bi] || createDefaultBarEditState();
      return {
        barEdits: {
          ...s.barEdits,
          [secKey]: {
            ...bySection,
            [bi]: {
              ...cur,
              addedNotes: [...(cur.addedNotes || []), clone(note)],
            },
          },
        },
      };
    }),

  deleteBarEditNote: (sectionId, barIndex, noteId) =>
    set((s) => {
      const secKey = String(sectionId);
      const bi = Number(barIndex);
      const nid = String(noteId || "");
      if (!nid) return s;
      const bySection = s.barEdits[secKey] || {};
      const cur = bySection[bi] || createDefaultBarEditState();
      return {
        barEdits: {
          ...s.barEdits,
          [secKey]: {
            ...bySection,
            [bi]: {
              ...cur,
              deletedNoteIds: Array.from(new Set([...(cur.deletedNoteIds || []), nid])),
              // If the note was newly added in this edit layer, remove it entirely.
              addedNotes: (cur.addedNotes || []).filter((n) => String((n as any)?.id || "") !== nid),
            },
          },
        },
      };
    }),

  nudgeBarEditNote: (sectionId, barIndex, noteId, tickDelta) =>
    set((s) => {
      const secKey = String(sectionId);
      const bi = Number(barIndex);
      const nid = String(noteId || "");
      const td = Number(tickDelta);
      if (!nid || !Number.isFinite(td) || td === 0) return s;
      const bySection = s.barEdits[secKey] || {};
      const cur = bySection[bi] || createDefaultBarEditState();

      const tickDeltaByNoteId = { ...(cur.tickDeltaByNoteId || {}) };
      tickDeltaByNoteId[nid] = (Number(tickDeltaByNoteId[nid]) || 0) + td;

      // If this is a newly added note, apply the delta directly into the stored added note.
      const addedNotes = (cur.addedNotes || []).map((n: any) => {
        if (String(n?.id || "") !== nid) return n;
        return { ...n, tickInBar: Number(n.tickInBar || 0) + td };
      });

      return {
        barEdits: {
          ...s.barEdits,
          [secKey]: {
            ...bySection,
            [bi]: {
              ...cur,
              tickDeltaByNoteId,
              addedNotes,
            },
          },
        },
      };
    }),

  clearBarEditsForBar: (sectionId, barIndex) =>
    set((s) => {
      const secKey = String(sectionId);
      const bi = Number(barIndex);
      const bySection = s.barEdits[secKey] || {};
      if (!bySection[bi]) return s;
      const next = { ...bySection };
      delete next[bi];
      return {
        barEdits: {
          ...s.barEdits,
          [secKey]: next,
        },
      };
    }),

  applyBarEditsToGeneratedTrack: (sectionId, barIndex) =>
    set((s) => {
      const track: any = s.generatedDrumTrack;
      if (!track || !Array.isArray(track.notes)) return s;

      const secKey = String(sectionId);
      const bi = Number(barIndex);
      const edit = (s.barEdits[secKey] || {})[bi];
      if (!edit) return s;

      const beatsPerBar = Number(s.arrangement.timeSig?.[0] || 4) || 4;
      const ppq = Number((track as any)?.resolution_ppq || 960) || 960;
      const ticksPerBar = ppq * beatsPerBar;

      const deleted = new Set((edit.deletedNoteIds || []).map((x) => String(x)));
      const tickDeltaById = edit.tickDeltaByNoteId || {};

      const clampTick = (t: number) => Math.max(0, Math.min(ticksPerBar - 1, Math.floor(t)));

      const updatedNotes = (track.notes || []).flatMap((n: any) => {
        const nid = String(n?.id || "");
        const bar = Number(n?.barIndex ?? -1);
        if (bar !== bi) return [n];
        if (deleted.has(nid)) return [];
        const delta = Number(tickDeltaById[nid] || 0);
        if (!Number.isFinite(delta) || delta === 0) return [n];
        return [{ ...n, tickInBar: clampTick(Number(n.tickInBar || 0) + delta) }];
      });

      const addedNotes = (edit.addedNotes || []).map((n: any) => {
        return {
          ...n,
          barIndex: bi,
          tickInBar: clampTick(Number(n.tickInBar || 0)),
          tickLength: Math.max(1, Math.floor(Number(n.tickLength || 1))),
        };
      });

      const merged = [...updatedNotes, ...addedNotes];

      return {
        generatedDrumTrack: {
          ...track,
          notes: merged,
        },
        barEdits: {
          ...s.barEdits,
          [secKey]: {
            ...(s.barEdits[secKey] || {}),
            [bi]: {
              ...createDefaultBarEditState(),
              forceFill: !!edit.forceFill,
              suppressFill: !!edit.suppressFill,
            },
          },
        },
      };
    }),

  setBarFillDirective: (sectionId, barIndex, patch) =>
    set((s) => {
      const secKey = String(sectionId);
      const bi = Number(barIndex);
      const prev = (s.barEdits[secKey] || {})[bi] || createDefaultBarEditState();
      return {
        barEdits: {
          ...s.barEdits,
          [secKey]: {
            ...(s.barEdits[secKey] || {}),
            [bi]: {
              ...prev,
              ...clone(patch || {}),
            },
          },
        },
      };
    }),

  // derived
  getEffectiveSectionConfig: (sectionId) => {
    const global = get().globalDefaults;
    const section = get().sectionOverrides[sectionId] ?? createDefaultSectionOverrideState();

    // Start with global defaults.
    let merged: any = { ...global };

    // Apply overrides by groups based on inherit flags.
    (Object.keys(section.inherit) as V3FieldGroup[]).forEach((group) => {
      if (section.inherit[group] === "override") {
        merged = { ...merged, ...pickOverrideGroups(section.overrides, group) };
      }
    });

    return merged;
  },
} as V3Store));
