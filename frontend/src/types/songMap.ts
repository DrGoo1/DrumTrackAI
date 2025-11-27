// types/songMap.ts - Full SongMap types for bar-level analysis

export type Bar = {
  index: number;
  start_time: number;
  end_time: number;
  meter: [number, number];
  tempo_bpm: number;
  beat_times: number[];
  confidence: number;
};

export type SectionLabel =
  | "intro"
  | "verse"
  | "prechorus"
  | "chorus"
  | "bridge"
  | "solo"
  | "outro"
  | "break"
  | "section"
  | "unknown";

export type Section = {
  id?: string;
  start: number;
  end: number;
  label?: SectionLabel | string;
  confidence?: number;
  energy?: number;
  spectral_centroid?: number;
  repetition_group?: number;
  tempo?: number;
  tempoConfidence?: number;
  tempoLocked?: boolean;

  // Bar integration
  startBarIndex?: number;
  endBarIndex?: number;
  barCount?: number;
  
  // UI properties
  density?: number;
  fillIn?: boolean;
  fillOut?: boolean;
};

export type SongMap = {
  duration: number;
  global_bpm_estimate: number;
  meter: [number, number];
  bars: Bar[];
  sections: Section[];
  beat_times: number[];
};

export type DrumBarPlan = {
  barIndex: number;
  sectionLabel: SectionLabel;
  barRole: "start" | "middle" | "end";
  grooveIntensity: number;     // 0–1
  addFill: boolean;
  crashOnDownbeat: boolean;
};

/**
 * Build drum plan from SongMap for automated drum generation
 */
export function buildDrumPlanFromSongMap(map: SongMap): DrumBarPlan[] {
  const plans: DrumBarPlan[] = [];
  const { bars, sections } = map;

  const findSectionForBar = (barIdx: number): Section | undefined =>
    sections.find(
      (s) =>
        (s.startBarIndex ?? 0) <= barIdx &&
        barIdx <= (s.endBarIndex ?? barIdx)
    );

  for (const bar of bars) {
    const sec = findSectionForBar(bar.index);
    const secLabel: SectionLabel = (sec?.label as SectionLabel) ?? "section";
    const secBars = (sec?.barCount ?? 1);
    const relPos =
      secBars > 1
        ? (bar.index - (sec?.startBarIndex ?? bar.index)) / (secBars - 1)
        : 0;

    let barRole: "start" | "middle" | "end" = "middle";
    if (relPos < 0.15) barRole = "start";
    else if (relPos > 0.85) barRole = "end";

    const energy = sec?.energy ?? 0.6;

    // Basic groove intensity rules
    let grooveIntensity = 0.6;
    if (secLabel === "chorus") grooveIntensity = 0.9;
    else if (secLabel === "verse") grooveIntensity = 0.7;
    else if (secLabel === "intro" || secLabel === "outro") grooveIntensity = 0.4;

    grooveIntensity *= 0.8 + 0.4 * energy; // scale by energy

    // Fills near section ends
    const addFill =
      barRole === "end" &&
      (secLabel === "verse" ||
        secLabel === "chorus" ||
        secLabel === "bridge");

    const crashOnDownbeat =
      barRole === "start" &&
      (secLabel === "chorus" || secLabel === "bridge");

    plans.push({
      barIndex: bar.index,
      sectionLabel: secLabel,
      barRole,
      grooveIntensity: Math.max(0.2, Math.min(1.0, grooveIntensity)),
      addFill,
      crashOnDownbeat,
    });
  }

  return plans;
}
