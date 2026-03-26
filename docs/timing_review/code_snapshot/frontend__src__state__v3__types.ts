import type { DrumGenerationConfig, FillControls, FillFrequency, RudimentBlock, RudimentControls, RudimentHandLead } from "../../types/drumTrack";
import type { DrumNoteEvent, DrumTrackForDCSM } from "../../types/drumTrack";
import type { ArrangementSection, TempoPt } from "../../midi/types";

export type V3EditorTab = "bar_tools" | "piano_roll" | "mixer" | "groove_library" | "metrics";

export type V3InspectorView = "both" | "global" | "section";

export type V3WorkflowMode = "audio" | "scratch";

export type V3ScratchRow = {
  label: string;
  bars: number;
};

export type V3BuildScope = "selected_section" | "full_song";

export type V3ExportPlugin = "jamstix" | "sd3" | "ssd5";

export type V3InheritFlag = "inherit" | "override";

export type V3FieldGroup =
  | "identity" // style/drummer
  | "generation" // intensity/variation/mode
  | "humanization" // humanize + amounts
  | "fills" // fill controls
  | "rudiments" // rudiment controls + blocks
  | "groove" // groove library selections
  | "egmd" // egmd phrase pin/overrides
  | "brain" // brain config
  | "guide"; // guide track

export type V3SectionOverrideState = {
  locked: boolean;
  inherit: Record<V3FieldGroup, V3InheritFlag>;
  overrides: Partial<DrumGenerationConfig>;
  inheritGlobalPresets?: boolean;
  presetStack?: V3PresetStackItem[];
};

export type V3PresetTier = "song" | "flavor" | "utility";

export type V3PresetStackItem = {
  presetId: string;
  tier: V3PresetTier;
  intensity: number; // 0..100
};

export type V3BarEditState = {
  addedNotes: DrumNoteEvent[];
  deletedNoteIds: string[];
  tickDeltaByNoteId: Record<string, number>;

  forceFill?: boolean;
  suppressFill?: boolean;
};

export type V3AuditionRequest =
  | {
      requestId: number;
      mode: "bar";
      sectionId: string;
      barIndex: number;
      startSec: number;
      endSec: number;
      notes: DrumNoteEvent[];
    }
  | {
      requestId: number;
      mode: "stop";
    };

export type V3GlobalDefaults = {
  buildScope: V3BuildScope;

  // export
  exportPlugin?: V3ExportPlugin;
  advancedArticulations?: boolean;

  // identity
  style: string;
  drummer: string;
  publicDrummerId?: string;

  // generation
  intensity: number; // 0..1
  variation: number; // 0..1
  generationMode: DrumGenerationConfig["generationMode"];

  // cymbal focus / hat-vs-ride
  chorusRidePreference?: number;
  cymbalFocusMode?: DrumGenerationConfig["cymbalFocusMode"];
  hatsToRideBlend?: number;
  hatsToRideThreshold?: number;
  rideBellPercent?: number;

  // left-foot hat pulse while riding
  footHatPulseSubdivision?: DrumGenerationConfig["footHatPulseSubdivision"];
  footHatPulseApply?: DrumGenerationConfig["footHatPulseApply"];

  // humanization
  humanize: boolean;
  humanizeAmount?: number;
  ghostNoteAmount?: number;
  swingAmount?: number;

  // fills/rudiments
  fillControls?: FillControls;
  rudimentControls?: RudimentControls;
  rudimentBlocks?: RudimentBlock[];

  // guide
  guideEnabled?: boolean;
  guideInstrument?: DrumGenerationConfig["guideInstrument"];

  // groove
  selectedGrooveId?: string;
  grooveUse?: DrumGenerationConfig["grooveUse"];
  fillGrooveId?: string;

  grooveSource?: DrumGenerationConfig["grooveSource"];
  grooveMode?: DrumGenerationConfig["grooveMode"];
  styleGroup?: DrumGenerationConfig["styleGroup"];

  // egmd
  egmdPhraseId?: number;
  egmdPhraseOverrides?: DrumGenerationConfig["egmdPhraseOverrides"];

  // When selecting a groove from the EGMD browse modal, prefer exact playback by MIDI path.
  // (Phrase IDs can be ambiguous across multiple EGMD indices/databases.)
  egmdMidiPath?: string;
  egmdFillMidiPath?: string;

  // brain
  brainConfig?: DrumGenerationConfig["brainConfig"];

  presetStack?: V3PresetStackItem[];
};

export type V3SelectionState = {
  selectedSectionId: string | null;
  selectedBarIndex: number | null;
  selectedTrackId: string | null;
  selectedClipId: string | null;
  selectedNoteIds: string[];
};

export type V3ArrangementState = {
  tempoMap: TempoPt[];
  beatTimes?: number[];
  timeSig: [number, number];
  sections: ArrangementSection[];
};

export type V3WaveformState = {
  peaks: number[];
  peaksL?: number[];
  peaksR?: number[];
  sr?: number;
  duration?: number;
};

export type V3ImportState = {
  fileKey: string | null;
  fileName: string | null;
  waveform: V3WaveformState | null;
  busyStage: "idle" | "upload" | "waveform" | "tempo" | "sectionize" | "align" | "generate";
  timeSigConfirmed: boolean;
  error: string | null;
};

export type V3UiState = {
  editorTab: V3EditorTab;
  showLegacyParity: boolean;
  arrangementOwner: "legacy" | "v3";
  inspectorView: V3InspectorView;
  presetPreview: boolean;

  autoGenerateNonce?: number;

  drummerPickerOpen?: boolean;
  drummerPickerTarget?: { scope: "global" } | { scope: "section"; sectionId: string };
};

export type V3CoachGoal = {
  id: string;
  label?: string;
  description?: string;
  tags?: string[];
};

export type V3CoachPatchLeaf = {
  op: "add";
  delta: number;
  clamp?: [number, number];
  reason?: string;
};

export type V3CoachPatch = Record<string, any>;

export type V3CoachAnalysis = {
  ok?: boolean;
  timing_score?: number;
  velocity_score?: number;
  humanization_score?: number;
  overall_score?: number;
  suggestions?: string[];
  coach_suggestions?: any[];
  config_patch?: V3CoachPatch;
  error?: string;
};

export type V3CoachMetrics = {
  timing_score: number;
  velocity_score: number;
  humanization_score: number;
  overall_score: number;
  note_count: number;
};

export type V3CoachSnapshot = {
  before?: {
    ts: number;
    target: "global" | "section";
    sectionId?: string;
    config: any;
    metrics: V3CoachMetrics | null;
  };
  after?: {
    ts: number;
    metrics: V3CoachMetrics | null;
  };
};

export type V3CoachState = {
  availableGoals: {
    sound_first: V3CoachGoal[];
    technique_first: V3CoachGoal[];
  } | null;
  selectedGoalIds: string[];
  lastAnalysis: V3CoachAnalysis | null;

  // computed from generatedDrumTrack
  lastTrackMetrics: V3CoachMetrics | null;

  // A/B snapshot around Apply->Regenerate
  snapshot: V3CoachSnapshot | null;
  snapshotPendingAfter: boolean;
};

export type V3EnvState = {
  // For Docker/Linux: resolveApiBaseNormalized() already supports REACT_APP_API_BASE.
  apiBase: string;
};

export type V3State = {
  env: V3EnvState;
  workflowMode: V3WorkflowMode;
  scratchArrangement: V3ScratchRow[];
  globalDefaults: V3GlobalDefaults;
  sectionOverrides: Record<string, V3SectionOverrideState>;
  barEdits: Record<string, Record<number, V3BarEditState>>;
  auditionRequest: V3AuditionRequest | null;
  arrangement: V3ArrangementState;
  importState: V3ImportState;
  generatedDrumTrack: DrumTrackForDCSM | null;
  playheadSec: number;
  selection: V3SelectionState;
  ui: V3UiState;
  coach: V3CoachState;
};

export type V3Actions = {
  // workflow
  setWorkflowMode: (mode: V3WorkflowMode) => void;
  setScratchArrangement: (rows: V3ScratchRow[]) => void;

  // arrangement
  setTempoMap: (tempoMap: TempoPt[]) => void;
  setBeatTimes: (beatTimes: number[] | null) => void;
  setTimeSig: (numerator: number, denominator: number) => void;
  setSections: (sections: ArrangementSection[]) => void;

  // import
  setImportState: (patch: Partial<V3ImportState>) => void;
  resetImport: () => void;

  // generation
  setGeneratedDrumTrack: (track: DrumTrackForDCSM | null) => void;

  // transport
  setPlayheadSec: (sec: number) => void;

  // selection
  setSelectedSectionId: (sectionId: string | null) => void;
  setSelectedBarIndex: (barIndex: number | null) => void;
  setSelectedClip: (trackId: string | null, clipId: string | null) => void;
  setSelectedNoteIds: (noteIds: string[]) => void;

  // ui
  setEditorTab: (tab: V3EditorTab) => void;
  setShowLegacyParity: (on: boolean) => void;
  setInspectorView: (view: V3InspectorView) => void;
  setPresetPreview: (on: boolean) => void;
  setDrummerPickerOpen: (open: boolean) => void;
  setDrummerPickerTarget: (target: { scope: "global" } | { scope: "section"; sectionId: string }) => void;
  bumpAutoGenerateNonce: () => void;

  // global defaults
  setGlobalDefaults: (patch: Partial<V3GlobalDefaults>) => void;
  setGlobalPresetStack: (stack: V3PresetStackItem[]) => void;
  upsertGlobalPreset: (item: V3PresetStackItem) => void;
  removeGlobalPreset: (presetId: string) => void;

  // section overrides
  ensureSection: (sectionId: string) => void;
  setSectionLocked: (sectionId: string, locked: boolean) => void;
  setSectionInheritFlag: (sectionId: string, group: V3FieldGroup, flag: V3InheritFlag) => void;
  setSectionOverrides: (sectionId: string, patch: Partial<DrumGenerationConfig>) => void;
  clearSectionOverrides: (sectionId: string) => void;
  setSectionInheritGlobalPresets: (sectionId: string, inherit: boolean) => void;
  setSectionPresetStack: (sectionId: string, stack: V3PresetStackItem[]) => void;
  upsertSectionPreset: (sectionId: string, item: V3PresetStackItem) => void;
  removeSectionPreset: (sectionId: string, presetId: string) => void;

  // per-bar edit layer (non-destructive until Apply)
  ensureBarEdit: (sectionId: string, barIndex: number) => void;
  addBarEditNote: (sectionId: string, barIndex: number, note: DrumNoteEvent) => void;
  deleteBarEditNote: (sectionId: string, barIndex: number, noteId: string) => void;
  nudgeBarEditNote: (sectionId: string, barIndex: number, noteId: string, tickDelta: number) => void;
  setBarFillDirective: (sectionId: string, barIndex: number, patch: { forceFill?: boolean; suppressFill?: boolean }) => void;
  clearBarEditsForBar: (sectionId: string, barIndex: number) => void;
  applyBarEditsToGeneratedTrack: (sectionId: string, barIndex: number) => void;

  // audition
  requestAuditionBarPreview: (sectionId: string, barIndex: number, startSec: number, endSec: number, notes: DrumNoteEvent[]) => void;
  stopAudition: () => void;

  // derived
  getEffectiveSectionConfig: (sectionId: string) => V3GlobalDefaults & Partial<DrumGenerationConfig>;

  // coach
  setCoachSelectedGoalIds: (goalIds: string[]) => void;
  fetchCoachGoals: () => Promise<void>;
  runGrooveCoach: () => Promise<void>;
  applyCoachPatch: () => Promise<void>;
};

export type V3Store = V3State & V3Actions;

export const DEFAULT_INHERIT: Record<V3FieldGroup, V3InheritFlag> = {
  identity: "inherit",
  generation: "inherit",
  humanization: "inherit",
  fills: "inherit",
  rudiments: "inherit",
  groove: "inherit",
  egmd: "inherit",
  brain: "inherit",
  guide: "inherit",
};

export function createDefaultGlobalDefaults(): V3GlobalDefaults {
  return {
    buildScope: "selected_section",

    exportPlugin: "jamstix",
    advancedArticulations: false,

    style: "rock",
    drummer: "",
    publicDrummerId: "",

    intensity: 0.7,
    variation: 0.8,
    generationMode: "ai_variation",

    chorusRidePreference: 0,
    cymbalFocusMode: "continuous",
    hatsToRideBlend: 0,
    hatsToRideThreshold: 0.6,
    rideBellPercent: 0.2,
    footHatPulseSubdivision: "off",
    footHatPulseApply: "both",

    humanize: true,
    humanizeAmount: 0.7,
    ghostNoteAmount: 0.7,
    swingAmount: 0,

    fillControls: {
      fillType: "auto",
      density: 0.7,
      frequency: "section_transitions" as FillFrequency,
    },
    rudimentControls: {
      enabled: true,
      preferredFamilies: [],
      preferredRudiments: [],
      density: 0.7,
      ensureDownbeatKick: true,
      preserveHatTail: true,
      handLead: "auto" as RudimentHandLead,
    },

    grooveSource: undefined,
    grooveMode: undefined,
    styleGroup: "rock",

    presetStack: [],
  };
}

export function createDefaultArrangement(): V3ArrangementState {
  return {
    tempoMap: [{ tSec: 0, bpm: 120 }],
    beatTimes: undefined,
    timeSig: [4, 4],
    sections: [],
  };
}

export function createDefaultImportState(): V3ImportState {
  return {
    fileKey: null,
    fileName: null,
    waveform: null,
    busyStage: "idle",
    timeSigConfirmed: false,
    error: null,
  };
}
