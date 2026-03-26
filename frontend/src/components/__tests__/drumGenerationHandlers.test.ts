import {
  applyDrumGenerationResult,
  type ApplyDrumGenerationDeps,
  type DrumGenerationResultShape,
  GLOBAL_FALLBACK_SECTION_ID,
} from "../drumGenerationHandlers";
import type { DrumGenerationConfig, DrumTrackForDCSM } from "../../types/drumTrack";

const baseConfig = (overrides: Partial<DrumGenerationConfig> = {}): DrumGenerationConfig => ({
  sectionId: "verse-1",
  startMeasure: 0,
  endMeasure: 4,
  tempos: [120, 120, 120, 120],
  timeSignature: [4, 4],
  style: "rock",
  drummer: "jeff_porcaro",
  intensity: 0.5,
  variation: 0.5,
  generationMode: "ai_variation",
  humanize: true,
  fillLocations: [],
  fillType: "auto",
  fillDensity: 0.5,
  ...overrides,
});

const fakeTrack = (): DrumTrackForDCSM => ({
  track_id: "t1",
  style_id: "rock",
  resolution_ppq: 960,
  notes: [
    {
      id: "n1",
      barIndex: 0,
      tickInBar: 0,
      tickLength: 960,
      instrumentId: "snare_center",
      velocity: 110,
      channel: 9,
      midiPitch: 38,
      isGhost: false,
      isAccent: true,
      isFlam: false,
      isDrag: false,
    },
    {
      id: "n2",
      barIndex: 1,
      tickInBar: 0,
      tickLength: 960,
      instrumentId: "kick",
      velocity: 100,
      channel: 9,
      midiPitch: 36,
      isGhost: false,
      isAccent: false,
      isFlam: false,
      isDrag: false,
    },
  ],
  performance_spec: {
    styleId: "rock",
    globalFeel: "straight",
    quantizationBase: "16th",
    phrases: [],
  },
});

const makeDeps = (): ApplyDrumGenerationDeps & { convertTrackToMidiNotes?: jest.Mock } => {
  const setSectionDrumTracks = jest.fn(
    (updater: (prev: Record<string, DrumTrackForDCSM>) => Record<string, DrumTrackForDCSM>) => {
      updater({});
    },
  );
  const setSectionGrooveMaps = jest.fn(
    (updater: (prev: Record<string, any>) => Record<string, any>) => {
      updater({});
    },
  );
  const setNotes = jest.fn((updater: (prev: any[]) => any[]) => {
    updater([]);
  });
  return {
    bpm: 120,
    timeSig: [4, 4],
    setSectionDrumTracks,
    setSectionGrooveMaps,
    setNotes,
    syncSectionMidiNotes: jest.fn(),
    ensureSectionSelection: jest.fn(),
    applyTrackToMidiClip: jest.fn(),
    setDebugDrumGen: jest.fn(),
  };
};

describe("applyDrumGenerationResult", () => {
  it("applies drum tracks to section state + midi clip", () => {
    const deps = makeDeps();
    const payload = baseConfig({ sectionId: "s1" });
    const result: DrumGenerationResultShape = {
      drum_track: fakeTrack(),
      metadata: {},
    };
    const applied = applyDrumGenerationResult(result as any, payload as any, deps as any, {
      placementContext: {
        startMeasure: 0,
        endMeasure: 1,
        tempos: [120, 120, 120, 120],
        timeSignature: [4, 4],
        startTimeSec: 0,
      },
    });

    expect(applied).toBe(true);
    expect(deps.setSectionDrumTracks).toHaveBeenCalled();
    expect(deps.syncSectionMidiNotes).toHaveBeenCalledWith(
      "s1",
      expect.objectContaining({ track_id: "t1" }),
      expect.any(Object),
    );
    expect(deps.applyTrackToMidiClip).toHaveBeenCalledWith("s1", expect.objectContaining({ track_id: "t1" }), null, expect.any(Object));
  });

  it("handles missing sectionId by applying as global", () => {
    const deps = makeDeps();
    const payload = baseConfig({ sectionId: null as any });
    const convertTrackToMidiNotes = jest.fn(() => [
      { id: "p1", time: 0, duration: 0.5, lane: "snare", vel: 0.8 },
    ]);
    const result: DrumGenerationResultShape = {
      drum_track: fakeTrack(),
      metadata: {},
    };

    const applied = applyDrumGenerationResult(
      result,
      payload,
      {
        ...deps,
      },
      {
        convertTrackToMidiNotes,
      },
    );

    expect(applied).toBe(true);
    expect(deps.setSectionDrumTracks).toHaveBeenCalledWith(expect.any(Function));
    expect(deps.syncSectionMidiNotes).not.toHaveBeenCalled();
    expect(deps.setNotes).toHaveBeenCalled();
    expect(deps.applyTrackToMidiClip).toHaveBeenCalledWith(null, expect.objectContaining({ track_id: "t1" }));
    const sectionDrumTracksMock = deps.setSectionDrumTracks as jest.Mock;
    const [[updater]] = sectionDrumTracksMock.mock.calls;
    const updated = updater({});
    expect(updated).toEqual(
      expect.objectContaining({
        [GLOBAL_FALLBACK_SECTION_ID]: expect.objectContaining({ track_id: "t1" }),
      }),
    );
  });

  it("hydrates legacy notes", () => {
    const deps = makeDeps();
    const hydrateLegacyNote = jest.fn((note: any, idx: number) => ({
      id: `legacy-${idx}`,
      time: note.time ?? 0,
      duration: 0.25,
      lane: "snare",
      vel: 0.8,
    }));
    const legacyNotes = [{ time: 0.1 }, { time: 0.5 }];

    const result: DrumGenerationResultShape = {
      midi_notes: legacyNotes,
      metadata: {},
    };

    const applied = applyDrumGenerationResult(
      result,
      baseConfig({ sectionId: "intro-1" }),
      deps,
      {
        gridSec: 0.05,
        hydrateLegacyNote,
      },
    );

    expect(applied).toBe(false);
    expect(hydrateLegacyNote).toHaveBeenCalled();
    expect(deps.setNotes).toHaveBeenCalled();
    expect(deps.applyTrackToMidiClip).toHaveBeenCalledWith("intro-1", null, legacyNotes);
  });
});
